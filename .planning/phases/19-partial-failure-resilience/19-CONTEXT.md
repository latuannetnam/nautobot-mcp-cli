# Phase 19: Partial Failure Resilience - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Composite workflows (`bgp_summary`, `routing_table`, `firewall_summary`, `interface_detail`) return partial data with warnings instead of all-or-nothing failure. The response envelope gains a `"partial"` status tier and a `warnings` list with per-child-call failure details.

</domain>

<decisions>
## Implementation Decisions

### Warning Accumulation Pattern
- **D-01:** Use a `WarningCollector` context object (small class with `.add(operation, error)` method) passed into composite functions. Each composite receives and populates it.
- **D-02:** Warning format is `{"operation": "<function_name>", "error": "<error_message>"}` — operation name + error message, no fallback value.
- **D-03:** Warnings accumulate in a single flat list per composite call (not nested per-section).
- **D-04:** Upgrade ALL existing silent `except Exception: pass` blocks (~15 locations across `routing.py`, `firewalls.py`, `interfaces.py`, `workflows.py`) to capture warnings via the collector.
- **D-05:** Captured warnings also emit `logger.warning()` for server-side observability alongside envelope return.

### Partial Status Semantics
- **D-06:** Three-tier status model: `"ok"` (all succeeded), `"partial"` (primary data present, enrichment degraded), `"error"` (primary query failed).
- **D-07:** Rule: primary query fails → `error`; any enrichment query fails → `partial`; all succeed → `ok`.
- **D-08:** Breaking change accepted — agents must update to handle `"partial"` (v1.4 is a new milestone).
- **D-09:** When `status: "partial"`, the `error` field contains a summary string (e.g., `"2 of 4 enrichment queries failed"`) for quick agent inspection. Detailed failures are in `warnings`.

### Degradation Boundary
- **D-10:** Primary vs enrichment split is hardcoded per-function — developer marks each call site in the code. No registry configuration needed.
- **D-11:** Primary/enrichment mapping per composite:
  - `bgp_summary`: primary = `list_bgp_groups` + `list_bgp_neighbors`; enrichment = `list_bgp_address_families`, `list_bgp_policy_associations`
  - `routing_table`: primary = `list_static_routes`; enrichment = nexthop inlining
  - `firewall_summary`: co-primaries = `list_firewall_filters` + `list_firewall_policers` (independent — partial if either succeeds, error only if BOTH fail); enrichment = `list_firewall_terms`, `list_firewall_policer_actions`
  - `interface_detail`: primary = `list_interface_units`; enrichment = `list_interface_families`, `list_vrrp_groups`, `list_arp_entries`
- **D-12:** For `firewall_summary`, filters and policers are independent co-primaries (both are major Juniper firewall features). If one fails but the other succeeds → `partial`. Only if both fail → `error`.
- **D-13:** For `interface_detail` per-unit enrichment: if family queries fail for some units but succeed for others → `partial`, include units that succeeded with data and warn about per-unit failures.

### Envelope Shape Change
- **D-14:** `warnings` field added to `_build_envelope()` in `workflows.py` (envelope-level, not per-model).
- **D-15:** `warnings` is always present as `[]` even when no warnings — consistent for agent parsing.
- **D-16:** Each warning entry is `{"operation": "<name>", "error": "<message>"}` (matches D-02).
- **D-17:** Composite functions return a tuple `(result, warnings)` — `run_workflow()` unpacks and passes warnings to `_build_envelope()`. Explicit, no side effects.

### Agent's Discretion
- Implementation details of `WarningCollector` class (dataclass vs regular class, method signatures beyond `.add()`)
- Exact logger format for warning messages
- Test structure and organization

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — PFR-01 through PFR-04 define the acceptance criteria for this phase

### Pain Point Analysis
- Conversation `00f9a812-bc8e-42b6-8a30-c68cd9e36834` — Verified pain point analysis identifying the all-or-nothing failure pattern

### Current Implementation
- `nautobot_mcp/cms/routing.py` — `get_device_bgp_summary()` (L598) and `get_device_routing_table()` (L667) composite functions
- `nautobot_mcp/cms/firewalls.py` — `get_device_firewall_summary()` (L647) composite function
- `nautobot_mcp/cms/interfaces.py` — `get_interface_detail()` (L652) composite function
- `nautobot_mcp/workflows.py` — `_build_envelope()` (L146) and `run_workflow()` (L173) dispatch engine

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_build_envelope()` in `workflows.py` — central envelope builder, single point to add `warnings` + `status: "partial"`
- `_serialize_result()` in `workflows.py` — handles Pydantic/dataclass/dict serialization, will need tuple unpacking logic
- Existing `except Exception: pass` blocks — ~15 sites already catching failures silently, need upgrading to use WarningCollector

### Established Patterns
- All 4 composite functions follow the same structure: fetch primary → loop enrichment → build response model → return
- Response models (`BGPSummaryResponse`, `FirewallSummaryResponse`, etc.) are Pydantic models in `models/cms/composites.py`
- `run_workflow()` wraps all composite calls with try/except and builds envelopes — ideal interception point

### Integration Points
- `run_workflow()` in `workflows.py` — must unpack `(result, warnings)` tuples from composite functions
- `_build_envelope()` — add `warnings` parameter and `partial` status logic
- All 4 composite functions — accept `WarningCollector`, return `(result, collector.warnings)`
- Existing tests in `tests/test_workflows.py` — need new test cases for partial failure paths

</code_context>

<specifics>
## Specific Ideas

- Firewalls: filters and policers are co-equal features of Juniper firewall configuration — treat as independent co-primaries, not parent/child
- The `error` field serves double duty: `null` when ok, summary string when partial, full error when error

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 19-partial-failure-resilience*
*Context gathered: 2026-03-25*
