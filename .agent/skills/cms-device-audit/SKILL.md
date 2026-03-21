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
- Nautobot API access configured (token + URL in env or config file)

## Workflow

### Step 1: Confirm Device Exists in Nautobot
Use `nautobot_device_summary` to verify the device is present and see high-level counts.

```
nautobot_device_summary(device_name="<device>")
```

Check: device name, location, role, interface/IP counts.

---

### Step 2: Collect Live BGP State from Device
Use `execute_junos_command` to pull BGP neighbor data:

```
execute_junos_command(router_name="<device>", command="show bgp summary | display json")
```

Parse the output into a list of neighbor dicts, each with:
```json
[{"peer_ip": "10.0.0.1", "peer_as": 65001, "local_address": "10.0.0.2", "group_name": "EXTERNAL"}]
```

---

### Step 3: Compare BGP Against CMS Records
Use `nautobot_cms_compare_bgp_neighbors`:

```
nautobot_cms_compare_bgp_neighbors(
    device_name="<device>",
    live_neighbors=[<list from step 2>]
)
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

### Step 5: Compare Static Routes Against CMS Records
Use `nautobot_cms_compare_static_routes`:

```
nautobot_cms_compare_static_routes(
    device_name="<device>",
    live_routes=[<list from step 4>]
)
```

Interpret the drift report (same structure as BGP). Pay special attention to:
- `nexthops_str` changes — next-hop changes are the most common drift type
- `preference` changes — administrative distance drift may indicate routing policy changes

---

### Step 6: Review Interface Details from CMS
Use `nautobot_cms_get_interface_detail` for the full interface picture:

```
nautobot_cms_get_interface_detail(device_name="<device>")
```

Review: interface units, address families, filter/policer associations, VRRP groups, ARP entries.
This is a CMS snapshot — compare manually against `show interfaces detail` output if needed.

---

### Step 7: Review Firewall Summary from CMS
Use `nautobot_cms_get_device_firewall_summary`:

```
nautobot_cms_get_device_firewall_summary(device_name="<device>")
```

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
- Changed → investigate field-level discrepancies; use create/update CRUD tools to reconcile

---

## Quick Check (Abridged Drift-Only Workflow)
For a fast drift check without the full interface/firewall review:

1. `nautobot_cms_get_device_bgp_summary` — overview of BGP state stored in Nautobot
2. `nautobot_cms_get_device_routing_table` — overview of routes stored in Nautobot
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
| `nautobot_device_summary` | Confirm device + see counts | `device_name` |
| `nautobot_cms_compare_bgp_neighbors` | BGP drift comparison | `device_name`, `live_neighbors` |
| `nautobot_cms_compare_static_routes` | Static route drift comparison | `device_name`, `live_routes` |
| `nautobot_cms_get_device_bgp_summary` | BGP snapshot from CMS | `device_name`, `detail` |
| `nautobot_cms_get_device_routing_table` | Route snapshot from CMS | `device_name`, `detail` |
| `nautobot_cms_get_interface_detail` | Full interface detail from CMS | `device_name` |
| `nautobot_cms_get_device_firewall_summary` | Firewall filter snapshot from CMS | `device_name` |
| `execute_junos_command` (jmcp) | Collect live device data | `router_name`, `command` |
