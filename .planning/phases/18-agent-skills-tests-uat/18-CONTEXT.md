# Phase 18 – Agent Skills, Tests & UAT — Context

Date: 2026-03-24

## Overview

Phase 18 updates the 3 existing agent skills to reference the new 3-tool API
(`nautobot_api_catalog`, `nautobot_call_nautobot`, `nautobot_run_workflow`) and
validates the full API Bridge against the live Nautobot dev server.

## Gray Areas Discussed

### 1. Skill Rewrite Depth

**Decision: Consolidate steps (Option B)**

Old multi-step patterns (collect data → compare) are collapsed into single
`nautobot_run_workflow()` calls where the workflow already handles both parts.
For example, the `cms-device-audit` skill's "Collect BGP + Compare BGP" (old
Steps 2+3) becomes a single `nautobot_run_workflow("compare_bgp", ...)` call.

| Old Pattern | New Pattern |
|---|---|
| `nautobot_device_summary(device_name=X)` | `nautobot_call_nautobot("GET", "/api/dcim/devices/", params={"name": X})` |
| `nautobot_cms_compare_bgp_neighbors(device_name=X, live_neighbors=[...])` | `nautobot_run_workflow("compare_bgp", {"device_name": X, "live_neighbors": [...]})` |
| `nautobot_cms_compare_static_routes(device_name=X, live_routes=[...])` | `nautobot_run_workflow("compare_routes", {"device_name": X, "live_routes": [...]})` |
| `nautobot_cms_get_interface_detail(device_name=X)` | `nautobot_run_workflow("interface_detail", {"device": X})` |
| `nautobot_cms_get_device_firewall_summary(device_name=X)` | `nautobot_run_workflow("firewall_summary", {"device": X})` |
| `nautobot_cms_get_device_bgp_summary(device_name=X)` | `nautobot_run_workflow("bgp_summary", {"device": X})` |
| `nautobot_cms_get_device_routing_table(device_name=X)` | `nautobot_run_workflow("routing_table", {"device": X})` |
| `nautobot_onboard_config(config_json=..., device_name=X)` | `nautobot_run_workflow("onboard_config", {"config_data": {...}, "device_name": X})` |
| `nautobot_verify_data_model(config_json=..., device_name=X)` | `nautobot_run_workflow("verify_data_model", {"config_data": {...}, "device_name": X})` |
| `nautobot_verify_config_compliance(device=X)` | `nautobot_run_workflow("verify_compliance", {"device_name": X})` |
| `nautobot_compare_device(device_name=X, interfaces_data=...)` | `nautobot_run_workflow("compare_device", {"device_name": X, "live_data": {...}})` |

**Quick Check section:** Keep simplified — useful for CMS-only checks (no live
device data needed), just update tool names.

**Reference table:** Replace old 8-tool table with new 3-tool reference table
showing which workflow IDs map to each purpose.

**jmcp references:** Keep Steps that call `execute_junos_command` identical but
add brief notes about expected data formats for workflow params (e.g.,
`live_neighbors` list-of-dict shape for `compare_bgp`).

### 2. UAT Scope vs Live Server Risk

**Decision: Both pytest + standalone script (Option C)**

| Choice | Decision | Rationale |
|---|---|---|
| Delivery format | Both: `@pytest.mark.live` tests + `scripts/uat_smoke_test.py` | CI-friendly + quick manual runs |
| Read/write scope | Read + idempotent write (Option B) | GET catalog/devices + POST dry_run=true onboard — validates write path without data mutation |
| Server URL | Env variable `NAUTOBOT_UAT_URL` with `http://101.96.85.93` default | Flexible for different environments |
| Failure tolerance | Fail hard (Option B) | Server availability is a prerequisite for UAT |

**CMS test device:** `HQV-PE-TestFake` for Juniper-specific / CMS plugin endpoint testing.

**UAT test scope:**
1. `nautobot_api_catalog()` — verify returns expected domains (dcim, ipam, circuits, tenancy, cms, workflows)
2. `nautobot_call_nautobot("GET", "/api/dcim/devices/")` — returns real device list
3. `nautobot_call_nautobot("GET", "/api/dcim/devices/", params={"name": "HQV-PE-TestFake"})` — returns specific device
4. `nautobot_run_workflow("bgp_summary", {"device": "HQV-PE-TestFake"})` — CMS composite workflow returns data
5. `nautobot_run_workflow("onboard_config", {"config_data": {...}, "device_name": "HQV-PE-TestFake", "dry_run": true})` — validates write path without committing

### 3. Skill Endpoint References (SKL-02)

**Decisions:**

| Choice | Decision |
|---|---|
| Detail level | Tool name + workflow ID + required params (Option B) |
| Example responses | Yes — show trimmed example envelope (Option A) |
| Catalog reference | Yes — start with "Discovery" step calling `nautobot_api_catalog()` (Option A) |
| Skill count | Keep at 3 skills — no new skills needed |

Each skill will follow this template:
```
### Step 0: Discover available endpoints (optional)
  nautobot_api_catalog(domain="cms")

### Step N: [Action]
  nautobot_run_workflow("workflow_id", {
    "param1": "value1",
    "param2": "value2"
  })

  Expected response:
  {
    "workflow": "...",
    "status": "ok",
    "data": { ... },
    ...
  }
```

### 4. Phase 17 Test Status (Pre-resolved)

**TST-04 and TST-05 already complete from Phase 17:**
- `test_workflows.py` — 387 lines covering registry sync, dispatch, transforms, envelope, errors
- `test_server.py` — 329 lines covering 3-tool registration, client singleton, error handling

Phase 18 testing is only the UAT piece (TST-06, TST-07, TST-08).

## Architecture Summary

```
Files to CREATE:
├── tests/test_uat.py               # @pytest.mark.live UAT tests
├── scripts/uat_smoke_test.py        # Standalone UAT runner

Files to MODIFY:
├── nautobot_mcp/skills/
│   ├── cms-device-audit/SKILL.md    # Rewrite: consolidate + new API
│   ├── onboard-router-config/SKILL.md # Rewrite: new workflow calls
│   └── verify-compliance/SKILL.md   # Rewrite: new workflow calls

Files UNCHANGED:
├── nautobot_mcp/server.py           # Already 3-tool (Phase 17)
├── nautobot_mcp/workflows.py        # Already complete (Phase 17)
├── nautobot_mcp/bridge.py           # Already complete (Phase 16)
├── nautobot_mcp/catalog/            # Already complete (Phase 15)
├── tests/test_server.py             # Already complete (Phase 17)
├── tests/test_workflows.py          # Already complete (Phase 17)
```

## Requirements Covered

- **SKL-01**: All 3 skills updated to reference `nautobot_call_nautobot`, `nautobot_run_workflow`, `nautobot_api_catalog`
- **SKL-02**: Skills embed tool + workflow ID + required params inline, with example envelopes
- **SKL-03**: `cms-device-audit` skill rewritten with consolidated steps + discovery step
- **SKL-04**: `onboard-router-config` skill uses `nautobot_run_workflow("onboard_config", ...)`
- **SKL-05**: `verify-compliance` skill uses `nautobot_run_workflow("verify_compliance", ...)`
- **TST-06**: UAT smoke test (pytest + standalone script) against Nautobot dev server
- **TST-07**: Verify `nautobot_api_catalog()` returns expected domains from live server
- **TST-08**: Verify `nautobot_call_nautobot("/api/dcim/devices/", "GET")` returns real data
