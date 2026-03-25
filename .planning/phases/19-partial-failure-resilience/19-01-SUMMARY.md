---
plan: 19-01
phase: 19
title: Core Partial Failure Infrastructure
status: complete
wave: 1
timestamp: 2026-03-25T14:40:00+07:00
---

# Summary: Plan 19-01 — Core Partial Failure Infrastructure

## What Was Built

- **`nautobot_mcp/warnings.py`** — New `WarningCollector` dataclass with `add(operation, error)`, `warnings` property, `has_warnings` property, and `summary(total_ops)` method
- **`nautobot_mcp/workflows.py`** — Updated `_build_envelope()` to support three-tier status (`ok`/`partial`/`error`) with `warnings` parameter; updated `run_workflow()` to unpack `(result, warnings)` tuples from composite functions
- **`tests/test_workflows.py`** — 11 new tests across 3 new test classes

## Key Files

key-files:
  created:
    - nautobot_mcp/warnings.py
  modified:
    - nautobot_mcp/workflows.py
    - tests/test_workflows.py

## Test Results

- `pytest tests/test_workflows.py` → **37 passed** (0 failures, 0 regressions)
- New tests: `TestWarningCollector` (5), `TestBuildEnvelopePartial` (3), `TestRunWorkflowPartial` (3)

## Self-Check: PASSED

All acceptance criteria met:
- [x] `WarningCollector` class exists with all required methods
- [x] `_build_envelope` supports `warnings` param and three-tier status
- [x] `warnings` key always present in envelope (even as `[]`)
- [x] `run_workflow` unpacks `(result, warnings)` tuples
- [x] Backward compatible: bare results still return `status: ok`
- [x] All 37 tests pass
