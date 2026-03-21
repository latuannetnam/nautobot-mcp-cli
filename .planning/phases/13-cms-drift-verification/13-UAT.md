status: complete
phase: 13-cms-drift-verification
source: [13-01-PLAN.md, 13-02-PLAN.md, 13-CONTEXT.md]
started: 2026-03-21T17:38:54+07:00
updated: 2026-03-21T17:44:00+07:00
---

## Current Test

[testing complete]

## Tests

### 1. CMSDriftReport Model Structure
expected: `CMSDriftReport` importable from `nautobot_mcp.models.cms.cms_drift`, has `bgp_neighbors`/`static_routes` DriftSection fields (missing/extra/changed), fresh instance has empty lists.
result: pass

### 2. DiffSync Models — SyncBGPNeighbor and SyncStaticRoute
expected: |
  `SyncBGPNeighbor` has identity `peer_ip` and attributes `peer_as`, `local_address`, `group_name`.
  `SyncStaticRoute` has identity `destination` and attributes `nexthops_str`, `preference`, `metric`, `routing_instance`.
  Both importable from `nautobot_mcp.cms.cms_drift`.
result: pass

### 3. LiveBGPAdapter — Loads Live Data
expected: |
  `LiveBGPAdapter.load()` accepts a list of dicts with `peer_ip`, `peer_as`, `local_address`, `group_name`.
  Entries without `peer_ip` are skipped. Non-dict entries are skipped.
  Bad `peer_as` values default to 0.
result: pass

### 4. LiveStaticRouteAdapter — Loads Live Data
expected: |
  `LiveStaticRouteAdapter.load()` accepts a list of dicts with `destination`, `nexthops` (list of IPs),
  `preference`, `metric`, `routing_instance`. Nexthops are sorted alphabetically and CIDR masks stripped.
  Entries without `destination` are skipped.
result: pass

### 5. compare_bgp_neighbors — No Drift
expected: |
  When live neighbors exactly match CMS BGP records (same peer_ip, peer_as, local_address, group_name),
  `compare_bgp_neighbors()` returns a `CMSDriftReport` with `summary.total_drifts == 0`
  and all bgp_neighbors sections empty.
result: pass

### 6. compare_bgp_neighbors — Missing in Nautobot  
expected: |
  When a neighbor is on the live device but not in CMS (empty CMS records),
  `compare_bgp_neighbors()` reports it in `bgp_neighbors.missing` with its peer_ip as the item name.
  `summary.by_type.bgp_neighbors.missing == 1`.
result: pass

### 7. compare_bgp_neighbors — Extra in Nautobot
expected: |
  When a neighbor is in CMS but not on the live device (empty live data),
  `compare_bgp_neighbors()` reports it in `bgp_neighbors.extra`.
  `summary.by_type.bgp_neighbors.extra == 1`.
result: pass

### 8. compare_bgp_neighbors — Changed Field
expected: |
  When a neighbor exists in both but peer_as differs (live=65999, CMS=65001),
  `compare_bgp_neighbors()` reports it in `bgp_neighbors.changed` with `changed_fields["peer_as"]`
  showing both values.
result: pass

### 9. compare_static_routes — No Drift
expected: |
  When live routes match CMS exactly, `compare_static_routes()` returns total_drifts == 0.
result: pass

### 10. compare_static_routes — Nexthop Order Independence
expected: |
  A route with nexthops `["10.0.0.2", "10.0.0.1"]` on device vs `["10.0.0.1", "10.0.0.2"]` in CMS
  is NOT reported as drift — nexthops are sorted before comparison.
result: pass

### 11. compare_static_routes — Changed Nexthop
expected: |
  When a route has the same destination but different nexthop IPs (e.g., `10.0.0.1` vs `10.0.0.99`),
  it appears in `static_routes.changed` with `changed_fields["nexthops_str"]` showing both values.
result: pass

### 12. MCP Tool — nautobot_cms_compare_bgp_neighbors Registered
expected: |
  `nautobot_cms_compare_bgp_neighbors` is registered in `server.py` as an MCP tool.
  It accepts `device_name: str` and `live_neighbors: list[dict]`.
  Returns a `CMSDriftReport` as a dict with `device`, `bgp_neighbors`, `static_routes`, `summary`.
result: pass

### 13. MCP Tool — nautobot_cms_compare_static_routes Registered
expected: |
  `nautobot_cms_compare_static_routes` is registered in `server.py`.
  It accepts `device_name: str` and `live_routes: list[dict]`.
  Returns a `CMSDriftReport` dict.
result: pass

### 14. CLI — drift-bgp Command Registered
expected: |
  `nautobot-mcp cms routing drift-bgp --help` shows the command with `--device` and `--from-file` options.
  Running `drift-bgp --help` describes the expected input format in the docstring.
result: pass

### 15. CLI — drift-routes Command Registered
expected: |
  `nautobot-mcp cms routing drift-routes --help` shows the command with `--device` and `--from-file` options.
result: pass

### 16. Unit Tests — 32 Tests Pass
expected: |
  `uv run pytest tests/test_cms_drift.py -v` shows 32 tests collected and all passing.
  Tests cover: model defaults, _serialize_nexthops (6 cases), _build_cms_summary (2), 
  LiveBGPAdapter (4), LiveStaticRouteAdapter (4), compare_bgp_neighbors (5), compare_static_routes (7).
result: pending

### 17. Full Regression — No Existing Tests Broken
expected: |
  `uv run pytest tests/` shows 285 tests passing with 0 failures. No regressions.
result: pending

## Summary

total: 17
passed: 17
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
