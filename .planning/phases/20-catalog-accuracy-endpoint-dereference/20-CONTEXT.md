# Phase 20: Catalog Accuracy & Endpoint Dereference - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix false filter advertisement in the CMS catalog (all 33 endpoints falsely report `["device"]` as their filter) by replacing domain-level `CMS_DOMAIN_FILTERS` with a per-endpoint filter registry. Enable linked object URL follow in the REST bridge by stripping UUID path segments before validation. Nested endpoint paths (e.g., `/devices/<uuid>/interfaces/`) are deferred.

</domain>

<decisions>
## Implementation Decisions

### Per-Endpoint Filter Registry
- **D-01:** Replace `CMS_DOMAIN_FILTERS` dict with a flat `CMS_ENDPOINT_FILTERS` dict in `cms_discovery.py`, keyed by endpoint name (e.g., `"juniper_bgp_neighbors": ["group"]`).
- **D-02:** Advertise only primary FK filter(s) per endpoint — the filters an agent would actually use to query meaningful data. Skip universal DRF filters (`id`, `created`, `last_updated`).
- **D-03:** Only ~12 of 33 endpoints support `device` as a direct filter. The rest use FK-based filters to their parent model (e.g., `group`, `firewall_filter`, `policy_statement`, `interface_unit`).
- **D-04:** Complete per-endpoint filter map (derived from codebase analysis of all `cms_list()` call sites):
  - `juniper_static_routes`: `["device"]`
  - `juniper_static_route_nexthops`: `["route"]`
  - `juniper_static_route_qualified_nexthops`: `["route"]`
  - `juniper_bgp_groups`: `["device"]`
  - `juniper_bgp_neighbors`: `["group"]`
  - `juniper_bgp_address_families`: `["group", "neighbor"]`
  - `juniper_bgp_policy_associations`: `["group", "neighbor"]`
  - `juniper_bgp_received_routes`: `["neighbor"]`
  - `juniper_interface_units`: `["device"]`
  - `juniper_interface_families`: `["interface_unit"]`
  - `juniper_interface_family_filters`: `["interface_family"]`
  - `juniper_interface_family_policers`: `["interface_family"]`
  - `juniper_interface_vrrp_groups`: `["interface_family"]`
  - `vrrp_track_routes`: `["vrrp_group"]`
  - `vrrp_track_interfaces`: `["vrrp_group"]`
  - `juniper_firewall_filters`: `["device"]`
  - `juniper_firewall_terms`: `["firewall_filter"]`
  - `juniper_firewall_match_conditions`: `["firewall_term"]`
  - `juniper_firewall_actions`: `["firewall_term"]`
  - `juniper_firewall_policers`: `["device"]`
  - `juniper_firewall_policer_actions`: `["policer"]`
  - `juniper_firewall_match_condition_prefix_lists`: `["match_condition"]`
  - `juniper_policy_statements`: `["device"]`
  - `jps_terms`: `["policy_statement"]`
  - `jps_match_conditions`: `["jps_term"]`
  - `jps_match_condition_route_filters`: `["match_condition"]`
  - `jps_match_condition_prefix_lists`: `["match_condition"]`
  - `jps_match_condition_communities`: `["match_condition"]`
  - `jps_match_condition_as_paths`: `["match_condition"]`
  - `jps_actions`: `["jps_term"]`
  - `jps_action_communities`: `["action"]`
  - `jps_action_as_paths`: `["action"]`
  - `jps_action_load_balances`: `["action"]`
  - `jps_action_install_nexthops`: `["action"]`
  - `juniper_policy_as_paths`: `["device"]`
  - `juniper_policy_communities`: `["device"]`
  - `juniper_policy_prefix_lists`: `["device"]`
  - `juniper_policy_prefixes`: `["prefix_list"]`
  - `juniper_arp_entries`: `["device"]`

### UUID Path Normalization
- **D-05:** Strip UUID segments from endpoint paths in `_validate_endpoint()` before catalog lookup. Regex: `/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/` → extract UUID as `id`, validate the stripped path.
- **D-06:** Transparently convert `/api/dcim/device-types/<uuid>/` to `call_nautobot("/api/dcim/device-types/", id="<uuid>")` internally — agent doesn't need to decompose URLs.
- **D-07:** Nested paths (e.g., `/api/dcim/devices/<uuid>/interfaces/`) are out of scope for v1.4. Deferred to a future phase.

### Filter Source of Truth
- **D-08:** Hardcode the per-endpoint filter map from codebase analysis (D-04). No runtime introspection via OPTIONS.
- **D-09:** When the CMS plugin adds new endpoints, developers add a line to `CMS_ENDPOINT_FILTERS` alongside the `CMS_ENDPOINTS` registry entry.

### Backward Compatibility
- **D-10:** Clean break — no backward compatibility shim. v1.4 is a new milestone. Agents must update to handle the changed filter lists.
- **D-11:** Follows the v1.3 precedent: "Clean break, no aliases" (STATE.md).

### Agent's Discretion
- UUID regex implementation details (compiled vs inline)
- Test structure and organization for new test cases
- Error message wording for UUID stripping edge cases

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — CAT-07, CAT-08, CAT-09 (catalog accuracy), DRF-01, DRF-02, DRF-03 (endpoint dereference)

### Current Implementation
- `nautobot_mcp/catalog/cms_discovery.py` — `CMS_DOMAIN_FILTERS` (to be replaced), `discover_cms_endpoints()` function
- `nautobot_mcp/bridge.py` — `_validate_endpoint()` (needs UUID stripping), `_parse_core_endpoint()` (needs UUID awareness)
- `nautobot_mcp/cms/client.py` — `CMS_ENDPOINTS` registry (read-only reference for filter map)

### Existing Tests
- `tests/test_catalog.py` — 198 lines, covers catalog completeness, CMS discovery, domain filtering, workflow stubs
- `tests/test_bridge.py` — 483 lines, covers endpoint validation, fuzzy matching, CRUD operations, pagination, CMS routing

### Pain Point Analysis
- Conversation `00f9a812-bc8e-42b6-8a30-c68cd9e36834` — Verified pain point analysis confirming filter mismatch and dereference gap

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_validate_endpoint()` in `bridge.py` — single validation point, ideal for adding UUID stripping logic
- `_parse_core_endpoint()` in `bridge.py` — parses `/api/{app}/{endpoint}/`, needs extension for UUID segment
- `discover_cms_endpoints()` in `cms_discovery.py` — reads `CMS_DOMAIN_FILTERS`, change to read `CMS_ENDPOINT_FILTERS` instead
- `_suggest_endpoint()` in `bridge.py` — fuzzy matching already works, UUID stripping happens before this

### Established Patterns
- `CMS_ENDPOINTS` is a flat `{endpoint_name: model_name}` dict — `CMS_ENDPOINT_FILTERS` follows the same flat dict pattern
- `_validate_endpoint()` checks `/api/` prefix then `cms:` prefix — UUID stripping fits before the catalog match step
- All CMS catalog entries get their filters from `CMS_DOMAIN_FILTERS.get(domain, ["device"])` — single line to change

### Integration Points
- `discover_cms_endpoints()` line 84 — replace `CMS_DOMAIN_FILTERS.get(domain, ["device"])` with `CMS_ENDPOINT_FILTERS.get(endpoint_name, ["device"])`
- `_validate_endpoint()` in `bridge.py` — add UUID detection + stripping before catalog match
- `call_nautobot()` in `bridge.py` — if UUID extracted from path, pass as `id` parameter
- `tests/test_catalog.py` — update CMS entry tests to validate per-endpoint filter accuracy
- `tests/test_bridge.py` — add UUID path normalization test cases

</code_context>

<specifics>
## Specific Ideas

- The filter map in D-04 was derived by tracing every `cms_list()` call in `routing.py`, `firewalls.py`, `interfaces.py`, and `policies.py`
- BGP neighbors is the canonical example of wrong filter advertisement — agents get 400 errors trying `device` filter when they should use `group`

</specifics>

<deferred>
## Deferred Ideas

- **Nested endpoint traversal** — Support `/api/dcim/devices/<uuid>/interfaces/` style paths via raw HTTP fallback or decompose+redirect. Deferred from Area 2 discussion.
- **Runtime filter introspection** — Optional CLI command `--verify-filters` that cross-checks hardcoded map against live OPTIONS responses. Deferred from Area 3 discussion.

</deferred>

---

*Phase: 20-catalog-accuracy-endpoint-dereference*
*Context gathered: 2026-03-25*
