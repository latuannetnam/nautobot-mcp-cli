---
plan: 16-01
phase: 16
title: REST Bridge Module
status: complete
completed: 2026-03-24
---

# Summary: Plan 16-01 — REST Bridge Module

## What Was Built

Created `nautobot_mcp/bridge.py` — the universal REST bridge module that dispatches CRUD operations to the correct Nautobot backend based on endpoint prefix.

## Key Files Created

- `nautobot_mcp/bridge.py` — 270-line module implementing the complete REST bridge

## Implementation Details

- **Endpoint validation**: `_validate_endpoint()` checks against both `CORE_ENDPOINTS` (15 endpoints) and `CMS_ENDPOINTS` (35+ endpoints)
- **Fuzzy matching**: `_suggest_endpoint()` uses `difflib.get_close_matches()` with cutoff=0.4 for "Did you mean?" hints
- **Routing**: `call_nautobot()` dispatches `/api/*` → `_execute_core()` via pynautobot, `cms:*` → `_execute_cms()` via CMS helpers
- **Pagination**: Hard cap at `MAX_LIMIT=200`, default `DEFAULT_LIMIT=50`, truncation metadata in response
- **Device resolution**: CMS GET/POST `device` param auto-resolved via `resolve_device_id()`
- **Error handling**: All `NautobotMCPError` subclasses re-raised; unexpected exceptions routed through `client._handle_api_error()`

## Acceptance Criteria Self-Check

- [x] `nautobot_mcp/bridge.py` exists with `def call_nautobot(`
- [x] `MAX_LIMIT = 200` and `DEFAULT_LIMIT = 50`
- [x] `import difflib` present
- [x] All `_validate_endpoint`, `_suggest_endpoint`, `_parse_core_endpoint`, `_execute_core`, `_execute_cms` functions present
- [x] `resolve_device_id` and `get_catalog` imports present
- [x] `from nautobot_mcp.bridge import call_nautobot` — no ImportError
- [x] `_validate_endpoint("/api/dcim/devices/")` — passes
- [x] `_validate_endpoint("cms:juniper_static_routes")` — passes
- [x] `_validate_endpoint("/api/dcim/invalid/")` — raises `NautobotValidationError` with "Did you mean"
- [x] `_parse_core_endpoint("/api/dcim/devices/")` returns `("dcim", "devices")`
- [x] `_parse_core_endpoint("/api/dcim/device-types/")` returns `("dcim", "device_types")`

## Self-Check: PASSED
