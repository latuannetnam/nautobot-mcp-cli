---
phase: 20
status: passed
completed: 2026-03-25
verifier: inline
---

# Phase 20: Catalog Accuracy & Endpoint Dereference — Verification

## Phase Goal

Fix false filter advertisement in the CMS catalog (all 33 endpoints falsely report `["device"]` as their filter) by replacing domain-level `CMS_DOMAIN_FILTERS` with a per-endpoint filter registry. Enable linked object URL follow in the REST bridge by stripping UUID path segments before validation.

## Requirements Coverage

| Req ID | Description | Status |
|--------|-------------|--------|
| CAT-07 | Per-endpoint CMS filter accuracy | ✅ Implemented |
| CAT-08 | Filter registry covers all CMS endpoints | ✅ Implemented |
| CAT-09 | Child endpoints don't report device filter | ✅ Implemented |
| DRF-01 | UUID segments stripped before catalog validation | ✅ Implemented |
| DRF-02 | UUID used as id parameter | ✅ Implemented |
| DRF-03 | Explicit id overrides URL-embedded UUID | ✅ Implemented |

## Must-Haves Verification

### Plan 20-01: Per-Endpoint Filter Registry

- [x] `CMS_ENDPOINT_FILTERS` dict keyed by endpoint name with correct primary FK filters (43 entries)
- [x] `CMS_DOMAIN_FILTERS` removed entirely (grep returns 0 matches)
- [x] `discover_cms_endpoints()` reads from `CMS_ENDPOINT_FILTERS` instead of `CMS_DOMAIN_FILTERS`
- [x] Every key in `CMS_ENDPOINTS` has a corresponding entry in `CMS_ENDPOINT_FILTERS`
- [x] `CMS_ENDPOINT_FILTERS["juniper_bgp_neighbors"]` = `["group"]` (not `["device"]`)
- [x] `CMS_ENDPOINT_FILTERS["juniper_firewall_terms"]` = `["firewall_filter"]`
- [x] Tests added: `TestCMSFilterAccuracy` with 6 test methods

### Plan 20-02: UUID Path Normalization & Dereference

- [x] UUID segments stripped from endpoint path before catalog validation
- [x] Extracted UUID automatically used as `id` parameter for GET operations
- [x] Agent-provided `id` parameter takes precedence over URL-embedded UUID
- [x] Nested paths (>1 UUID) rejected with clear error message
- [x] CMS endpoints (no `/api/` prefix) unaffected
- [x] Response preserves original endpoint (with UUID) for transparency
- [x] Tests added: `TestUUIDPathNormalization` (6 tests) + `TestCallNautobotWithUUID` (3 tests)

## Test Results

```
pytest tests/test_catalog.py  → 29 passed (in 0.09s)
pytest tests/test_bridge.py   → 64 passed (in 0.17s)
pytest tests/                 → 430 passed, 11 deselected (in 1.81s)
```

**Zero regressions across all 21 test files.**

## Commits

- `8061a6c` — feat(phase-20): per-endpoint CMS filter registry (CAT-07, CAT-08, CAT-09)
- `e52bcc0` — feat(phase-20): UUID path normalization and dereference (DRF-01, DRF-02, DRF-03)

## Verdict: PASSED ✅

All must-haves implemented. All tests pass. No regressions.
