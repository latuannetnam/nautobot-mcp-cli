# Phase 38: Regression Gate — Research

**Researched:** 2026-03-31
**Status:** COMPLETE

---

## Research Findings

### 1. Smoke Test Execution (uat_cms_smoke.py)

- **Mechanism:** The script instruments pynautobot's `Request._make_call` with a monkey-patch that counts HTTP calls per URL path (lines 31–46 of `scripts/uat_cms_smoke.py`). It installs once globally, then reads call counts after each subprocess completes.

- **Execution flow:**
  1. `_install_counter()` patches pynautobot (no-op if already installed)
  2. For each of 5 workflows: runs `uv run nautobot-mcp --json <cmd>` as subprocess with 120s timeout
  3. `time.monotonic()` measures wall-clock elapsed ms
  4. **Pass criteria:** `returncode == 0` AND `elapsed_ms <= THRESHOLD_MS`
  5. `_get_counts()` snapshots and resets the per-workflow HTTP call counts
  6. Summary table printed; exit code 0 = all pass, 1 = any fail

- **5 workflows tested:**
  | ID | CLI command |
  |----|-------------|
  | `bgp_summary` | `cms routing bgp-summary --device HQV-PE1-NEW` |
  | `routing_table` | `cms routing routing-table --device HQV-PE1-NEW` |
  | `firewall_summary` | `cms firewalls firewall-summary --device HQV-PE1-NEW` |
  | `interface_detail` | `cms interfaces detail --device HQV-PE1-NEW` |
  | `devices_inventory` | `devices inventory HQV-PE1-NEW` |

- **Evidence:** `scripts/uat_cms_smoke.py`, lines 69–117 (`_build_workflows()`), lines 218–328 (`run_workflow()`)

- **Implication for planning:** The smoke test is a standalone Python script — no modification needed. Execution requires `NAUTOBOT_URL` + `NAUTOBOT_TOKEN` environment variables (or `--profile prod/dev`). HQV-PE1-NEW must be reachable and have JunOS CMS data. Exit 0 = RGP-01 satisfied.

---

### 2. Smoke Test Prior Performance Data

- **Historical baseline:** `uat_cms_smoke.py` line 192 comment: "bgp_summary: was ~80s before fix; target <5s per v1.8 requirement (REG-01)". This is the v1.8 Phase 33 fix result.

- **Phase 37 unit test run (145f2c5):** "548 unit tests pass" — the final count after 9 routing/BGP N+1 tests were added.

- **No live smoke timings in commits:** The smoke test was run against prod manually (manual-only per D-04). No timestamped output was committed. Empirical baselines must come from this phase's actual run.

- **Thresholds (confirmed conservative):**
  | Workflow | Threshold | Rationale |
  |----------|-----------|-----------|
  | `bgp_summary` | 5,000 ms | Was 80s pre-v1.8; now ~1-3s expected |
  | `routing_table` | 15,000 ms | Conservative; no pre-fix benchmark |
  | `firewall_summary` | 15,000 ms | Conservative; N+1 was >120s |
  | `interface_detail` | 15,000 ms | Conservative; N+1 was ~2,000 calls |
  | `devices_inventory` | 15,000 ms | Conservative; baseline established |

- **Decision D-01** (38-CONTEXT.md): "Keep existing conservative thresholds as-is. No changes to `THRESHOLD_MS`." — confirmed.

- **Implication for planning:** After running the smoke test, actual timings should be documented in the phase summary. If all 5 pass comfortably, thresholds are confirmed conservative. No threshold tightening in this phase.

---

### 3. Unit Test Baseline

- **Current count:** 558 tests collected, 569 total (11 deselected)
- **Previous count (Phase 37 commit 145f2c5):** 548 tests — 10 tests added in Phase 37 Plan 03
- **Breakdown by N+1 test file:**
  | File | Tests | Phase | Coverage |
  |------|-------|-------|---------|
  | `tests/test_cms_interfaces_n1.py` | 8 | Phase 35 | CQP-01 |
  | `tests/test_cms_firewalls_n1.py` | 8 | Phase 36 | CQP-02 |
  | `tests/test_cms_routing_n1.py` | 9 | Phase 37 | CQP-03 + CQP-04 |
  | **N+1 subtotal** | **25** | | |

- **CMS-adjacent test files:** `test_cms_composites.py` (25 tests — composite response model validation), `test_cms_client.py` (17 tests), `test_cms_routing.py`, `test_cms_firewalls.py`, `test_cms_interfaces.py`, `test_cms_arp.py`, `test_cms_policies.py`, `test_cms_drift.py`

- **Evidence:** `uv run pytest --collect-only -q 2>&1 | tail -10` → "558/569 tests collected (11 deselected) in 0.78s"

- **Implication for planning:** The baseline is 558 tests. After Phase 37, no new tests were added to non-N+1 files. Running `uv run pytest -q` is the validation step for RGP-02. Exit 0 = RGP-02 satisfied.

---

### 4. N+1 Test Coverage

- **Coverage matrix for the 4 fixed workflows:**
  | Workflow | N+1 test file | Tests | Invariants verified |
  |----------|--------------|-------|----------------------|
  | `interface_detail` | `test_cms_interfaces_n1.py` | 8 | ≤3 bulk calls; no per-unit/per-family loops; graceful VRRP degradation; family hard-fail; prefetch map enrichment; summary mode |
  | `firewall_summary` | `test_cms_firewalls_n1.py` | 8 | ≤2 bulk calls; no per-filter/per-policer loops; graceful terms/actions degradation; prefetch map enrichment; detail=False unaffected |
  | `routing_table` | `test_cms_routing_n1.py` (routing section) | 5 | ≤3 bulk calls; no per-route fallback; empty nexthops graceful; bulk exception silent; 50-route scale invariant |
  | `bgp_summary` | `test_cms_routing_n1.py` (BGP section) | 4 | Guard prevents AF/policy calls at 0 neighbors; ≤2 bulk calls with detail=True; af_keyed_usable=False suppresses fallback; AF bulk exception WarningCollector |

- **All 4 workflows covered ✓** — no gaps in N+1 invariant coverage.

- **Minor note (non-blocking):** `test_bgp_summary_guard_0_neighbors` tests the `detail=True` path with 0 neighbors. The `detail=False` path is untested for N+1 specifically, but `list_bgp_address_families` and `list_bgp_policy_associations` are only called in the `detail:` block — confirmed in `cms/routing.py`. This is a cosmetic gap, not a functional risk.

- **Evidence:** Tests listed above; confirmed by test function names and `assert` statements in each file.

- **Implication for planning:** All N+1 invariants are already tested. The Phase 38 unit test run will re-exercise all 25 N+1 tests plus 533 other tests. No new tests needed.

---

### 5. Execution Strategy

- **Phase type:** Pure execution — no code changes, no new tests, no refactoring.
- **38-CONTEXT.md** explicitly states: "Keep existing conservative thresholds as-is", "Run full unit test suite", "Manual smoke test only — don't gate CI on prod hardware".
- **Two deliverables → two sequential plans:**
  - **Plan 01 — Smoke Test:** Run `uat_cms_smoke.py` against HQV-PE1-NEW on prod; document actual timings; confirm 5/5 PASS.
  - **Plan 02 — Unit Tests:** Run `uv run pytest -q`; confirm 558/558 PASS; commit if all green.
- **No code changes in either plan** — purely observational and pass/fail.
- **Dependency:** Plan 01 output (actual timing data) is useful context for Plan 02 summary, but Plan 02 is independent and can proceed regardless.

- **Implication for planning:** Both plans are trivially short (one command each). Combined execution time: ~5–15 minutes for smoke test (prod network), ~30 seconds for unit tests. Total phase clock time: ~15–30 minutes.

---

## Validation Architecture

### RGP-01: Smoke Test Gate

```
Command:  uv run python scripts/uat_cms_smoke.py HQV-PE1-NEW [--profile prod]
          (or: NAUTOBOT_URL=https://nautobot.netnam.vn NAUTOBOT_TOKEN=<x> uv run python scripts/uat_cms_smoke.py HQV-PE1-NEW)

Success criteria:
  - All 5 workflow results show PASS
  - No workflow exceeds THRESHOLD_MS (bgp_summary ≤5000ms, others ≤15000ms)
  - No timeouts (120s hard limit)
  - Exit code 0

Verification artifact: Phase 38 plan summary includes actual elapsed_ms per workflow
```

### RGP-02: Unit Test Gate

```
Command:  uv run pytest -q

Success criteria:
  - All 558 tests collected → 558 passed
  - 0 failed, 0 errored
  - Exit code 0

Verification artifact: pytest output line "558 passed in ~Xs"
```

### Combined Gate

```
Both gates must pass:
  RGP-01: smoke test → 5/5 PASS
  RGP-02: unit tests → 558/558 PASS
→ Phase 38 COMPLETE
→ RGP-01 and RGP-02 marked Done in REQUIREMENTS.md
```

---

## Key Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Prod server unreachable during smoke test | Low | Run with `--profile dev` fallback; document if prod unavailable |
| HQV-PE1-NEW has changed CMS data | Low | Smoke test covers 5 workflows; partial data → workflow-specific failure, not crash |
| Timing flakiness on prod | Low | Conservative 5s/15s thresholds; flakiness would show as occasional FAIL |
| New test file added mid-phase | Low | Collect-only before run; compare count to 558 baseline |
| Non-CMS code regression from Phase 35-37 | Very Low | Full suite run covers all 26 test files; N+1 changes were isolated to CMS module |

---

## Recommended Phase Structure

Given the pure-execution nature, the phase has exactly 2 lightweight plans:

| Plan | Action | Command | Success criteria |
|------|--------|---------|-----------------|
| 01 | Smoke test | `uv run python scripts/uat_cms_smoke.py HQV-PE1-NEW` | 5/5 PASS, exit 0 |
| 02 | Unit suite | `uv run pytest -q` | 558/558 PASS, exit 0 |

No new code, no new tests, no threshold changes. Phase complete when both exit 0.
