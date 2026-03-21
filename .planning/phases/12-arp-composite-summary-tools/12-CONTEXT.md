# Phase 12: ARP & Composite Summary Tools - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Add ARP entry read-only tools and build composite summary tools that aggregate data across multiple CMS models in a single call — device BGP summary, routing table, interface detail, firewall summary. Requirements ARP-01, ARP-02, COMP-01, COMP-02, COMP-03, COMP-04 (6 requirements total).

Note: ARP-02 (create/update/delete) is downscoped to read-only — ARP entries are runtime operational data collected from devices, not user-managed configuration.

</domain>

<decisions>
## Implementation Decisions

### ARP Device-Scoping — Native `device` Filter

Tested on dev server (2026-03-21):
- `filter(device=name_or_id)` ✅ — CMS DRF viewset has a custom `device` filter (works despite no direct device FK on Django model)
- `filter(interface=id)` ✅ — Filter by interface UUID
- `filter(mac_address=...)` ✅ — Filter by MAC address
- `interface__device` ❌ — NOT supported (400 error)

Use the native `device` filter for device-scoping. Also support `interface` and `mac_address` filters.

### ARP CRUD Scope — Read-Only

ARP entries are runtime/operational data collected from live devices. No user-managed mutation.

| Model | List | Get | Create | Update | Delete |
|-------|------|-----|--------|--------|--------|
| JuniperArpEntry | ✅ | ✅ | ❌ | ❌ | ❌ |

**Estimated tool count:** 2 ARP tools (list + get)

### ARP Display Fields — Standard

MAC address, IP address, interface name, hostname, device name. No enrichment needed.

### ARP Interface Filter

Support filtering by both device and interface: `list_arp_entries(device=X, interface="ge-0/0/0")`.

### ARP CLI Namespace — Under Interfaces

ARP is strongly tied to interfaces. CLI goes under `nautobot-mcp cms interfaces arp-entries --device X` rather than a separate `cms arp` domain.

### Composite Tool Architecture — Per-Domain Functions

Composite functions live in their respective domain CRUD modules:
- `get_device_bgp_summary()` → `cms/routing.py`
- `get_device_routing_table()` → `cms/routing.py`
- `get_interface_detail()` → `cms/interfaces.py`
- `get_device_firewall_summary()` → `cms/firewalls.py`

**Reuse existing CRUD functions** — compose `list_bgp_groups()`, `list_bgp_neighbors()`, etc. from existing domain modules and combine results. Mirrors how `get_device_summary` in `devices.py` composes existing functions.

### Composite Response Models — Dedicated File

Composite Pydantic response models go in `models/cms/composites.py` (e.g., `BGPSummaryResponse`, `RoutingTableResponse`, `InterfaceDetailResponse`, `FirewallSummaryResponse`).

### Composite Response Depth — Shallow Default + Rich Detail

All composite tools support a `detail` parameter (default False):

**COMP-01 — `get_device_bgp_summary(device, detail=False)`:**
- Default: groups (name, type, local-AS) + neighbors (peer IP, peer AS, session state) + counts for address families and policies
- Detail: + inlined address families and policy associations per neighbor

**COMP-02 — `get_device_routing_table(device, detail=False)`:**
- Default: routes with destination, preference, next-hop count
- Detail: + all simple and qualified next-hops inlined per route

**COMP-03 — `get_interface_detail(interface_id, detail=False)`:**
- Default: unit info + family list + counts for filters/policers/VRRP/ARP
- Detail: + full filter names, policer settings, VRRP virtual IPs, ARP entries

**COMP-04 — `get_device_firewall_summary(device, detail=False)`:**
- Default: filters (name, family, term count) + policers (name, bandwidth)
- Detail: + term names with match/action summaries per filter

### Composite CLI — Per-Domain with `-summary` Suffix

Composite CLI commands live under their domain subgroup:
- `nautobot-mcp cms routing bgp-summary --device X [--detail]`
- `nautobot-mcp cms routing routing-table --device X [--detail]`
- `nautobot-mcp cms interfaces detail --device X --interface ge-0/0/0.0 [--detail]`
- `nautobot-mcp cms firewalls firewall-summary --device X [--detail]`

`--detail` flag mirrors MCP tool behavior (default = summary, `--detail` = everything inlined).

### Claude's Discretion
- Exact Pydantic field selection for ARP and composite response models
- Table column selection for CLI output
- Internal helper functions for composing domain results
- Error messages and hints for composite-specific operations
- Whether composite tools need additional filtering (e.g., routing table by routing instance)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Established patterns (from Phase 8 + 9 + 10 + 11)
- `nautobot_mcp/cms/client.py` — Generic CRUD helpers (`cms_list`, `cms_get`), device UUID resolution, endpoint registry (ARP already registered)
- `nautobot_mcp/models/cms/base.py` — `CMSBaseSummary` base model with `from_nautobot()`, `_extract_device()`, `_get_field()`
- `nautobot_mcp/cms/routing.py` — Routing CRUD functions (BGP + static routes) to compose for COMP-01/COMP-02
- `nautobot_mcp/cms/interfaces.py` — Interface CRUD functions to compose for COMP-03
- `nautobot_mcp/cms/firewalls.py` — Firewall CRUD functions to compose for COMP-04
- `nautobot_mcp/models/cms/routing.py` — Routing Pydantic models (inlining pattern)
- `nautobot_mcp/models/cms/interfaces.py` — Interface Pydantic models (shallow list / rich get)
- `nautobot_mcp/models/cms/firewalls.py` — Firewall Pydantic models
- `nautobot_mcp/models/cms/policies.py` — Policy Pydantic models
- `nautobot_mcp/cli/cms_routing.py` — CLI pattern (Typer + rich tables + `--detail` flag)
- `nautobot_mcp/cli/cms_interfaces.py` — CLI pattern for interface commands

### Composite pattern reference
- `nautobot_mcp/devices.py` § `get_device_summary()` — Existing composite function that composes multiple API calls into one response
- `nautobot_mcp/models/device.py` § `DeviceSummaryResponse` — Existing composite response model

### CMS API model definitions
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\models\arp.py` — ARP model (interface FK, ip_address FK, mac_address, hostname)
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\api\urls.py` — DRF endpoint: `juniper-arp-entries`

</canonical_refs>

<code_context>
## Existing Code Insights

### CMS Endpoint Names (pynautobot underscore format)
- `juniper_arp_entries` → ARP entries (already in CMS_ENDPOINTS registry)

### ARP Model Structure
- `JuniperArpEntry.interface` → FK to Interface (not Device — device accessed via viewset custom filter)
- `JuniperArpEntry.ip_address` → FK to IPAddress
- `JuniperArpEntry.mac_address` → CharField (XX:XX:XX:XX:XX:XX format)
- `JuniperArpEntry.hostname` → CharField (optional, often same as IP)
- `unique_together = [interface, ip_address]`

### Supported API Filters (verified on dev server)
- `device` — filter by device name or UUID (custom viewset filter)
- `interface` — filter by interface UUID
- `mac_address` — filter by MAC address

### Composite Functions — Integration Points
Each composite function composes existing CRUD functions:
- `get_device_bgp_summary` → calls `list_bgp_groups(device=X)` + `list_bgp_neighbors(device=X)` + optionally `list_bgp_address_families` + `list_bgp_policy_associations`
- `get_device_routing_table` → calls `list_static_routes(device=X)` + optionally inlines nexthops
- `get_interface_detail` → calls `get_interface_unit(id)` + `list_interface_families(unit=X)` + `list_vrrp_groups(unit=X)` + `list_arp_entries(interface=X)`
- `get_device_firewall_summary` → calls `list_firewall_filters(device=X)` + `list_firewall_policers(device=X)` + optionally `list_firewall_terms`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following established Phase 8/9/10/11 patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-arp-composite-summary-tools*
*Context gathered: 2026-03-21*
