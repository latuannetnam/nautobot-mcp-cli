"""Base Nautobot API client wrapping pynautobot.

Provides connection management, error translation, and endpoint access.
Connection is lazy — validated on first API call, not on initialization.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

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
            status_code = getattr(getattr(error, "req", None), "status_code", 0)

            if status_code == 404:
                raise NautobotNotFoundError(
                    message=f"{model_name} not found during {operation}",
                    hint=f"Verify the {model_name.lower()} exists in Nautobot",
                ) from error

            if status_code in (401, 403):
                raise NautobotAuthenticationError(
                    message=f"Authentication failed during {operation} on {model_name}",
                ) from error

            if status_code == 400:
                raise NautobotValidationError(
                    message=f"Validation error during {operation} on {model_name}: {error}",
                    hint=f"Check required fields for {model_name}",
                ) from error

            raise NautobotAPIError(
                message=f"API error during {operation} on {model_name}: {error}",
                status_code=status_code,
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
                code="PLUGIN_NOT_FOUND",
                hint="Ensure nautobot-golden-config is installed on your Nautobot instance",
            ) from e
