# Phase 31: Bridge Param Guard — Summary

**Phase:** 31-bridge-param-guard
**Completed:** 2026-03-29
**Status:** Complete

## Overview

Added `_guard_filter_params()` to `bridge.py` to intercept oversized `__in` list values before they reach pynautobot's `.filter()`, preventing 414 Request-URI Too Large errors from external callers who pass large UUID lists through the MCP bridge.

## What Was Built

- `_guard_filter_params()` helper at module level in `bridge.py`:
  - Raises `NautobotValidationError` when any `__in` param has > 500 items
  - Converts `__in` lists ≤ 500 to DRF-native comma-separated strings (`?id__in=uuid1,uuid2`)
  - Non-`__in` list params (tag, status, location) pass through unchanged
- Wired into `_execute_core()` before `endpoint_accessor.filter()` call
- Wired into `_execute_cms()` after device resolution, before `endpoint_accessor.filter()` call
- 18 unit tests: `TestParamGuard` (13) + `TestParamGuardIntegration` (5)

## Commits

| # | Description |
|---|---|
| 837bf6c | feat(bridge): add _guard_filter_params() to guard __in lists against 414 errors |
| 56541da | feat(bridge): wire _guard_filter_params into _execute_core() before filter() call |
| c727f98 | feat(bridge): wire _guard_filter_params into _execute_cms() after device resolution |
| 00d5f4d | test(bridge): add TestParamGuard and TestParamGuardIntegration covering __in list guard logic |
| 2dd5e97 | fix(bridge): fix _guard_filter_params to return {} not None for empty dict input |
| a981498 | docs(phase-31): complete bridge-param-guard phase |
| 0cfa3e4 | docs(phase-31): evolve PROJECT.md — add Phase 31 validated requirements |

## Key Decisions

- **500-item threshold**: Matches pynautobot's natural 500-item limit behavior; raises before pynautobot crashes
- **`or {}` fallback**: `_guard_filter_params` returns `None` for `None`/`{}` input; `or {}` ensures `effective_params` stays a dict in `_execute_cms()`
- **Comma-separated over repeated params**: `?id__in=a,b,c` vs `?id__in=a&id__in=b&id__in=c` — ~3x shorter query string
- **Raise vs truncate**: Raising with clear error message guides callers to chunk their queries

## Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| BRIDGE-01 | `_execute_core()` raises `NautobotValidationError` for `__in` > 500 | ✅ |
| BRIDGE-02 | `_execute_cms()` raises `NautobotValidationError` for `__in` > 500 | ✅ |
| BRIDGE-03 | `__in` lists ≤ 500 converted to comma-separated strings | ✅ |
| BRIDGE-04 | Non-`__in` list params pass through unchanged | ✅ |
| BRIDGE-05 | Unit tests: 18 tests covering all guard logic paths | ✅ |
