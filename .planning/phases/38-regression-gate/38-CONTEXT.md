# Phase 38: Regression Gate - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Gate all CMS N+1 query fixes (Phases 35-37) with:
1. UAT smoke test — all 5 CMS workflows pass within thresholds on HQV-PE1-NEW
2. Full unit test suite passes — no regression

Out of scope: CI integration, additional smoke test devices, threshold tightening.

</domain>

<decisions>
## Implementation Decisions

### Smoke Test Thresholds (D-01)
- **D-01:** Keep existing conservative thresholds as-is. No changes to `THRESHOLD_MS` in `scripts/uat_cms_smoke.py`:
  - `bgp_summary`: ≤5,000ms
  - `routing_table`: ≤15,000ms
  - `firewall_summary`: ≤15,000ms
  - `interface_detail`: ≤15,000ms
  - `devices_inventory`: ≤15,000ms

### Smoke Test Device Scope (D-02)
- **D-02:** Smoke test targets `HQV-PE1-NEW` only. No changes to device scope.

### Unit Test Scope (D-03)
- **D-03:** Run full unit test suite: `uv run pytest`. No filtering — ensures no regressions anywhere in the codebase, not just CMS N+1 fixes.

### CI Gate Integration (D-04)
- **D-04:** Smoke test is a manual developer tool only. No GitHub Actions CI gate — avoids gating PRs on prod hardware availability or network issues.

### Smoke Test Target Device Name
- **D-05:** Use `HQV-PE1-NEW` as the smoke test device. This is the canonical device with ~2,000 units, used consistently across all Phase 35-37 N+1 testing.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 38 Requirements
- `.planning/ROADMAP.md` — Phase 38: Regression Gate, Plan 01 (smoke), Plan 02 (unit tests)
- `.planning/REQUIREMENTS.md` §RGP — RGP-01 (smoke ≤60s all workflows on HQV-PE1), RGP-02 (full unit suite passes)

### Prior Phase Decisions
- `.planning/phases/35-interface-detail-n1-fix/35-CONTEXT.md` — CQP-01: ≤3 HTTP calls, inline prefetch, graceful degradation for VRRP
- `.planning/phases/36-firewall-summary-n1-fix/36-CONTEXT.md` — CQP-02: ≤6 HTTP calls, graceful degradation for terms/actions
- `.planning/phases/37-routing-table-bgp-n1-fixes/37-CONTEXT.md` — CQP-03: ≤3 HTTP calls, CQP-04: guard hardening, CQP-05: WarningCollector preserved

### Smoke Test Infrastructure
- `scripts/uat_cms_smoke.py` — Existing smoke test: 5 workflows, THRESHOLD_MS dict, HQV-PE1-NEW target, pynautobot monkey-patch counter

### Unit Test Infrastructure
- `tests/test_cms_interfaces_n1.py` — Phase 35 N+1 invariant tests (348 lines)
- `tests/test_cms_firewalls_n1.py` — Phase 36 N+1 invariant tests (517 lines)
- `tests/test_cms_routing_n1.py` — Phase 37 N+1 invariant tests (361 lines)

</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- `scripts/uat_cms_smoke.py` — Already fully functional. Only needs to be run, not modified.
- `tests/test_cms_interfaces_n1.py` — Monkey-patch `cms_list` to count HTTP calls. Pattern proven.
- `tests/test_cms_firewalls_n1.py` — Same monkey-patch pattern for firewalls.
- `tests/test_cms_routing_n1.py` — Same monkey-patch pattern for routing/bgp.

### Established Patterns
- Smoke test: `uv run nautobot-mcp --json <command>` subprocess call, exit 0 = pass, threshold check
- HTTP call counter: pynautobot `Request._make_call` monkey-patch
- Unit tests: `pytest` with `uv run pytest` invocation

### Integration Points
- Smoke test calls: `nautobot-mcp --json cms routing bgp-summary --device`, `cms routing routing-table --device`, `cms firewalls firewall-summary --device`, `cms interfaces detail --device`, `devices inventory <device>`
- Unit tests: `pytest tests/` (all test files, no filtering)

</codebase_context>

<specifics>
## Specific Ideas

- "Keep conservative thresholds — don't over-tune. If it passes 5s/15s, it's good enough."
- "Full unit test suite — don't filter. 530 tests gives us confidence across the whole codebase."
- "Manual smoke test only — don't gate CI on prod hardware. Too risky."
- "HQV-PE1-NEW is the canonical test device — used consistently across Phases 35-37."

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 38-regression-gate*
*Context gathered: 2026-03-31*
