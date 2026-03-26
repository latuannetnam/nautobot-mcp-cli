# Phase 22: Response Ergonomics & UAT - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Add summary modes, response size metadata, and limit parameters to composite workflows. Validate all v1.4 fixes (PFR, CAT, DRF, WFC, ERR) end-to-end against the Nautobot dev server. Affects `interfaces.py`, `workflows.py`, smoke script, and test suite.

</domain>

<decisions>
## Implementation Decisions

### Summary Mode Depth (RSP-01)

- **D-01:** `detail=False` strips `families[]` arrays AND their `vrrp_groups[]` sub-arrays entirely from each unit.
- **D-02:** `family_count` and `vrrp_group_count` stay at unit level even in `detail=False` mode — agents retain counts without the full nested payload.
- **D-03:** `arp_entries` block is controlled by the existing `include_arp` flag — `detail=False` does NOT affect ARP inclusion.
- **D-04:** `detail=True` (default) returns full enriched data — all families, VRRP groups, and ARP entries as before.
- **D-05:** `get_interface_detail()` function signature gains a `detail: bool = True` parameter. Registry `param_map` already has it from Phase 21 (it was added then but the function didn't implement it).

### limit Parameter Design (RSP-03)

- **D-06:** `limit=0` means "no cap" (Nautobot convention: limit=0 = return all). Positive integer caps each result array.
- **D-07:** Applies per-array within each composite (units[], routes[], neighbors[], groups[], filters[], policers[]) — each array independently capped at the `limit` value.
- **D-08:** Applied to ALL composites: `bgp_summary`, `routing_table`, `firewall_summary`, `interface_detail`.
- **D-09:** `limit` is optional across all composites — defaults to `0` (no cap). Agents opt into capping, not out of it.
- **D-10:** Registry `param_map` gains `"limit": "limit"` for all composites. Function signatures updated accordingly.

### response_size_bytes Semantics (RSP-02)

- **D-11:** `response_size_bytes` measures `len(json.dumps(response_body))` — the size of the JSON-encoded response body string.
- **D-12:** Always present in the envelope for all composites (not conditional on size threshold).
- **D-13:** Included in ALL composites: `bgp_summary`, `routing_table`, `firewall_summary`, `interface_detail`.
- **D-14:** Measured after the full response is assembled and serialized — represents the on-wire payload size an agent would receive.

### UAT Validation Scope

- **D-15:** Smoke script (`smoke.py` or equivalent) updated with checks for all three RSP requirements:
  - RSP-01: `detail=False` returns counts-only for families/VRRP
  - RSP-02: envelope includes `response_size_bytes`
  - RSP-03: `limit=N` caps result arrays
- **D-16:** Pytest test suite (`tests/`) gains dedicated test cases for all three RSP requirements:
  - `test_interface_detail_summary_mode()` — validates detail=False stripping behavior
  - `test_response_size_bytes_in_envelope()` — validates size field presence across composites
  - `test_limit_parameter_*()` — one test per composite validating cap behavior
- **D-17:** All 415+ existing tests continue to pass after RSP changes.
- **D-18:** "Passes against dev server" = smoke script exits with `[PASS]` on all RSP checks, AND pytest suite (excluding `live` marker) passes.

### Claude's Discretion
- Exact `detail=False` implementation (which specific nested fields to strip, how to handle empty arrays)
- Exact limit application logic within each composite function (how to slice arrays: `[:limit]` vs paginate)
- Smoke script file name and location (check existing smoke script)
- Pytest test file organization (new file vs additions to existing test_workflows.py)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — RSP-01, RSP-02, RSP-03 (response ergonomics)

### Prior Phase Decisions
- `.planning/phases/19-partial-failure-resilience/19-CONTEXT.md` — WarningCollector, three-tier status, primary/enrichment split
- `.planning/phases/21-workflow-contracts-error-diagnostics/21-CONTEXT.md` — _build_envelope() signature, detail param_map entry, NautobotValidationError.errors

### Current Implementation
- `nautobot_mcp/cms/interfaces.py` — `get_interface_detail()` (L653) — needs `detail` param implementation
- `nautobot_mcp/cms/routing.py` — `get_device_bgp_summary()`, `get_device_routing_table()` composites
- `nautobot_mcp/cms/firewalls.py` — `get_device_firewall_summary()` composite
- `nautobot_mcp/workflows.py` — `WORKFLOW_REGISTRY` (needs limit + detail on all composites), `_build_envelope()` (needs response_size_bytes)
- `nautobot_mcp/models/cms/composites.py` — Pydantic response models for all composites
- `smoke.py` or `smoke_test.py` — existing standalone smoke script (find and update)

### Existing Tests
- `tests/test_workflows.py` — 60 lines, registry sync guard tests (add RSP tests here)
- `tests/test_interfaces.py` — existing interface tests (add summary mode tests here)
- Existing smoke script — 9 checks, needs RSP coverage additions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `detail` param already in `param_map` for `bgp_summary` and `interface_detail` (Phase 21) — registry is ready, functions need updating
- `_build_envelope()` in `workflows.py` — single point to add `response_size_bytes` to every composite envelope
- `WarningCollector` context from Phase 19 — used for enrichment query failures
- `(result, warnings)` tuple return pattern — limit logic can be applied before returning

### Established Patterns
- `limit=0` in Nautobot means "no limit" — conflicts with Python falsy semantics, resolved by treating `0` as sentinel
- Array slicing via `[:limit]` — Python idiom for capping list length
- `json.dumps()` + `len()` — standard way to measure JSON payload size in Python
- Composite functions aggregate multiple API calls into one response — `response_size_bytes` should reflect the final serialized response size

### Integration Points
- `get_interface_detail()` — add `detail: bool = True` parameter, implement summary stripping
- All composite functions — add `limit: int = 0` parameter, apply per-array cap
- `run_workflow()` in `workflows.py` — measure serialized response size after `_serialize_result()`, pass to `_build_envelope()`
- `_build_envelope()` — add `response_size_bytes` to return dict
- Smoke script — add RSP-01/02/03 checks
- Pytest suite — add RSP test cases

</code_context>

<specifics>
## Specific Ideas

- Summary mode (detail=False) targets the families[] and vrrp_groups[] nesting — this is where interface_detail grows large
- limit applies per-array independently — e.g., interface_detail with limit=10 returns up to 10 units, each with up to 10 families
- response_size_bytes should reflect what the agent actually receives over the wire

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-response-ergonomics-uat*
*Context gathered: 2026-03-26*
