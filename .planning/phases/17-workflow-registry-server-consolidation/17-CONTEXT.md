# Phase 17 – Workflow Registry & Server Consolidation — Context

Date: 2026-03-24

## Overview

Phase 17 implements the `run_workflow` tool and registry to wrap 10 existing
composite domain functions, then rewrites `server.py` from ~165 individual tool
definitions down to 3 tools (`nautobot_api_catalog`, `call_nautobot`,
`run_workflow`).

## Gray Areas Discussed

### 1. Parameter Normalization — `device` vs `device_name`

**Decision: Option B — Keep the split visible (no normalization)**

The naming reflects a **real semantic difference**:

| Category | Param | Accepts | Internal Path |
|---|---|---|---|
| CMS Composites (bgp_summary, routing_table, firewall_summary, interface_detail) | `device` | name **or** UUID | Passes to CMS list functions → `resolve_device_id()` |
| Business Logic (onboard_config, verify_compliance, verify_data_model, compare_device) | `device_name` | hostname only | Name-based lookups (`get_device_ips(device_name=...)`) |
| CMS Drift (compare_bgp, compare_routes) | `device_name` | hostname only | Assigned to adapter `.device_name` |

The registry passes through parameter names as documented in `WORKFLOW_STUBS`.
No automatic translation. Agents see `device` for CMS workflows and
`device_name` for business logic workflows — this prevents agents from
accidentally passing UUIDs to functions that only accept hostnames.

### 2. `onboard_config` Parameter Type

**Decision: Accept structured dict**

The workflow stub exposes `config_data: dict` (not `config_json: str`).
The wrapper calls `ParsedConfig.model_validate(config_data)` to convert
the agent-supplied dict into the Pydantic model the underlying function
expects.

Update `WORKFLOW_STUBS` to reflect:
```python
"onboard_config": {
    "params": {
        "config_data": "dict (required, ParsedConfig schema)",
        "device_name": "str (required)",
        "dry_run": "bool (optional, default true)",
    },
    ...
}
```

### 3. `compare_device` Input Shape

**Decision: Normalize to dict only**

The workflow wrapper only accepts the flat-map dict shape:
```python
{"ae0.0": {"ips": ["10.1.1.1/30"], "vlans": [100]}}
```

The underlying `compare_device()` function auto-detects dict vs list input,
but the workflow API simplifies to dict-only for agent clarity.

Update `WORKFLOW_STUBS`:
```python
"compare_device": {
    "params": {
        "device_name": "str (required)",
        "live_data": "dict (required, {iface_name: {ips: [...], vlans: [...]}})",
    },
    ...
}
```

### 4. Server.py Rewrite Strategy

**`get_client()` singleton**: Keep in `server.py`. Only the 3 tool handlers
need it — `bridge.py` and `workflows.py` receive client as a parameter from
the tool handler. No separate `client_factory.py` needed.

**Old `server.py`**: Delete cleanly. It's in git history if needed. No
`server_legacy.py` preservation.

**`handle_error()`**: Keep in `server.py` as a utility for the 3 tool
handlers. The same `NautobotNotFoundError → ToolError` translation applies
to all 3 tools.

### 5. Registry vs Stubs Architecture

**Decision: Separate (Option B) with sync guard**

Two distinct modules serve two distinct audiences:

| Module | Purpose | Import Weight |
|---|---|---|
| `catalog/workflow_stubs.py` | Agent-facing metadata (params, descriptions, aggregates) | Zero — pure dict literal |
| `nautobot_mcp/workflows.py` | Runtime dispatch (function refs, param mapping, execution) | Heavy — imports all domain modules |

**Rationale**: Merging would make `get_catalog()` pull in the entire domain
stack (routing, firewalls, verification, onboarding, drift, cms_drift, plus
NautobotClient, DiffSync, ParsedConfig, etc.) just to serve parameter
descriptions. The current catalog engine imports only lightweight metadata.

**Sync guard**: A test `test_registry_matches_stubs()` asserts:
```python
assert set(WORKFLOW_STUBS.keys()) == set(WORKFLOW_REGISTRY.keys())
```

### 6. Response Envelope

**Decision: Common envelope**

All `run_workflow` outputs use a standard wrapper:
```python
{
    "workflow": "bgp_summary",
    "device": "core-rtr-01",
    "status": "ok",       # or "error"
    "data": { ... },      # domain-specific output
    "timestamp": "2026-03-24T13:00:00Z",
    "error": None,        # or error message string
}
```

Domain objects are serialized via `.model_dump()` (Pydantic) or
`dataclasses.asdict()` into the `data` field. Error cases populate `error`
and set `status: "error"` with `data: None`.

## Architecture Summary

```
nautobot_mcp/
├── server.py              # NEW — 3 tools: catalog, bridge, workflow (~200 lines)
├── workflows.py           # NEW — registry + dispatch + envelope
├── bridge.py              # Existing (Phase 16)
├── catalog/
│   ├── engine.py          # Existing (Phase 15)
│   ├── core_endpoints.py  # Existing
│   ├── cms_discovery.py   # Existing
│   └── workflow_stubs.py  # Updated — param corrections
├── cms/                   # Unchanged
├── verification.py        # Unchanged
├── onboarding.py          # Unchanged
└── drift.py               # Unchanged
```

## Workflow Registry Structure

```python
WORKFLOW_REGISTRY = {
    "bgp_summary": {
        "function": get_device_bgp_summary,
        "param_map": {"device": "device", "detail": "detail"},
    },
    "onboard_config": {
        "function": onboard_config,
        "param_map": {"config_data": "_parsed_config", "device_name": "device_name", "dry_run": "dry_run"},
        "transforms": {"config_data": lambda d: ParsedConfig.model_validate(d)},
    },
    # ... etc
}
```

## Requirements Covered

- **WFL-01**: Workflow registry maps 10 workflow IDs to functions
- **WFL-02**: Registry validates required params before dispatch
- **WFL-03**: Parameter mapping translates agent-facing names to function args
- **WFL-04**: Common response envelope wraps all workflow outputs
- **WFL-05**: `device` vs `device_name` split preserved (no normalization)
- **WFL-06**: `run_workflow` dispatches and returns envelope
- **SVR-01**: `server.py` reduced to 3 tool definitions
- **SVR-02**: `get_client()` singleton stays in `server.py`
- **SVR-03**: `handle_error()` translates errors for all 3 tools
- **SVR-04**: Old 165-tool server.py deleted (git history preserved)
- **TST-04**: `test_workflows.py` — registry dispatch, param validation, envelope
- **TST-05**: `test_server.py` — rewritten for 3-tool interface
