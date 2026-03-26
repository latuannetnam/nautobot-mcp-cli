"""Workflow registry and dispatch engine.

Maps 10 workflow IDs to their composite domain functions, validates
parameters, performs normalization, and wraps results in a common
response envelope.

Usage:
    from nautobot_mcp.workflows import WORKFLOW_REGISTRY, run_workflow

    result = run_workflow(client, workflow_id="bgp_summary", params={"device": "core-rtr-01"})
    # {"workflow": "bgp_summary", "device": "core-rtr-01", "status": "ok", "data": {...}, ...}
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from nautobot_mcp.catalog.workflow_stubs import WORKFLOW_STUBS
from nautobot_mcp.cms.cms_drift import compare_bgp_neighbors, compare_static_routes
from nautobot_mcp.cms.firewalls import get_device_firewall_summary
from nautobot_mcp.cms.interfaces import get_interface_detail
from nautobot_mcp.cms.routing import get_device_bgp_summary, get_device_routing_table
from nautobot_mcp.drift import compare_device
from nautobot_mcp.exceptions import NautobotValidationError
from nautobot_mcp.models.parser import ParsedConfig
from nautobot_mcp.onboarding import onboard_config
from nautobot_mcp.verification import verify_config_compliance, verify_data_model

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


# ---------------------------------------------------------------------------
# Workflow Registry
# ---------------------------------------------------------------------------


WORKFLOW_REGISTRY: dict[str, dict] = {
    "bgp_summary": {
        "function": get_device_bgp_summary,
        "param_map": {"device": "device", "detail": "detail"},
        "required": ["device"],
    },
    "routing_table": {
        "function": get_device_routing_table,
        "param_map": {"device": "device", "detail": "detail"},
        "required": ["device"],
    },
    "firewall_summary": {
        "function": get_device_firewall_summary,
        "param_map": {"device": "device", "detail": "detail"},
        "required": ["device"],
    },
    "interface_detail": {
        "function": get_interface_detail,
        "param_map": {"device": "device", "include_arp": "include_arp"},
        "required": ["device"],
    },
    "onboard_config": {
        "function": onboard_config,
        "param_map": {
            "config_data": "parsed_config",
            "device_name": "device_name",
            "dry_run": "dry_run",
        },
        "required": ["config_data", "device_name"],
        "transforms": {
            "config_data": lambda d: ParsedConfig.model_validate(d),
        },
    },
    "compare_device": {
        "function": compare_device,
        "param_map": {
            "device_name": "device_name",
            "live_data": "interfaces_data",
        },
        "required": ["device_name", "live_data"],
    },
    "verify_data_model": {
        "function": verify_data_model,
        "param_map": {
            "device_name": "device_name",
            "parsed_config": "parsed_config",
        },
        "required": ["device_name", "parsed_config"],
    },
    "verify_compliance": {
        "function": verify_config_compliance,
        "param_map": {"device_name": "device_name"},
        "required": ["device_name"],
    },
    "compare_bgp": {
        "function": compare_bgp_neighbors,
        "param_map": {
            "device_name": "device_name",
            "live_neighbors": "live_neighbors",
        },
        "required": ["device_name", "live_neighbors"],
    },
    "compare_routes": {
        "function": compare_static_routes,
        "param_map": {
            "device_name": "device_name",
            "live_routes": "live_routes",
        },
        "required": ["device_name", "live_routes"],
    },
}


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _serialize_result(obj: Any) -> Any:
    """Serialize workflow result to a JSON-safe structure.

    Handles:
    - Pydantic BaseModel → .model_dump()
    - Dataclass → dataclasses.asdict()
    - dict → pass-through
    - Anything else → str(obj)
    """
    try:
        # Pydantic v2: has model_dump
        if hasattr(obj, "model_dump") and callable(obj.model_dump):
            return obj.model_dump()
    except Exception:
        pass

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)

    if isinstance(obj, dict):
        return obj

    if isinstance(obj, (list, tuple)):
        return [_serialize_result(item) for item in obj]

    return str(obj)


def _build_envelope(
    workflow_id: str,
    params: dict,
    data: Any = None,
    error: Exception | str | None = None,
    warnings: list[dict[str, str]] | None = None,
) -> dict:
    """Wrap a workflow result in a standard response envelope.

    Supports three-tier status:
    - ``"error"``  — workflow function raised an exception (data is None)
    - ``"partial"`` — function returned data but some enrichment queries failed (warnings present)
    - ``"ok"``     — full success, no warnings

    Args:
        workflow_id: Workflow name.
        params: Agent-facing parameter dict (used to extract device name).
        data: Serialized result data, or None on hard error.
        error: Exception (hard error) or summary string (partial error). None when ok.
        warnings: List of warning dicts from WarningCollector, or None.

    Returns:
        dict with keys: workflow, device, status, data, error, warnings, timestamp
    """
    device = params.get("device") or params.get("device_name")

    # Three-tier status: error > partial > ok
    if error and data is None:
        status = "error"
    elif warnings:
        status = "partial"
    else:
        status = "ok"

    # error field: exception string when error, summary string when partial, None when ok
    if error and data is None:
        error_str = str(error)
    elif isinstance(error, str):
        error_str = error  # summary string for partial
    else:
        error_str = None

    return {
        "workflow": workflow_id,
        "device": device,
        "status": status,
        "data": data,
        "error": error_str,
        "warnings": warnings if warnings is not None else [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Dispatch engine
# ---------------------------------------------------------------------------


def run_workflow(
    client: "NautobotClient",
    workflow_id: str,
    params: dict,
) -> dict:
    """Execute a named workflow and return a standard response envelope.

    Validates the workflow_id against the registry, checks required params,
    maps agent-facing param names to function argument names, applies any
    type transforms (e.g., dict → ParsedConfig), injects the client, calls
    the function, serializes the result, and wraps everything in a common
    response envelope.

    Args:
        client: NautobotClient instance.
        workflow_id: Workflow name (e.g., "bgp_summary", "compare_device").
        params: Agent-facing parameter dict matching the workflow stub signature.

    Returns:
        Envelope dict with keys: workflow, device, status, data, error, timestamp.

    Raises:
        NautobotValidationError: If workflow_id is unknown or required params are missing.
    """
    # 1. Validate workflow_id
    if workflow_id not in WORKFLOW_REGISTRY:
        available = ", ".join(sorted(WORKFLOW_REGISTRY.keys()))
        raise NautobotValidationError(
            f"Unknown workflow: '{workflow_id}'. "
            f"Available workflows: {available}"
        )

    entry = WORKFLOW_REGISTRY[workflow_id]
    required = entry.get("required", [])
    param_map = entry.get("param_map", {})
    transforms = entry.get("transforms", {})
    func = entry["function"]

    # 2. Validate required params
    missing = [p for p in required if p not in params]
    if missing:
        raise NautobotValidationError(
            f"Workflow '{workflow_id}' missing required params: {missing}. "
            f"Received: {list(params.keys())}"
        )

    # 3. Map agent-facing names → function argument names
    kwargs: dict = {}
    for agent_name, func_name in param_map.items():
        if agent_name in params:
            value = params[agent_name]
            # 4. Apply transforms if defined
            if agent_name in transforms:
                value = transforms[agent_name](value)
            kwargs[func_name] = value

    # 5. Call function with client as first positional arg
    try:
        raw_result = func(client, **kwargs)

        # Composite functions return (result, warnings) tuples
        if isinstance(raw_result, tuple) and len(raw_result) == 2:
            result, warnings_list = raw_result
        else:
            result = raw_result
            warnings_list = []

        serialized = _serialize_result(result)

        # Build envelope with warnings if present
        if warnings_list:
            failed = len(warnings_list)
            error_summary = f"{failed} enrichment queries failed"
            return _build_envelope(
                workflow_id, params,
                data=serialized,
                error=error_summary,
                warnings=warnings_list,
            )
        return _build_envelope(workflow_id, params, data=serialized)
    except Exception as e:
        return _build_envelope(workflow_id, params, error=e)
