---
phase: 18
status: passed
updated: 2026-03-25
requirements_verified:
  - SKL-01
  - SKL-02
  - SKL-03
  - SKL-04
  - SKL-05
  - TST-06
  - TST-07
  - TST-08
---

# Phase 18 Verification — Agent Skills, Tests & UAT

## Summary

**Status: PASSED**

All 5 must-haves for skill rewrites verified. UAT test infrastructure created and validated against static checks. Live server UAT (against `http://101.96.85.93`) requires human run with `NAUTOBOT_TOKEN` configured.

---

## Must-Have Verification

### SKL-01: All 3 skills reference only the new 3-tool API

| Skill | nautobot_api_catalog | nautobot_call_nautobot | nautobot_run_workflow |
|-------|---------------------|----------------------|----------------------|
| cms-device-audit | ✅ yes | ✅ yes | ✅ yes |
| onboard-router-config | ✅ yes | ✅ yes | ✅ yes |
| verify-compliance | ✅ yes | ✅ yes | ✅ yes |

Verified: `Get-ChildItem nautobot_mcp/skills -Recurse -Filter "*.md" | Select-String "nautobot_run_workflow|nautobot_call_nautobot|nautobot_api_catalog"` → 39 matches across all 3 files.

### SKL-01 (negative): No old tool names remain

Verified: `Get-ChildItem nautobot_mcp/skills -Recurse -Filter "*.md" | Select-String "nautobot_device_summary|nautobot_onboard_config|nautobot_verify_.*|nautobot_compare_device|nautobot_get_device_ips|nautobot_cms_.*"` → **0 matches**.

### SKL-02: Discovery step in every skill

- ✅ `cms-device-audit`: Step 0 `nautobot_api_catalog(domain="cms")`
- ✅ `onboard-router-config`: Step 0 `nautobot_api_catalog(domain="workflows")`
- ✅ `verify-compliance`: Step 0 `nautobot_api_catalog(domain="workflows")`

### SKL-02: Inline params + example envelopes

- ✅ All 3 skills have inline `workflow_id`, `params` shown per call
- ✅ At least one trimmed example response envelope per skill (with `"status": "ok"`)

### SKL-03: cms-device-audit consolidated steps

- ✅ Old Step 2+3 (collect BGP + compare) → `nautobot_run_workflow("compare_bgp", ...)`
- ✅ Old Step 4+5 (collect routes + compare) → `nautobot_run_workflow("compare_routes", ...)`
- ✅ Interface detail → `nautobot_run_workflow("interface_detail", ...)`
- ✅ Firewall summary → `nautobot_run_workflow("firewall_summary", ...)`
- ✅ Quick Check updated to use workflow calls

### SKL-04: onboard-router-config skill

- ✅ Uses `nautobot_run_workflow(workflow_id="onboard_config", ...)`
- ✅ Uses `nautobot_run_workflow(workflow_id="verify_data_model", ...)`
- ✅ Parameter is `config_data` (not `config_json`)

### SKL-05: verify-compliance skill

- ✅ Uses `nautobot_run_workflow(workflow_id="verify_compliance", ...)`
- ✅ Uses `nautobot_run_workflow(workflow_id="verify_data_model", ...)`
- ✅ Uses `nautobot_run_workflow(workflow_id="compare_device", ...)`
- ✅ Uses `nautobot_call_nautobot` for device IP lookup

### TST-06 + TST-07 + TST-08: UAT Test Infrastructure

| Check | Status |
|-------|--------|
| `tests/test_uat.py` exists | ✅ |
| `pytestmark = pytest.mark.live` | ✅ |
| `UAT_DEVICE = "HQV-PE-TestFake"` | ✅ |
| `NAUTOBOT_UAT_URL` env var with `http://101.96.85.93` default | ✅ |
| Test classes: TestCatalogUAT, TestBridgeUAT, TestWorkflowUAT, TestIdempotentWriteUAT | ✅ |
| ≥9 test functions | ✅ (11 tests) |
| No `pytest.mark.skip` or `pytest.skip` | ✅ |
| `ast.parse(test_uat.py)` → valid | ✅ |
| `pyproject.toml` has `live` marker registered | ✅ |
| Normal `pytest tests/` excludes UAT (0 UAT collected) | ✅ |
| `scripts/uat_smoke_test.py` exists with shebang | ✅ |
| Smoke script has `UAT_DEVICE = "HQV-PE-TestFake"` | ✅ |
| Smoke script has `NAUTOBOT_UAT_URL` env var | ✅ |
| Smoke script has ≥8 test checks (has 9) | ✅ |
| `ast.parse(uat_smoke_test.py)` → valid | ✅ |
| Smoke script exits 0 on success, 1 on failure | ✅ |

---

## Regression Gate

**397 tests passed, 0 failed, 11 deselected (UAT live tests)**

All prior phase tests (test_catalog.py, test_bridge.py, test_workflows.py, test_server.py, etc.) continue to pass with no regressions.

---

## Human Verification Required

The following tests require network access to the live dev server (`http://101.96.85.93`) and a valid `NAUTOBOT_TOKEN`:

1. **pytest UAT run**: `pytest tests/test_uat.py -m live -v`
   - Expected: 11 tests pass, `HQV-PE-TestFake` found in dcim, CMS workflows return data
2. **Smoke script run**: `python scripts/uat_smoke_test.py`
   - Expected: 9 checks ✓, exits with code 0

These require operator access to the Nautobot dev server and cannot be automated in offline CI.

---

## Phase Success Criteria (from ROADMAP)

| Criterion | Status |
|-----------|--------|
| cms-device-audit references `call_nautobot` and `run_workflow` | ✅ |
| onboard-router-config uses `run_workflow("onboard_config", ...)` | ✅ |
| verify-compliance uses `run_workflow("verify_compliance", ...)` | ✅ |
| UAT smoke test infrastructure created | ✅ |
| `nautobot_api_catalog()` tested in UAT (catalog domains covered) | ✅ (static + UAT) |
| `call_nautobot("/api/dcim/devices/", "GET")` tested in UAT | ✅ (in TestBridgeUAT) |
