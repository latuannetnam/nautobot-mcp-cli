---
phase: 13
plan: 1
title: CMS Drift Engine — DiffSync Models, Adapters & CMSDriftReport
status: complete
completed: "2026-03-21T17:44:00+07:00"
---

# Summary: Plan 13-01

## Completed

- **CMSDriftReport** Pydantic model in `nautobot_mcp/models/cms/cms_drift.py` with `bgp_neighbors` and `static_routes` DriftSection fields, summary dict, and warnings list
- **DiffSync models**: `SyncBGPNeighbor` (identity: `peer_ip`, attributes: `peer_as`, `local_address`, `group_name`) and `SyncStaticRoute` (identity: `destination`, attributes: `nexthops_str`, `preference`, `metric`, `routing_instance`)
- **4 DiffSync adapters**: `LiveBGPAdapter`, `CMSBGPAdapter`, `LiveStaticRouteAdapter`, `CMSStaticRouteAdapter` — all in `nautobot_mcp/cms/cms_drift.py`
- **Comparison functions**: `compare_bgp_neighbors()` and `compare_static_routes()` accept live data + device name, return `CMSDriftReport`
- **Helpers**: `_serialize_nexthops()` for consistent nexthop sorting/dedup, `_build_cms_summary()` for drift count aggregation
- **CMSDriftReport** exported from `nautobot_mcp/models/cms/__init__.py`

## Files Modified

- `nautobot_mcp/models/cms/cms_drift.py` [NEW]
- `nautobot_mcp/cms/cms_drift.py` [NEW]
- `nautobot_mcp/models/cms/__init__.py` [MODIFIED]
