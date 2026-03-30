---
phase: 33
plan: 03
slug: regression-prevention
status: draft
wave: 1
dependencies: [01]
autonomous: false
requirements: [REG-01, REG-02, REG-03]
must_haves:
  - `THRESHOLD_MS` dict added to `uat_cms_smoke.py` with bgp_summary < 5000ms threshold
  - Threshold enforcement logic added to `run_workflow()` — `passed` is False if elapsed_ms > threshold
  - All existing unit tests pass (`uv run pytest tests/test_cms_client.py tests/test_cms_routing.py -v`)
  - Smoke script committed and pushed
---

# Plan 03: Regression Prevention

**Phase:** 33 — CMS Pagination Fix
**Goal:** Add performance thresholds to smoke test; ensure no regression; commit smoke script
**Requirements:** REG-01, REG-02, REG-03

## Wave 1

### Task 33-03-01: Add threshold enforcement to `uat_cms_smoke.py`

<read_first>
- `scripts/uat_cms_smoke.py` — L1-225 (entire file, current implementation)
- `scripts/uat_cms_smoke.py` — specifically: `WORKFLOWS` dict (L26-72), `WorkflowResult` dataclass (L75-84), `run_workflow()` (L86-176), `print_results()` (L179-195)
</read_first>

<action>
Make two additions to `scripts/uat_cms_smoke.py`:

**Addition 1 — `THRESHOLD_MS` dict:** Add immediately after `WORKFLOWS` (after L72, before the blank line at L73):

```python
# Performance thresholds: workflow_id → max_allowed_ms
# bgp_summary: was ~80s before fix; target <5s per v1.8 requirement (REG-01)
# Other thresholds: conservative 2x estimates; update to 2× empirically observed
# post-fix times per D-06.
THRESHOLD_MS: dict[str, float] = {
    "bgp_summary": 5000.0,
    "routing_table": 15000.0,
    "firewall_summary": 15000.0,
    "interface_detail": 15000.0,
    "devices_inventory": 15000.0,
}
```

**Addition 2 — Threshold check in `run_workflow()`:** After the `elapsed_ms` assignment (L99, after `elapsed_ms = round(...)`), add:

```python
    # Threshold check — evaluate before parsing to catch slow-but-successful runs
    threshold = THRESHOLD_MS.get(workflow["id"])
    exceeded = threshold is not None and elapsed_ms > threshold
```

Then in the final `return WorkflowResult(...)` block (around L168-176), update `passed` and `error`:

Update this existing line:
```python
    passed = result.returncode == 0
```
to:
```python
    passed = result.returncode == 0 and not exceeded
```

And update the `error` assignment. In the current code, `error=None` is hardcoded. Replace the `return WorkflowResult(...)` block so that:

```python
    if exceeded:
        threshold_error = f"Threshold exceeded: {elapsed_ms:.0f}ms > {threshold:.0f}ms"
    else:
        threshold_error = None

    return WorkflowResult(
        id=workflow["id"],
        name=workflow["name"],
        passed=passed,
        elapsed_ms=elapsed_ms,
        status=None,
        error=threshold_error,
        summary=" | ".join(summary_parts),
    )
```

Note: `summary_parts` is built before the threshold check and only reflects exit-code state. Threshold-exceeded runs still get `summary_parts.append("FAIL")` and `summary_parts.append(f"exit={result.returncode}")` from the existing logic. The `threshold_error` is set independently of the existing error handling. Ensure the final `return` uses `error=threshold_error`, not `error=None`.
</action>

<acceptance_criteria>
- [ ] `grep -n "THRESHOLD_MS" scripts/uat_cms_smoke.py` returns exactly 1 definition match plus references in `run_workflow()` and `print_results()`
- [ ] `grep -n "bgp_summary.*5000\|5000.*bgp_summary" scripts/uat_cms_smoke.py` returns match
- [ ] `grep -n "exceeded" scripts/uat_cms_smoke.py` returns `exceeded = ...` assignment and `if exceeded:` check in return block
- [ ] `grep -n "threshold" scripts/uat_cms_smoke.py` returns at least 3 matches: dict, `threshold = ...` assignment, `threshold_info` in print
- [ ] `uv run python -c "exec(open('scripts/uat_cms_smoke.py').read())"` — script parses without syntax errors
- [ ] **REG-01 verified:** bgp_summary threshold is exactly `5000.0` ms in `THRESHOLD_MS`
- [ ] **REG-01 verified:** A workflow whose elapsed_ms > threshold gets `passed=False`
</acceptance_criteria>

---

### Task 33-03-02: Run full test suite — verify no regression

<read_first>
- `tests/test_cms_client.py` — existing tests, especially `TestCMSList` (L149-186)
- `tests/test_cms_routing.py` — existing CMS routing tests
- `nautobot_mcp/cms/client.py` — modified `cms_list()` with `_CMS_BULK_LIMIT` (Plan 01 output)
</read_first>

<action>
Run the full CMS test suite to verify no regressions:

```bash
uv run pytest tests/test_cms_client.py tests/test_cms_routing.py -v
```

The `TestCMSList` class tests (L149-186 in `test_cms_client.py`) will be affected by the pagination fix:
- `test_list_with_limit` (L175-185): passes `limit=1` — the `elif limit > 0` branch is taken — **no change to behavior** — must still pass
- `test_list_all` (L152-161): calls `cms_list(...)` without explicit `limit` — takes the new `if limit == 0` branch — **now calls `.all(limit=200)` instead of `.all()` with no kwarg** — mock must still work

The `mock_client_with_cms.cms.juniper_static_routes.all` fixture returns `[mock_cms_record]` regardless of what kwargs are passed. The existing `test_list_all` test does NOT assert on the kwargs, so it will continue to pass with the fix. The new `TestCMSListPagination` tests explicitly assert on kwargs — they are additive and do not affect existing tests.

Also run a quick sanity check on non-CMS tests:
```bash
uv run pytest tests/test_bridge.py -v --timeout=30
```
</action>

<acceptance_criteria>
- [ ] `uv run pytest tests/test_cms_client.py -v` — all tests pass (existing + new `TestCMSListPagination`)
- [ ] `uv run pytest tests/test_cms_routing.py -v` — all tests pass
- [ ] `uv run pytest tests/test_cms_client.py::TestCMSList::test_list_all -v` — still passes after pagination fix
- [ ] `uv run pytest tests/test_cms_client.py::TestCMSList::test_list_with_limit -v` — still passes (limit=1 preserved)
- [ ] **REG-02 verified:** All existing tests pass — no behavioral regression
</acceptance_criteria>

---

### Task 33-03-03: Commit and push smoke script changes

<read_first>
- `scripts/uat_cms_smoke.py` — final state after Task 33-02-01 and 33-03-01
- `.git/COMMIT_EDITMSG` or recent commit messages for style reference
</read_first>

<action>
Create a commit for the Phase 33 changes. The commit should include:

1. **Files to stage:**
   - `scripts/uat_cms_smoke.py` — HTTP counter instrumentation (Task 33-02-01) + threshold enforcement (Task 33-03-01)

2. **Commit message:**
```
feat(smoke): instrument HTTP call counter and add performance thresholds

- Add monkey-patch HTTP call counter via pynautobot Request._make_call
  to measure HTTP call counts per CMS endpoint (DISC-01)
- Add THRESHOLD_MS dict: bgp_summary=5000ms, others=15000ms (REG-01)
- Threshold enforcement: run fails if elapsed_ms exceeds threshold
- Call counts printed per workflow in smoke test output

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

3. **Verification after push:**
   - `git log --oneline -1 scripts/uat_cms_smoke.py` shows the Phase 33 commit

Note: `nautobot_mcp/cms/client.py` and `tests/test_cms_client.py` changes (Plan 01) are committed in the Phase 33 implementation commit, not in this smoke-script-only commit. If Plan 01 changes have already been committed, this commit only touches `scripts/uat_cms_smoke.py`. The exact scope depends on whether Plan 01 was committed first or all Phase 33 changes are in one commit.

Per convention: commit Plan 01 changes first, then this smoke script commit. If both are in the same working tree, combine them into one commit covering all Phase 33 changes.
</action>

<acceptance_criteria>
- [ ] `git status scripts/uat_cms_smoke.py` — file is staged
- [ ] Commit message contains `feat(smoke)` and `THRESHOLD_MS`
- [ ] `git log --oneline -1 scripts/uat_cms_smoke.py` shows a Phase 33 commit hash
- [ ] **REG-03 verified:** Smoke script is committed (not just saved)
- [ ] **REG-03 verified:** Commit is pushed (or `git log --oneline -1` confirms local commit exists if remote push is pending)
</acceptance_criteria>

---

## Summary

| Task | Requirement | Status |
|------|-------------|--------|
| 33-03-01 | REG-01 (threshold enforcement in smoke test) | ⬜ |
| 33-03-02 | REG-02 (all existing unit tests pass) | ⬜ |
| 33-03-03 | REG-03 (smoke script committed) | ⬜ |

**Quality gate:** `uv run pytest tests/test_cms_client.py tests/test_cms_routing.py -v` must be green; smoke script commit hash visible in `git log`.
