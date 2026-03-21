# Phase 10: Interface Models — Units, Families, VRRP - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Add full CRUD MCP tools, Pydantic models, and CLI commands for Juniper interface models in netnam-cms-core: interface units (VLAN mode, encapsulation, QinQ), families (inet/inet6/mpls), filter/policer associations, and VRRP groups with tracking. Requirements INTF-01 through INTF-07.

</domain>

<decisions>
## Implementation Decisions

### CRUD Scope per Model

| Model | List | Get | Create | Update | Delete | Rationale |
|-------|------|-----|--------|--------|--------|-----------|
| JuniperInterfaceUnit | ✅ | ✅ | ✅ | ✅ | ✅ | Primary parent, full CRUD |
| JuniperInterfaceFamily | ✅ | ✅ | ✅ | ✅ | ✅ | Key child, agents manage protocol families |
| JuniperInterfaceFamilyFilter | ✅ | ✅ | ✅ | ❌ | ✅ | Junction — agents can attach/detach filters |
| JuniperInterfaceFamilyPolicer | ✅ | ✅ | ✅ | ❌ | ✅ | Junction — agents can attach/detach policers |
| JuniperInterfaceVRRPGroup | ✅ | ✅ | ✅ | ✅ | ✅ | Important child, full CRUD |
| VRRPTrackRoute | ✅ | ✅ | ❌ | ❌ | ❌ | Tracking config — read-only |
| VRRPTrackInterface | ✅ | ✅ | ❌ | ❌ | ❌ | Tracking config — read-only |

### Inlining Strategy — Hybrid

- **`list_interface_units`** stays **shallow** — returns unit fields + `family_count` (integer). No inline families. Fast for listing 51+ units.
- **`get_interface_unit`** is **rich** — inlines family summaries with their filter/policer names. Single call gives full picture of one unit.
- This hybrid matches the "fast list, rich detail" pattern and avoids N+1 API calls on list operations.

### M2M VLAN Handling — IDs Only

- `outer_vlans` and `inner_vlans` (M2M fields) represented as `list[str]` of VLAN UUIDs in Pydantic models.
- `router_tagged_vlan` (FK) represented as optional VLAN UUID string.
- Keeps responses minimal — agents can query VLANs separately if needed.

### Device-Scoping — Direct Filter

- `list_interface_units(device="R1")` resolves device UUID, passes `device=device_id` to the API.
- **Confirmed working on dev server:** `cms.juniper_interface_units.filter(device=device_id)` returned 51 units for HQV-PE-TestFake.
- The `JuniperInterfaceUnitFilterSet` has an explicit `device` shortcut filter that traverses `interface__device`.
- Other models (families, VRRP, trackers) filter by parent FK only (`interface_unit`, `family`, `vrrp_group`).

### CLI Command Structure

- **Nested domain namespace:** `nautobot-mcp cms interfaces <command>` (same pattern as Phase 9's `cms routing`)
- **CLI ships with this phase** — not deferred to Phase 14.
- **Tabular output + `--detail` flag** — default shows concise table, `--detail` shows inlined child data.

### Claude's Discretion
- Exact Pydantic field selection per model (which fields to include vs omit)
- Table column selection for CLI output per model
- Internal helper functions for inlining families into `get_interface_unit` response
- Error messages and hints for interface-specific operations
- Whether `family_count` is computed client-side or extracted from API response

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Established patterns (from Phase 8 + 9)
- `nautobot_mcp/cms/client.py` — Generic CRUD helpers (`cms_list`, `cms_get`, `cms_create`, `cms_update`, `cms_delete`), device UUID resolution, endpoint registry
- `nautobot_mcp/models/cms/base.py` — `CMSBaseSummary` base model with `from_nautobot()`, `_extract_device()`, `_get_field()`
- `nautobot_mcp/cms/routing.py` — Phase 9 CRUD pattern to follow (inlining, device-scoping, list+get patterns)
- `nautobot_mcp/models/cms/routing.py` — Phase 9 Pydantic model pattern to follow
- `nautobot_mcp/cli/cms_routing.py` — Phase 9 CLI pattern to follow (Typer + rich tables)
- `nautobot_mcp/client.py` — `NautobotClient.cms` property for plugin access

### CMS API model definitions
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\models\interfaces.py` — All 7 interface models (InterfaceUnit, InterfaceFamily, FamilyFilter, FamilyPolicer, VRRPGroup, TrackRoute, TrackInterface)
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\filters\interfaces.py` — FilterSet definitions (confirms `device` shortcut filter on InterfaceUnit, parent FK filters on others)
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\api\urls.py` — DRF endpoint registrations (all 7 interface endpoints confirmed)

</canonical_refs>

<code_context>
## Existing Code Insights

### CMS Endpoint Names (pynautobot underscore format)
- `juniper_interface_units` → Interface units (has `device` filter)
- `juniper_interface_families` → Protocol families (filter by `interface_unit`)
- `juniper_interface_family_filters` → Filter associations (filter by `family`, `filter_type`, `enabled`)
- `juniper_interface_family_policers` → Policer associations (filter by `family`, `policer_type`, `enabled`)
- `juniper_interface_vrrp_groups` → VRRP groups (filter by `family`, `group_number`)
- `vrrp_track_routes` → Track routes (filter by `vrrp_group`)
- `vrrp_track_interfaces` → Track interfaces (filter by `vrrp_group`, `tracked_interface`)

### Key Model Relationships
- InterfaceUnit.interface → OneToOne to Interface (Interface.device gives Device)
- InterfaceUnit.outer_vlans → M2M to VLAN
- InterfaceUnit.inner_vlans → M2M to VLAN
- InterfaceUnit.router_tagged_vlan → FK to VLAN (nullable)
- InterfaceFamily.interface_unit → FK to InterfaceUnit (related_name: `families`)
- InterfaceFamilyFilter.family → FK to InterfaceFamily (related_name: `family_filters`)
- InterfaceFamilyFilter.filter → FK to JuniperFirewallFilter
- InterfaceFamilyPolicer.family → FK to InterfaceFamily (related_name: `family_policers`)
- InterfaceFamilyPolicer.policer → FK to JuniperFirewallPolicer
- VRRPGroup.family → FK to InterfaceFamily (related_name: `vrrp_groups`)
- VRRPGroup.virtual_address → FK to IPAddress
- VRRPGroup.interface_address → FK to IPAddress (nullable)
- VRRPTrackRoute.vrrp_group → FK to VRRPGroup (related_name: `tracked_routes`)
- VRRPTrackRoute.route_address → FK to IPAddress
- VRRPTrackInterface.vrrp_group → FK to VRRPGroup (related_name: `tracked_interfaces`)
- VRRPTrackInterface.tracked_interface → FK to Interface

### API Test Results (HQV-PE-TestFake)
- `juniper_interface_units.filter(device=device_id)` → 51 units ✅
- `juniper_interface_families.filter(interface_unit=unit_id)` → 3 families for ae0 (inet, inet6, vpls) ✅
- InterfaceUnit API keys: id, object_type, display, interface, vlan_mode, encapsulation, gigether_speed, is_qinq_enabled, outer_vlans, inner_vlans, router_tagged_vlan, lacp_active, description, ...

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following established Phase 8/9 patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-interface-models-units-families-vrrp*
*Context gathered: 2026-03-21*
