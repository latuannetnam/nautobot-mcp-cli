# Milestones

## v1.2 Juniper CMS Model MCP Tools (Shipped: 2026-03-21)

**Phases completed:** 6 phases, 18 plans | 62 commits | 98 files changed | +21,735 lines

**Key accomplishments:**

- **164 MCP tools** — full CRUD for 5 Juniper CMS model domains: routing (BGP + static routes), interfaces (units, families, VRRP), firewalls, policies, ARP
- **4 composite summary tools** — `get_device_bgp_summary`, `get_device_routing_table`, `get_interface_detail`, `get_device_firewall_summary` (single-call aggregations)
- **DiffSync drift engine** — `compare_bgp_neighbors` + `compare_static_routes`; live jmcp data vs Nautobot CMS records; no config files required
- **`nautobot-mcp cms` CLI** — routing, interfaces, firewalls, policies, drift subcommands
- **`cms-device-audit` agent skill** — 8-step jmcp → CMS comparison audit workflow
- **293 unit tests** — up from 105 at v1.1; full coverage across all 6 phases

---

## v1.1 Agent-Native MCP Tools (Shipped: 2026-03-20)

**Phases completed:** 7 phases, 19 plans

**Key accomplishments:**

- `nautobot_get_device_ips` — all IPs for a device in one call (M2M traversal)
- `nautobot_get_device_summary` — device health at a glance
- `nautobot_list_interfaces(include_ips=True)` — inline IP enrichment
- `nautobot_compare_device` — file-free drift detection
- `verify quick-drift` CLI command
- 46 MCP tools | 105 unit tests | ~11k LOC

**Last phase number:** 7

---

## v1.0 MVP (Shipped: 2026-03-18)

**Phases completed:** 4 phases, 13 plans, 0 tasks

**Key accomplishments:**

- 44+ MCP tools for Device, Interface, IPAM, Organization, Circuit, Golden Config
- CLI interface with Typer
- JunOS config parser with VendorParser ABC
- Config onboarding and verification workflows
- Agent skills (onboard-router-config, verify-compliance)

**Last phase number:** 4

---
