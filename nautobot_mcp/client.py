"""Base Nautobot API client wrapping pynautobot.

Provides connection management, error translation, and endpoint access.
Connection is lazy — validated on first API call, not on initialization.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

import pynautobot
from requests.exceptions import ConnectionError as RequestsConnectionError

from nautobot_mcp.config import NautobotProfile, NautobotSettings
from nautobot_mcp.exceptions import (
    NautobotAPIError,
    NautobotAuthenticationError,
    NautobotConnectionError,
    NautobotNotFoundError,
    NautobotValidationError,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# Per-endpoint hint map for ERR-02: actionable hints keyed by URL path prefix.
# Longest-match wins (sorted by key length descending at lookup time).
ERROR_HINTS: dict[str, str] = {
    "/api/dcim/devices/": "Device filter accepts 'name', 'slug', or 'id' (UUID). "
        "Avoid partial name matches — use exact name or UUID.",
    "/api/dcim/interfaces/": "Interface filter requires 'device' set to device UUID, "
        "not device name. Use /api/dcim/devices/ to look up the UUID first.",
    "/api/dcim/locations/": "Location filter: use 'name' for exact match, "
        "'slug' for URL-safe match, or 'id' for UUID.",
    "/api/dcim/devices/<uuid>/interfaces/": "Device interfaces: filter by 'device' UUID only. "
        "Interface names are not valid filter values at this endpoint.",
    "/api/ipam/ip-addresses/": "IP address filter: use 'address' for exact, "
        "'family' for inet/inet6, 'device' for device UUID. "
        "Interface name is not a valid filter — use interface_id instead.",
    "/api/ipam/vlans/": "VLAN filter: use 'vid' (integer) or 'name'. "
        "Scope to a location with 'location' UUID for accuracy.",
    "/api/ipam/prefixes/": "Prefix filter: use 'prefix' for CIDR, "
        "'vlan_vid' for VLAN number, 'location' UUID to scope results.",
    "/api/tenancy/tenants/": "Tenant filter: use 'name' or 'slug'. "
        "Tenant groups are filtered via 'group' name, not group UUID.",
    "/api/extras/jobs/": "Job filter: use 'name' or 'slug'. "
        "Jobs may require appropriate permissions to appear in results.",
    "/api/plugins/golden_config/": "Golden Config plugin endpoints: ensure the "
        "plugin is installed and the service account has plugin permissions.",
}

# Status-code fallback hints for ERR-04: unknown endpoints get generic guidance
# keyed by HTTP status code.
STATUS_CODE_HINTS: dict[int, str] = {
    429: "Rate limited — retry after exponential backoff or check Nautobot task schedule",
    500: "Nautobot server error — check Nautobot service health and application logs",
    502: "Nautobot gateway error — check Nautobot service health and reverse proxy logs",
    503: "Nautobot unavailable — check service status and network connectivity",
    504: "Nautobot request timed out — try a narrower filter or smaller query",
    422: "Unprocessable entity — field values don't match Nautobot API schema; check data types",
}


def _get_hint_for_request(
    req: Any,
    operation: str,
    model_name: str,
    status_code: int,
) -> str:
    """Resolve the best available hint for a failed API request.

    Strategy (in priority order):
    1. Longest-match ERROR_HINTS entry for the request URL path
    2. STATUS_CODE_HINTS entry for the HTTP status code
    3. Generic fallback string

    Args:
        req: requests.Response object (or Any from pynautobot RequestError.req).
             May be None if the error has no associated response.
        operation: Operation name (e.g., "list", "create", "filter").
        model_name: Model name (e.g., "Device", "Interface").
        status_code: HTTP status code integer.

    Returns:
        A hint string — always non-empty.
    """
    # 1. Try endpoint-specific hint from ERROR_HINTS
    if req is not None and hasattr(req, "url"):
        url = getattr(req, "url", "") or ""
        # Longest-match: sort keys by length descending, pick first match
        for hint_key in sorted(ERROR_HINTS.keys(), key=len, reverse=True):
            if hint_key in url:
                return ERROR_HINTS[hint_key]

    # 2. Try status-code fallback
    if status_code in STATUS_CODE_HINTS:
        return STATUS_CODE_HINTS[status_code]

    # 3. Generic fallback derived from operation + model
    fallbacks = {
        "list": f"Check that {model_name.lower()} objects exist in Nautobot and the filter parameters are valid",
        "get": f"Verify the {model_name.lower()} ID or name is correct",
        "create": f"Check required fields for {model_name.lower()} match the Nautobot API schema",
        "update": f"Verify the {model_name.lower()} exists and the update data is valid",
        "delete": f"Verify the {model_name.lower()} exists and is not protected",
    }
    return fallbacks.get(
        operation,
        f"Check {model_name.lower()} data and Nautobot server health",
    )


class NautobotClient:
    """Nautobot API client with connection management and error handling.

    Wraps pynautobot.api with:
    - Lazy connection initialization
    - Structured error translation
    - Retry support via pynautobot's built-in retries
    - Endpoint property accessors
    """

    def __init__(
        self,
        profile: Optional[NautobotProfile] = None,
        settings: Optional[NautobotSettings] = None,
    ) -> None:
        """Initialize client with a connection profile.

        Args:
            profile: Direct connection profile. Takes priority over settings.
            settings: Application settings to extract active profile from.
                If neither profile nor settings provided, auto-discovers from
                env vars and config files.
        """
        if profile is not None:
            self._profile = profile
        elif settings is not None:
            self._profile = settings.get_active_profile()
        else:
            discovered = NautobotSettings.discover()
            self._profile = discovered.get_active_profile()

        self._api: Optional[pynautobot.api] = None

    @property
    def api(self) -> pynautobot.api:
        """Lazily initialized pynautobot API instance."""
        if self._api is None:
            self._api = pynautobot.api(
                url=self._profile.url,
                token=self._profile.token,
                retries=3,
            )
            self._api.http_session.verify = self._profile.verify_ssl

            if self._profile.api_version:
                self._api.api_version = self._profile.api_version

        return self._api

    def validate_connection(self) -> dict[str, str]:
        """Validate connectivity to the Nautobot server.

        Returns:
            Dict with status, version, and url info.

        Raises:
            NautobotConnectionError: If server is unreachable.
            NautobotAuthenticationError: If token is invalid.
        """
        try:
            status = self.api.status()
            version = status.get("nautobot-version", "unknown")
            return {
                "status": "connected",
                "version": version,
                "url": self._profile.url,
            }
        except RequestsConnectionError as e:
            raise NautobotConnectionError(
                message=f"Cannot connect to {self._profile.url}",
                hint="Check NAUTOBOT_URL setting and ensure the server is reachable",
            ) from e
        except pynautobot.core.query.RequestError as e:
            if hasattr(e, "req") and hasattr(e.req, "status_code"):
                if e.req.status_code in (401, 403):
                    raise NautobotAuthenticationError(
                        message=f"Authentication failed for {self._profile.url}",
                        hint="Check NAUTOBOT_TOKEN — ensure it's valid and not expired",
                    ) from e
            raise NautobotAPIError(
                message=f"API error during connection validation: {e}",
                status_code=getattr(getattr(e, "req", None), "status_code", 0),
            ) from e
        except Exception as e:
            raise NautobotConnectionError(
                message=f"Unexpected error connecting to {self._profile.url}: {e}",
                hint="Check NAUTOBOT_URL setting and network connectivity",
            ) from e

    def _handle_api_error(
        self,
        error: Exception,
        operation: str,
        model_name: str,
    ) -> None:
        """Translate pynautobot exceptions to custom exceptions.

        Args:
            error: The original exception from pynautobot.
            operation: The operation being performed (e.g., "list", "get").
            model_name: The model name (e.g., "Device", "Interface").

        Raises:
            NautobotNotFoundError: For 404 errors.
            NautobotAuthenticationError: For 401/403 errors.
            NautobotValidationError: For 400 errors.
            NautobotAPIError: For all other API errors.
        """
        if isinstance(error, pynautobot.core.query.RequestError):
            req_obj = getattr(error, "req", None)
            status_code = getattr(req_obj, "status_code", 0) if req_obj else 0

            if status_code == 404:
                raise NautobotNotFoundError(
                    message=f"{model_name} not found during {operation}",
                    hint=f"Verify the {model_name.lower()} exists in Nautobot",
                ) from error

            if status_code in (401, 403):
                raise NautobotAuthenticationError(
                    message=f"Authentication failed during {operation} on {model_name}",
                ) from error

            # ERR-01: Parse DRF 400 body — handle None req by using effective_status=400
            if status_code == 400 or (req_obj is None and not isinstance(error, RequestsConnectionError)):
                # When req_obj is None, we can't definitively determine the status.
                # Treat as 400 (validation error) since that's the most common case.
                effective_status = status_code if status_code == 400 else 400

                field_errors: list[dict[str, str]] = []

                if req_obj is not None:
                    raw_body = getattr(req_obj, "text", None)
                    if raw_body:
                        import json as _json
                        try:
                            body = _json.loads(raw_body)
                            # Handle DRF error shapes:
                            # {"field": ["msg"]}  or  {"field": "msg"}  or  {"detail": "string"}
                            # Normalize non_field_errors and detail to _detail for uniform handling
                            if isinstance(body, dict):
                                for field, messages in body.items():
                                    normalized_field = "_detail" if field in ("detail", "non_field_errors") else field
                                    if isinstance(messages, list):
                                        for msg in messages:
                                            field_errors.append({"field": normalized_field, "error": str(msg)})
                                    elif isinstance(messages, str):
                                        field_errors.append({"field": normalized_field, "error": messages})
                                    else:
                                        field_errors.append({"field": normalized_field, "error": str(messages)})
                            elif isinstance(body, str):
                                field_errors.append({"field": "_detail", "error": body})
                        except (ValueError, TypeError):
                            pass  # Non-JSON body — fall through to generic message

                hint = _get_hint_for_request(req_obj, operation, model_name, effective_status)

                raise NautobotValidationError(
                    message=f"Validation error during {operation} on {model_name}: {error}",
                    hint=hint,
                    errors=field_errors if field_errors else None,
                ) from error

            hint = _get_hint_for_request(req_obj, operation, model_name, status_code)

            raise NautobotAPIError(
                message=f"API error during {operation} on {model_name}: {error}",
                status_code=status_code,
                hint=hint,
            ) from error

        if isinstance(error, RequestsConnectionError):
            raise NautobotConnectionError(
                message=f"Connection lost during {operation} on {model_name}",
            ) from error

        raise NautobotAPIError(
            message=f"Unexpected error during {operation} on {model_name}: {error}",
        ) from error

    @property
    def dcim(self):
        """Access DCIM app endpoints (devices, interfaces, locations, etc.)."""
        return self.api.dcim

    @property
    def ipam(self):
        """Access IPAM app endpoints (prefixes, IP addresses, VLANs, etc.)."""
        return self.api.ipam

    @property
    def tenancy(self):
        """Access Tenancy app endpoints (tenants, tenant groups)."""
        return self.api.tenancy

    @property
    def circuits(self):
        """Access Circuits app endpoints (circuits, providers, etc.)."""
        return self.api.circuits

    @property
    def golden_config(self):
        """Access Golden Config plugin endpoints.

        Returns pynautobot plugin app for golden-config.
        Raises NautobotAPIError if plugin is not installed.
        """
        try:
            return self.api.plugins.golden_config
        except Exception as e:
            raise NautobotAPIError(
                message="Golden Config plugin not available",
                hint="Ensure nautobot-golden-config is installed on your Nautobot instance",
            ) from e

    @property
    def cms(self):
        """Access NetNam CMS Core plugin endpoints.

        Returns pynautobot plugin app for netnam-cms-core.
        Raises NautobotAPIError if plugin is not installed.
        """
        try:
            return self.api.plugins.netnam_cms_core
        except Exception as e:
            raise NautobotAPIError(
                message="NetNam CMS Core plugin not available",
                hint="Ensure netnam-cms-core is installed on your Nautobot instance",
            ) from e
