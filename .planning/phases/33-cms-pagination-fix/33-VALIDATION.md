---
phase: 33
slug: cms-pagination-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` or `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/test_cms_client.py -v -k "pagination or bulk_limit"` |
| **Full suite command** | `uv run pytest tests/test_cms_client.py tests/test_cms_routing.py -v` |
| **Estimated runtime** | ~15 seconds (unit tests), ~60 seconds (smoke UAT) |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds (unit), 60 seconds (UAT smoke)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 33-01-01 | 01 | 1 | PAG-01, PAG-02 | unit | `pytest tests/test_cms_client.py::TestCMSListPagination -v` | ✅ | ⬜ pending |
| 33-01-02 | 01 | 1 | PAG-03 | code review | grep `_CMS_BULK_LIMIT = 200` in `cms/client.py` | ✅ | ⬜ pending |
| 33-01-03 | 01 | 1 | PAG-04 | unit | `pytest tests/test_cms_client.py::TestCMSListPagination::test_limit_zero_uses_bulk_limit -v` | ✅ | ⬜ pending |
| 33-01-04 | 01 | 1 | PAG-05 | unit | `pytest tests/test_cms_client.py::TestCMSListPagination::test_explicit_positive_limit_preserved -v` | ✅ | ⬜ pending |
| 33-01-05 | 01 | 1 | PAG-06 | unit | `pytest tests/test_cms_client.py::TestCMSListPagination::test_limit_zero_with_filters_uses_bulk_limit -v` | ✅ | ⬜ pending |
| 33-02-01 | 02 | 1 | DISC-01 | UAT | `uat_cms_smoke.py` with HTTP call counting (monkey-patch) | ✅ | ⬜ pending |
| 33-02-02 | 02 | 1 | DISC-02 | summary doc | No code change — findings written to Phase 33 summary | ✅ | ⬜ pending |
| 33-03-01 | 03 | 1 | REG-01 | UAT | `uat_cms_smoke.py` bgp_summary < 5000ms | ✅ | ⬜ pending |
| 33-03-02 | 03 | 1 | REG-02 | unit | `uv run pytest tests/test_cms_client.py tests/test_cms_routing.py tests/test_cms_composites.py -v` | ✅ | ⬜ pending |
| 33-03-03 | 03 | 1 | REG-03 | git | `git status scripts/uat_cms_smoke.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cms_client.py` — add `TestCMSListPagination` class with PAG-04/05/06 tests
- [ ] `scripts/uat_cms_smoke.py` — add `THRESHOLD_MS` dict + threshold enforcement check
- [ ] No new framework installation needed — pytest already exists

*Existing infrastructure covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DISC-01: HTTP call count measurement | DISC-01 | Requires monkey-patch of `requests.Session.get` or `Request._make_call` — not unit-testable without live server | Run `uat_cms_smoke.py` with added HTTP counter instrumentation; record call counts per endpoint |
| DISC-02: Summary doc findings | DISC-02 | Document writing, not code | Write findings (slow endpoints found, actual call counts) to Phase 33 summary |
| REG-01: bgp_summary < 5s on live server | REG-01 | Requires live Nautobot server (HQV-PE1-NEW) | Run `uat_cms_smoke.py` after fix — bgp_summary must complete in < 5000ms |
| REG-03: Script committed and pushed | REG-03 | Git commit verification | `git log --oneline -1 scripts/uat_cms_smoke.py` must show post-phase commit |

*All unit test behaviors have automated verification (PAG-01..PAG-06, REG-02).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s (unit), < 60s (UAT)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** {pending / approved YYYY-MM-DD}
