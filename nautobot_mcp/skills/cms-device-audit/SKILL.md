---
name: cms-device-audit
description: Full CMS-aware device audit — compare live device state against Nautobot CMS records across BGP, routes, interfaces, and firewall domains
---

# CMS Device Audit

## When to Use
- When auditing a Juniper device against its Nautobot CMS records for configuration drift
- When performing pre/post change verification across BGP, static routes, interfaces, and firewalls
- When checking whether CMS plugin data is current and accurate for a device

## Prerequisites
- Device must exist in Nautobot with CMS plugin data populated
- `jmcp` MCP server connected for live device data collection
- Nautobot API access configured

## Workflow

### Step 0: Discover Available Endpoints
Optional — shows available CMS endpoints and workflows:

```
nautobot_api_catalog(domain="cms")
```

---

### Step 1: Confirm Device Exists in Nautobot
Use `nautobot_call_nautobot` to verify the device is present and see high-level counts:

```
nautobot_call_nautobot(
    method="GET",
    endpoint="/api/dcim/devices/",
    params={"name": "<device>"}
)
```

Required params: `method` (str), `endpoint` (str), `params` (dict).

Example response envelope:
```json
{"status": "ok", "method": "GET", "endpoint": "/api/dcim/devices/", "data": [{"id": "uuid", "name": "core-rtr-01", "location": {}}], "count": 1}
```

Check: device name, location, role, interface/IP counts.

---

### Step 2: Collect Live BGP State from Device
Use `execute_junos_command` to pull BGP neighbor data:

```
execute_junos_command(router_name="<device>", command="show bgp summary | display json")
```

Parse the output into a list of neighbor dicts:
```json
[{"peer_ip": "10.0.0.1", "peer_as": 65001, "local_address": "10.0.0.2", "group_name": "EXTERNAL"}]
```

---

### Step 3: Compare BGP Against CMS Records (CONSOLIDATED)
Use `nautobot_run_workflow` — this handles retrieval + comparison in one call:

```
nautobot_run_workflow(
    workflow_id="compare_bgp",
    params={"device_name": "<device>", "live_neighbors": [<list from step 2>]}
)
```

Required params: `device_name` (str), `live_neighbors` (list of dicts).
Format note for `live_neighbors`: `[{"peer_ip": "10.0.0.1", "peer_as": 65001, "local_address": "10.0.0.2", "group_name": "EXTERNAL"}]`

Example response envelope:
```json
{"workflow": "compare_bgp", "device": "core-rtr-01", "status": "ok", "data": {"bgp_neighbors": {}}, "error": null, "timestamp": "..."}
```

Interpret the `CMSDriftReport`:
- `missing_in_nautobot` → neighbor is on device but not in CMS (needs onboarding)
- `extra_in_nautobot` (missing on device) → stale CMS record (possible decommission)
- `changed` → field-level discrepancies (peer_as, local_address, group mismatch)
- `total_drifts: 0` → BGP is fully in sync ✓

---

### Step 4: Collect Live Static Routes from Device
Use `execute_junos_command` to pull routing table:

```
execute_junos_command(router_name="<device>", command="show route protocol static | display json")
```

Map the output to a list of route dicts:
```json
[{"destination": "0.0.0.0/0", "nexthops": ["10.0.0.1"], "preference": 5, "metric": 0, "routing_instance": "default"}]
```

---

### Step 5: Compare Static Routes Against CMS Records (CONSOLIDATED)
Use `nautobot_run_workflow` — handles retrieval + comparison in one call:

```
nautobot_run_workflow(
    workflow_id="compare_routes",
    params={"device_name": "<device>", "live_routes": [<list from step 4>]}
)
```

Required params: `device_name` (str), `live_routes` (list of dicts).
Format note for `live_routes`: `[{"destination": "0.0.0.0/0", "nexthops": ["10.0.0.1"], "preference": 5, "metric": 0, "routing_instance": "default"}]`

Interpret the drift report (same structure as BGP). Pay special attention to:
- `nexthops_str` changes — next-hop changes are the most common drift type
- `preference` changes — administrative distance drift may indicate routing policy changes

---

### Step 6: Review Interface Details from CMS
Use `nautobot_run_workflow` for the full interface picture:

```
nautobot_run_workflow(
    workflow_id="interface_detail",
    params={"device": "<device>"}
)
```

Required params: `device` (str). Optional: `include_arp` (bool, default false).

Review: interface units, address families, filter/policer associations, VRRP groups, ARP entries.

---

### Step 7: Review Firewall Summary from CMS

```
nautobot_run_workflow(
    workflow_id="firewall_summary",
    params={"device": "<device>"}
)
```

Required params: `device` (str). Optional: `detail` (bool, default false).

Review: filter names, term counts, policer associations. Use to spot missing or extra filters.

---

### Step 8: Compile Audit Report
Aggregate findings across all domains:

| Domain | Total Drifts | Missing | Extra | Changed |
|--------|-------------|---------|-------|---------|
| BGP Neighbors | N | N | N | N |
| Static Routes | N | N | N | N |
| Interfaces | Manual | — | — | — |
| Firewalls | Manual | — | — | — |

**Decision guidance:**
- `total_drifts: 0` across all → device fully compliant with CMS records ✓
- Missing in Nautobot → trigger onboarding workflow (`onboard-router-config` skill)
- Extra in Nautobot → verify device state, then delete stale CMS records via CRUD tools
- Changed → investigate field-level discrepancies; use `nautobot_call_nautobot` CRUD to reconcile

---

## Quick Check (Abridged Drift-Only Workflow)
For a fast drift check without the full interface/firewall review:

1. `nautobot_run_workflow("bgp_summary", {"device": "<device>"})` — overview of BGP state stored in Nautobot
2. `nautobot_run_workflow("routing_table", {"device": "<device>"})` — overview of routes stored in Nautobot
3. Run Steps 2-5 above to collect live data and compare

---

## CLI Alternative
For scripted or operator-driven drift checks:

```bash
# BGP drift: compare live JSON file against CMS
nautobot-mcp cms drift bgp --device core-rtr-01 --from-file live-bgp.json

# Route drift: compare live JSON file against CMS
nautobot-mcp cms drift routes --device core-rtr-01 --from-file live-routes.json

# BGP summary from Nautobot (no live data needed)
nautobot-mcp cms routing bgp-summary --device core-rtr-01

# Routing table from Nautobot
nautobot-mcp cms routing routing-table --device core-rtr-01

# Interface detail from Nautobot
nautobot-mcp cms interfaces detail --device core-rtr-01

# Firewall summary from Nautobot
nautobot-mcp cms firewalls firewall-summary --device core-rtr-01
```

---

## Key MCP Tools Reference

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `nautobot_api_catalog` | Discover endpoints and workflows | `domain` (optional) |
| `nautobot_call_nautobot` | REST CRUD for any Nautobot endpoint | `method`, `endpoint`, `params`, `body` |
| `nautobot_run_workflow` | Execute composite workflows | `workflow_id`, `params` |
| `execute_junos_command` (jmcp) | Collect live device data | `router_name`, `command` |

### Workflow IDs for this skill
| Workflow ID | Purpose | Required Params |
|-------------|---------|-----------------|
| `compare_bgp` | BGP drift comparison | `device_name`, `live_neighbors` |
| `compare_routes` | Static route drift comparison | `device_name`, `live_routes` |
| `bgp_summary` | BGP snapshot from CMS | `device` |
| `routing_table` | Route snapshot from CMS | `device` |
| `interface_detail` | Full interface detail from CMS | `device` |
| `firewall_summary` | Firewall filter snapshot from CMS | `device` |
