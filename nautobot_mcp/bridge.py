"""REST Bridge — universal CRUD dispatcher for Nautobot API.

Routes endpoint calls to the correct backend (pynautobot core or CMS plugin)
based on endpoint prefix, with validation, pagination, and error hints.
"""

from __future__ import annotations

import difflib
import logging
from typing import Optional

from nautobot_mcp.catalog.engine import get_catalog
from nautobot_mcp.catalog.core_endpoints import CORE_ENDPOINTS
from nautobot_mcp.cms.client import CMS_ENDPOINTS, resolve_device_id, get_cms_endpoint
from nautobot_mcp.exceptions import (
    NautobotMCPError,
    NautobotNotFoundError,
    NautobotValidationError,
)

logger = logging.getLogger(__name__)

MAX_LIMIT = 200  # Hard cap to prevent context window flooding
DEFAULT_LIMIT = 50


def _build_valid_endpoints() -> list[str]:
    """Build flat list of all valid endpoint strings for fuzzy matching."""
    endpoints = []
    for domain, entries in CORE_ENDPOINTS.items():
        for name, entry in entries.items():
            endpoints.append(entry["endpoint"])
    for endpoint_name in CMS_ENDPOINTS:
        endpoints.append(f"cms:{endpoint_name}")
    return endpoints


def _suggest_endpoint(invalid_endpoint: str) -> list[str]:
    """Find closest matching valid endpoints using difflib."""
    valid = _build_valid_endpoints()
    return difflib.get_close_matches(invalid_endpoint, valid, n=3, cutoff=0.4)


def _validate_endpoint(endpoint: str) -> None:
    """Validate endpoint exists in catalog. Raises NautobotValidationError if not."""
    # Check core endpoints
    if endpoint.startswith("/api/"):
        for domain, entries in CORE_ENDPOINTS.items():
            for name, entry in entries.items():
                if entry["endpoint"] == endpoint:
                    return
    # Check CMS endpoints
    elif endpoint.startswith("cms:"):
        cms_key = endpoint[4:]  # Strip "cms:" prefix
        if cms_key in CMS_ENDPOINTS:
            return
    # Not found — build error with suggestions
    suggestions = _suggest_endpoint(endpoint)
    hint = f"Did you mean: {', '.join(suggestions)}" if suggestions else (
        "Use nautobot_api_catalog() to see available endpoints"
    )
    raise NautobotValidationError(
        message=f"Unknown endpoint: '{endpoint}'",
        hint=hint,
    )


def _validate_method(method: str, endpoint: str) -> str:
    """Validate and normalize HTTP method. Returns uppercase method."""
    method = method.upper().strip()
    valid_methods = {"GET", "POST", "PATCH", "DELETE"}
    if method not in valid_methods:
        raise NautobotValidationError(
            message=f"Invalid method: '{method}'",
            hint=f"Valid methods: GET, POST, PATCH, DELETE",
        )
    return method


def _parse_core_endpoint(endpoint: str) -> tuple[str, str]:
    """Parse /api/{app}/{endpoint}/ into (app_name, endpoint_name).

    Returns tuple of (app, endpoint) for pynautobot accessor lookup.
    E.g., "/api/dcim/devices/" → ("dcim", "devices")
         "/api/dcim/device-types/" → ("dcim", "device_types")
    """
    parts = endpoint.strip("/").split("/")
    # parts = ["api", "dcim", "devices"] or ["api", "dcim", "device-types"]
    if len(parts) < 3:
        raise NautobotValidationError(
            message=f"Invalid core endpoint format: '{endpoint}'",
            hint="Core endpoints should be: /api/{app}/{endpoint}/",
        )
    app_name = parts[1]   # "dcim"
    ep_name = parts[2]    # "devices" or "device-types"
    # Convert hyphenated names to underscore (pynautobot convention)
    ep_name = ep_name.replace("-", "_")
    return app_name, ep_name


def _execute_core(client, app_name: str, ep_name: str, method: str,
                  params: dict | None, data: dict | None,
                  obj_id: str | None, limit: int) -> dict:
    """Execute a core Nautobot API operation via pynautobot."""
    # Get pynautobot app accessor (e.g., client.api.dcim)
    app = getattr(client.api, app_name, None)
    if app is None:
        raise NautobotValidationError(
            message=f"Unknown Nautobot app: '{app_name}'",
            hint=f"Valid apps: dcim, ipam, circuits, tenancy",
        )
    # Get endpoint accessor (e.g., client.api.dcim.devices)
    endpoint_accessor = getattr(app, ep_name, None)
    if endpoint_accessor is None:
        raise NautobotValidationError(
            message=f"Unknown endpoint '{ep_name}' in app '{app_name}'",
            hint=f"Use nautobot_api_catalog(domain='{app_name}') to see available endpoints",
        )

    if method == "GET":
        if obj_id:
            record = endpoint_accessor.get(id=obj_id)
            if record is None:
                raise NautobotNotFoundError(
                    message=f"Object '{obj_id}' not found",
                    hint="Check the UUID is correct",
                )
            return {"count": 1, "results": [dict(record)]}
        # List operation with optional filters
        if params:
            records = list(endpoint_accessor.filter(**params))
        else:
            records = list(endpoint_accessor.all())
        total = len(records)
        capped_limit = min(limit, MAX_LIMIT)
        truncated = total > capped_limit
        results = [dict(r) for r in records[:capped_limit]]
        response = {"count": len(results), "results": results}
        if truncated:
            response["truncated"] = True
            response["total_available"] = total
        return response

    elif method == "POST":
        if not data:
            raise NautobotValidationError(
                message="POST requires 'data' parameter",
                hint="Provide the fields to create as 'data' dict",
            )
        record = endpoint_accessor.create(**data)
        return {"count": 1, "results": [dict(record)]}

    elif method == "PATCH":
        if not obj_id:
            raise NautobotValidationError(
                message="PATCH requires 'id' parameter",
                hint="Provide the UUID of the object to update",
            )
        record = endpoint_accessor.get(id=obj_id)
        if record is None:
            raise NautobotNotFoundError(
                message=f"Object '{obj_id}' not found for update",
                hint="Check the UUID is correct",
            )
        if data:
            for key, value in data.items():
                setattr(record, key, value)
            record.save()
        return {"count": 1, "results": [dict(record)]}

    elif method == "DELETE":
        if not obj_id:
            raise NautobotValidationError(
                message="DELETE requires 'id' parameter",
                hint="Provide the UUID of the object to delete",
            )
        record = endpoint_accessor.get(id=obj_id)
        if record is None:
            raise NautobotNotFoundError(
                message=f"Object '{obj_id}' not found for deletion",
                hint="Check the UUID is correct",
            )
        record.delete()
        return {"count": 0, "results": [], "deleted": obj_id}


def _execute_cms(client, cms_key: str, method: str,
                 params: dict | None, data: dict | None,
                 obj_id: str | None, limit: int) -> dict:
    """Execute a CMS plugin operation via pynautobot CMS accessor."""
    # Resolve device name to UUID if device param provided
    effective_params = dict(params) if params else {}
    if "device" in effective_params:
        device_val = effective_params["device"]
        effective_params["device"] = resolve_device_id(client, device_val)

    # Get CMS endpoint accessor
    endpoint_accessor = get_cms_endpoint(client, cms_key)

    if method == "GET":
        if obj_id:
            record = endpoint_accessor.get(id=obj_id)
            if record is None:
                model_name = CMS_ENDPOINTS.get(cms_key, cms_key)
                raise NautobotNotFoundError(
                    message=f"{model_name} '{obj_id}' not found",
                    hint=f"Check the UUID is correct",
                )
            return {"count": 1, "results": [dict(record)]}
        # List with filters
        if effective_params:
            records = list(endpoint_accessor.filter(**effective_params))
        else:
            records = list(endpoint_accessor.all())
        total = len(records)
        capped_limit = min(limit, MAX_LIMIT)
        truncated = total > capped_limit
        results = [dict(r) for r in records[:capped_limit]]
        response = {"count": len(results), "results": results}
        if truncated:
            response["truncated"] = True
            response["total_available"] = total
        return response

    elif method == "POST":
        if not data:
            raise NautobotValidationError(
                message="POST requires 'data' parameter",
                hint="Provide the fields to create as 'data' dict",
            )
        # Resolve device in data too
        effective_data = dict(data)
        if "device" in effective_data:
            effective_data["device"] = resolve_device_id(client, effective_data["device"])
        record = endpoint_accessor.create(**effective_data)
        return {"count": 1, "results": [dict(record)]}

    elif method == "PATCH":
        if not obj_id:
            raise NautobotValidationError(
                message="PATCH requires 'id' parameter",
                hint="Provide the UUID of the object to update",
            )
        record = endpoint_accessor.get(id=obj_id)
        if record is None:
            model_name = CMS_ENDPOINTS.get(cms_key, cms_key)
            raise NautobotNotFoundError(
                message=f"{model_name} '{obj_id}' not found for update",
            )
        if data:
            for key, value in data.items():
                setattr(record, key, value)
            record.save()
        return {"count": 1, "results": [dict(record)]}

    elif method == "DELETE":
        if not obj_id:
            raise NautobotValidationError(
                message="DELETE requires 'id' parameter",
                hint="Provide the UUID of the object to delete",
            )
        record = endpoint_accessor.get(id=obj_id)
        if record is None:
            model_name = CMS_ENDPOINTS.get(cms_key, cms_key)
            raise NautobotNotFoundError(
                message=f"{model_name} '{obj_id}' not found for deletion",
            )
        record.delete()
        return {"count": 0, "results": [], "deleted": obj_id}


def call_nautobot(
    client,
    endpoint: str,
    method: str = "GET",
    params: Optional[dict] = None,
    data: Optional[dict] = None,
    id: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> dict:
    """Execute a Nautobot API call via the REST bridge.

    Routes to the correct backend based on endpoint prefix:
    - /api/* → pynautobot core accessor
    - cms:* → CMS plugin helpers

    Args:
        client: NautobotClient instance.
        endpoint: API endpoint path ("/api/dcim/devices/") or CMS key ("cms:juniper_static_routes").
        method: HTTP method — GET, POST, PATCH, DELETE.
        params: Query filters for GET operations.
        data: Request body for POST/PATCH operations.
        id: Object UUID for single-object operations.
        limit: Max results for GET list operations (default 50, hard cap 200).

    Returns:
        Wrapped response dict with count, results, endpoint, method, and optional truncation metadata.
    """
    # Validate endpoint exists in catalog
    _validate_endpoint(endpoint)

    # Validate and normalize method
    method = _validate_method(method, endpoint)

    # Cap limit
    effective_limit = min(limit, MAX_LIMIT) if limit > 0 else DEFAULT_LIMIT

    try:
        # Route to correct backend
        if endpoint.startswith("/api/"):
            app_name, ep_name = _parse_core_endpoint(endpoint)
            result = _execute_core(client, app_name, ep_name, method,
                                   params, data, id, effective_limit)
        elif endpoint.startswith("cms:"):
            cms_key = endpoint[4:]  # Strip "cms:" prefix
            result = _execute_cms(client, cms_key, method,
                                  params, data, id, effective_limit)
        else:
            raise NautobotValidationError(
                message=f"Unsupported endpoint prefix: '{endpoint}'",
                hint="Endpoints must start with '/api/' or 'cms:'. "
                     "Use nautobot_api_catalog() to see available endpoints.",
            )

        # Add request context to response
        result["endpoint"] = endpoint
        result["method"] = method
        return result

    except NautobotMCPError:
        raise  # Re-raise our structured errors
    except Exception as e:
        # Translate unexpected errors
        client._handle_api_error(e, method.lower(), endpoint)
        raise  # _handle_api_error always raises, but satisfy type checker
