# Changelog

All notable changes to **nautobot-mcp-cli** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

> Changes targeting the next milestone (v1.3) will appear here.

Candidates:
- Multi-vendor config parsers (Cisco IOS/IOS-XE, Arista EOS)
- Bulk device onboarding (batch config files)
- Config remediation suggestions based on drift reports
- Extended drift coverage (interfaces, firewalls)

---

## [v1.2] — 2026-03-21

### Juniper CMS Model CRUD Tools

Full CRUD MCP tools for all Juniper-specific models in the `netnam-cms-core` Nautobot plugin — 5 model domains, 40+ Pydantic models, and a new `nautobot_mcp/cms/` subpackage.

**Routing** (BGP groups, BGP neighbors, static routes with inlined next-hops, routing instances)
- `nautobot_cms_list_static_routes` / `nautobot_cms_get_static_route` / `nautobot_cms_create_static_route` / `nautobot_cms_delete_static_route`
- `nautobot_cms_list_bgp_groups` / `nautobot_cms_get_bgp_group` / `nautobot_cms_create_bgp_group` / `nautobot_cms_delete_bgp_group`
- `nautobot_cms_list_bgp_neighbors` / `nautobot_cms_get_bgp_neighbor` / `nautobot_cms_create_bgp_neighbor` / `nautobot_cms_delete_bgp_neighbor`
- `nautobot_cms_list_bgp_address_families` / `nautobot_cms_list_bgp_policy_associations` / `nautobot_cms_list_bgp_received_routes`
- `nautobot_cms_list_routing_instances` / `nautobot_cms_list_static_route_nexthops`

**Interfaces** (interface units, address families, filter/policer associations, VRRP)
- `nautobot_cms_list_interface_units` / `nautobot_cms_get_interface_unit` / `nautobot_cms_create_interface_unit` / `nautobot_cms_delete_interface_unit`
- `nautobot_cms_list_interface_families` / `nautobot_cms_get_interface_family`
- `nautobot_cms_list_ff_associations` / `nautobot_cms_create_ff_association` / `nautobot_cms_delete_ff_association`
- `nautobot_cms_list_fp_associations` / `nautobot_cms_create_fp_association` / `nautobot_cms_delete_fp_association`
- `nautobot_cms_list_vrrp_groups` / `nautobot_cms_get_vrrp_group` / `nautobot_cms_create_vrrp_group` / `nautobot_cms_delete_vrrp_group`

**Firewalls & Policies** (firewall filters, terms, match conditions, policers, policy statements)
- `nautobot_cms_list_firewall_filters` / `nautobot_cms_get_firewall_filter` / `nautobot_cms_create_firewall_filter` / `nautobot_cms_delete_firewall_filter`
- `nautobot_cms_list_firewall_terms` / `nautobot_cms_create_firewall_term` / `nautobot_cms_delete_firewall_term`
- `nautobot_cms_list_firewall_policers` / `nautobot_cms_create_firewall_policer` / `nautobot_cms_delete_firewall_policer`
- `nautobot_cms_list_policy_statements` / `nautobot_cms_create_policy_statement` / `nautobot_cms_delete_policy_statement`
- Plus policy terms, match conditions, actions, prefix lists, communities, AS paths

**ARP**
- `nautobot_cms_list_arp_entries` / `nautobot_cms_get_arp_entry` / `nautobot_cms_create_arp_entry` / `nautobot_cms_delete_arp_entry`

### Composite Summary Tools

Single-call summaries aggregating across related models:
- `nautobot_cms_get_device_bgp_summary` — all BGP groups + neighbor counts + session state in one call; `detail=True` expands per-group neighbors with address families and policy associations
- `nautobot_cms_get_device_routing_table` — all static routes with inlined next-hops and routing instances
- `nautobot_cms_get_interface_detail` — full interface unit view: families, filter/policer associations, VRRP groups, ARP entries
- `nautobot_cms_get_device_firewall_summary` — all firewall filters with term counts and policer associations

### CMS Drift Verification

DiffSync-based live-vs-CMS comparison — no config files required:
- `nautobot_cms_compare_bgp_neighbors` — compare BGP neighbors collected from a live device (via jmcp) against Nautobot CMS records; returns `CMSDriftReport` with `missing`, `extra`, and `changed` sections
- `nautobot_cms_compare_static_routes` — same for static routes; nexthop comparison is order-independent

### CLI Commands

CMS model operations under `nautobot-mcp cms`:
- `nautobot-mcp cms routing <subcommand>` — full CRUD + `bgp-summary` + `routing-table`
- `nautobot-mcp cms interfaces <subcommand>` — full CRUD + `detail` + ARP (`list-arp-entries`, `get-arp-entry`)
- `nautobot-mcp cms firewalls <subcommand>` — full CRUD + `firewall-summary`
- `nautobot-mcp cms policies <subcommand>` — full CRUD
- `nautobot-mcp cms drift bgp --device DEVICE --from-file live.json` — BGP drift check
- `nautobot-mcp cms drift routes --device DEVICE --from-file live.json` — route drift check

### Agent Skills

- `cms-device-audit` skill — 8-step CMS-aware device audit workflow: confirm device in Nautobot → collect live BGP + routes via jmcp → compare against CMS records → review interface detail + firewall summary → compile audit report with action guidance

### Stats

- MCP tools: 46 → **164**
- Unit tests: 105 → **293**
- Phases: 7 (CMS foundation, routing, interfaces, firewalls/policies, ARP+composites, drift engine, CLI+skills)

---

## [v1.1] — 2026-03-20

### Added

**Device Queries**
- `nautobot_get_device_ips` — returns all IP addresses on all interfaces for a device in one call,
  using M2M traversal via `ip_address_to_interface` (more reliable than direct device filter)
- `nautobot_get_device_summary` — single-call device health check: interface count, IP count, VLAN
  count, enabled/disabled link-state statistics
- `nautobot_list_interfaces(include_ips=True)` — embeds IPs inline per interface using a batch M2M
  query (≤2 API calls total, not N+1 per interface)

**Cross-Entity Filters**
- `nautobot_list_ip_addresses(device=...)` — filter IPs to a specific device
- `nautobot_list_vlans(device=...)` — filter VLANs to a specific device's interfaces

**File-Free Drift Comparison**
- `nautobot_compare_device` — compare structured interface data against Nautobot records; no config
  file required; input auto-detected as flat dict or DeviceIPEntry list (chainable from
  `nautobot_get_device_ips`)
- Pydantic models: `InterfaceDrift`, `DriftSummary`, `QuickDriftReport`
- Lenient IP validation: accepts IPs without prefix length with a warning (real-world jmcp output)

**CLI Commands**
- `nautobot-mcp devices summary DEVICE` — compact device overview; `--detail` for full breakdown
- `nautobot-mcp ipam ips list --device DEVICE` — device-scoped IP query
- `nautobot-mcp ipam vlans list --device DEVICE` — device-scoped VLAN query
- `nautobot-mcp interfaces list --include-ips` — interfaces with IPs inline
- `nautobot-mcp verify quick-drift DEVICE` — file-free drift check with multiple input modes:
  - `--interface`/`--ip`/`--vlan` flags for single-interface quick checks
  - `--data` JSON string for bulk inline input
  - `--file` JSON file for scripted flows
  - stdin pipe for agent-driven workflows
  - `--json` for machine-readable output
  - Colored table output: ✅ OK / ❌ DRIFT per interface with missing/extra detail

**Agent Skills**
- `verify-compliance` skill guide updated with "File-Free Drift Check" section:
  jmcp chaining workflow and `nautobot_get_device_ips` → `nautobot_compare_device` chain

### Stats

- MCP tools: 44 → **46**
- Unit tests: 76 → **105**
- Files changed since v1.0: 75 (+8225 / -156)

---

## [v1.0] — 2026-03-18

Initial release — full Nautobot automation via MCP and CLI.

### Added

**Core Infrastructure**
- `NautobotClient` — pynautobot wrapper with profile support, SSL control, and pagination
- Multi-source config loading: YAML file → env vars → CLI flags (layered precedence)
- Named profiles (`default`, `staging`, etc.) in `.nautobot-mcp.yaml`
- FastMCP 3.0 MCP server with automatic tool registration from type hints

**MCP Tools (44 total)**
- **Devices** — list, get, create, update, delete
- **Interfaces** — list, get, create, update, assign IP
- **IPAM** — prefixes, IP addresses, VLANs (list + create)
- **Organization** — tenants, locations (list, get, create, update)
- **Circuits** — list, get, create, update
- **Golden Config** — intended config, backup config, compliance features/rules/results, quick diff
- **Onboarding** — parse config, onboard to Nautobot (dry-run safe)
- **Verification** — compliance check (Golden Config), DiffSync data model drift report

**CLI**
- Typer-based CLI mirroring all MCP tools
- `--json` global flag for machine-readable output
- `--profile` / `--url` / `--token` / `--no-verify` global flags

**Config Parsing & Onboarding**
- JunOS JSON config parser (`juniper_junos`) via `show configuration | display json`
- Extensible `VendorParser` ABC + `ParserRegistry` for future vendors
- Onboarding engine: parse → dry-run preview → commit (Device → Interfaces → IPs → VLANs)

**Verification**
- Golden Config compliance check via quick diff
- DiffSync-based data model verification: per-object diff with `missing`, `extra`, `changed` statuses
  for interfaces, IP addresses, and VLANs

**Agent Skills**
- `onboard-router-config` — step-by-step skill guide for jmcp → parse → onboard workflow
- `verify-compliance` — skill guide for compliance checks and data model drift detection

### Stats

- MCP tools: **44**
- Unit tests: **76**
- Lines of code: ~3,400 Python

---

*For full per-phase details see [`.planning/milestones/`](.planning/milestones/).*
