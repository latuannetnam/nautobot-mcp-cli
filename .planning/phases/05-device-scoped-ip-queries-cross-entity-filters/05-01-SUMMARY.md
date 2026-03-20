---
phase: 5
plan: "05-01"
subsystem: ipam
tags: [device-ips, mcp-tool, m2m-query]
requires: [nautobot_mcp.models.ipam, nautobot_mcp.ipam, nautobot_mcp.server, nautobot_mcp.cli.ipam]
provides: [get_device_ips, nautobot_get_device_ips, DeviceIPEntry, DeviceIPsResponse]
affects: [tests/test_server.py]
tech-stack:
  added: []
  patterns: [M2M traversal via ip_address_to_interface, Pydantic response models]
key-files:
  created: []
  modified:
    - nautobot_mcp/models/ipam.py
    - nautobot_mcp/ipam.py
    - nautobot_mcp/server.py
    - nautobot_mcp/cli/ipam.py
    - tests/test_server.py
key-decisions:
  - M2M traversal via ip_address_to_interface endpoint (not direct device filter on ip_addresses) — reliable cross-entity query
requirements-completed: [DEVIP-01, DEVIP-02, DEVIP-03]
duration: "~15 min"
completed: "2026-03-20"
---

# Phase 5 Plan 01: Device-Scoped IP Query Tool Summary

**One-liner:** New `nautobot_get_device_ips` MCP tool using M2M table traversal returns all interface-bound IPs for a device in one call, with `DeviceIPEntry`/`DeviceIPsResponse` Pydantic models and a CLI `addresses device-ips DEVICE` command.

**Duration:** ~15 min | **Tasks:** 6 | **Files modified:** 5

## What Was Built

- `DeviceIPEntry` and `DeviceIPsResponse` Pydantic models in `models/ipam.py`
- `get_device_ips(client, device_name)` core function in `ipam.py` — walks interfaces → M2M → IPs
- `nautobot_get_device_ips(device_name)` MCP tool in `server.py`
- `addresses device-ips DEVICE` CLI command in `cli/ipam.py` with JSON + text output
- `TestGetDeviceIPs` test class in `tests/test_server.py` (3 tests)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Self-Check: PASSED

- All 81 tests pass (`uv run pytest tests/ -v`)
- `nautobot_get_device_ips` in registered tool list (44 tools total)
- `from nautobot_mcp.ipam import get_device_ips` → OK
- `from nautobot_mcp.models.ipam import DeviceIPEntry, DeviceIPsResponse` → OK
- `uv run nautobot-mcp ipam addresses device-ips --help` → shows command
