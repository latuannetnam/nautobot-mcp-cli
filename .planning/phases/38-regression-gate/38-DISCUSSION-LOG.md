# Phase 38: Regression Gate - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 38-regression-gate
**Areas discussed:** Smoke thresholds, Smoke test scope, Unit test scope, CI gate integration

---

## Smoke Thresholds

| Option | Description | Selected |
|--------|-------------|----------|
| Tighten after N+1 fixes | Set tighter thresholds: bgp_summary ≤3s, others ≤10s | |
| Keep conservative (current) | Keep current THRESHOLD_MS as-is: bgp ≤5s, others ≤15s | ✓ |
| Percentile-based (p90) | Run first, measure, set p90 + 20% margin | |

**User's choice:** Keep conservative (current)
**Notes:** No changes to THRESHOLD_MS. Thresholds are conservative but sufficient to catch regressions.

---

## Smoke Test Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Single device (HQV-PE1-NEW) | Keep existing: run against HQV-PE1-NEW only | ✓ |
| All Nautobot devices | Query all devices and run against each | |
| Configurable device list | Accept --device flag or --device-file | |

**User's choice:** Single device HQV-PE1-NEW
**Notes:** Sticking with canonical device name HQV-PE1-NEW.

---

## Unit Test Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full suite | uv run pytest — all ~530 tests, no filtering | ✓ |
| CMS-focused subset | pytest tests/test_cms_*.py only | |
| N+1 invariant only | pytest tests/test_cms_*_n1.py only | |

**User's choice:** Full suite (Recommended)
**Notes:** No filtering — ensures no regressions anywhere in the codebase.

---

## CI Gate Integration

| Option | Description | Selected |
|--------|-------------|----------|
| CI gate | GitHub Actions job blocking PRs on prod smoke test | |
| Manual only | Keep smoke test as manual developer tool | ✓ |
| CI on dev profile | GitHub Actions job using --profile dev | |

**User's choice:** Manual only
**Notes:** No CI gate. Too risky to block PRs on prod hardware availability.

---

## Summary

All 4 gray areas resolved in a single discussion pass. Phase 38 is a verification gate — the work is primarily execution (running existing tests), not building new functionality. The decisions ensure:
1. Smoke test uses existing thresholds and device — no threshold tuning
2. Full unit test suite runs without filtering — maximum regression coverage
3. Smoke test stays manual — no CI gate on prod hardware
