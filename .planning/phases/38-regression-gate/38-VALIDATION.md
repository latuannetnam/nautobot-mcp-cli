---
phase: 38
slug: regression-gate
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-31
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pytest.ini (root) |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest -q --tb=short` |
| **Estimated runtime** | ~30 seconds (unit tests) + ~5-15 minutes (smoke test on prod) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q` (unit tests, ~30s)
- **After smoke test task:** Record actual elapsed_ms per workflow from script output
- **Before `/gsd:verify-work`:** Full unit suite must be green
- **Max feedback latency:** ~30 seconds for unit tests

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 38-01-01 | 01 | 1 | RGP-01 | UAT smoke | `uv run python scripts/uat_cms_smoke.py HQV-PE1-NEW` | pending |
| 38-02-01 | 02 | 1 | RGP-02 | unit | `uv run pytest -q` | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements:
- `scripts/uat_cms_smoke.py` — production-ready smoke test
- `tests/test_cms_interfaces_n1.py` — Phase 35 N+1 tests (8 tests)
- `tests/test_cms_firewalls_n1.py` — Phase 36 N+1 tests (8 tests)
- `tests/test_cms_routing_n1.py` — Phase 37 N+1 tests (9 tests)
- All other unit test files — baseline regression coverage

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live smoke test against prod HW | RGP-01 | Requires access to HQV-PE1-NEW device and Nautobot prod server | Run `uv run python scripts/uat_cms_smoke.py HQV-PE1-NEW [--profile prod]` |

---

## Validation Sign-Off

- [ ] All tasks have automated verification
- [ ] Smoke test covers all 5 CMS workflows
- [ ] Unit suite covers all 558 tests
- [ ] Phase complete when both exit 0

**Approval:** pending
