---
phase: 37
slug: routing-table-bgp-n1-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `tests/conftest.py` (shared fixtures) |
| **Quick run command** | `uv run pytest tests/test_cms_routing_n1.py -v` |
| **Full suite command** | `uv run pytest tests/ -v --ignore=tests/test_uat.py` |
| **Estimated runtime** | ~15-30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_cms_routing_n1.py -v`
- **After every plan wave:** Run `uv run pytest tests/test_cms_interfaces_n1.py tests/test_cms_firewalls_n1.py tests/test_cms_routing_n1.py -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 37-01-01 | 01 | 1 | CQP-03 | unit | `uv run pytest tests/test_cms_routing_n1.py -v -k routing` | ✅ W0 | ⬜ pending |
| 37-02-01 | 02 | 1 | CQP-04 | unit | `uv run pytest tests/test_cms_routing_n1.py -v -k bgp` | ✅ W0 | ⬜ pending |
| 37-03-01 | 03 | 1 | CQP-03+CQP-05 | unit | `uv run pytest tests/test_cms_routing_n1.py -v` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cms_routing_n1.py` — N+1 invariant tests for routing_table (Plan 01) and bgp_summary (Plan 02), plus bulk lookup tests (Plan 03)
- [ ] `tests/conftest.py` — shared fixtures (existing, verify `cms_list` monkey-patch helper is present)
- [ ] `tests/test_cms_interfaces_n1.py` — verify Phase 35 tests still pass after routing changes (regression)
- [ ] `tests/test_cms_firewalls_n1.py` — verify Phase 36 tests still pass after routing changes (regression)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live workflow timing on HQV-PE1 | CQP-03, CQP-04 | Requires live Nautobot + CMS plugin on HQV-PE1 | `nautobot-mcp --json cms routing routing-table --device HQV-PE1-NEW` — measure total HTTP calls via logging |
| Smoke test: routing_table within 60s | RGP-01 (Phase 38) | Phase 38 regression gate | Run `scripts/uat_cms_smoke.py` after all Phase 37 changes |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
