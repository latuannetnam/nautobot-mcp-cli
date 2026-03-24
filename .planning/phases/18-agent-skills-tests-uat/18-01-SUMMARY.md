---
plan: 18-01
phase: 18
status: complete
key-files:
  created: []
  modified:
    - nautobot_mcp/skills/cms-device-audit/SKILL.md
    - nautobot_mcp/skills/onboard-router-config/SKILL.md
    - nautobot_mcp/skills/verify-compliance/SKILL.md
commits:
  - "feat(phase-18): rewrite cms-device-audit skill for 3-tool API Bridge"
  - "feat(phase-18): rewrite onboard-router-config skill for 3-tool API Bridge"
  - "feat(phase-18): rewrite verify-compliance skill for 3-tool API Bridge"
---

# Plan 18-01 Summary: Agent Skill File Rewrites

## What Was Built
Rewrote all 3 agent skill guides to reference the new 3-tool API Bridge (`nautobot_api_catalog`, `nautobot_call_nautobot`, `nautobot_run_workflow`), removing all references to the old 165-tool interface.

## Changes Made

### cms-device-audit/SKILL.md
- Added **Step 0**: `nautobot_api_catalog(domain="cms")` discovery step
- Replaced `nautobot_device_summary` → `nautobot_call_nautobot(GET /api/dcim/devices/)`
- Merged old Steps 2+3 (collect BGP + compare) → single `nautobot_run_workflow(workflow_id="compare_bgp", ...)`
- Merged old Steps 4+5 (collect routes + compare) → single `nautobot_run_workflow(workflow_id="compare_routes", ...)`
- Replaced `nautobot_cms_get_interface_detail` → `nautobot_run_workflow(workflow_id="interface_detail", ...)`
- Replaced `nautobot_cms_get_device_firewall_summary` → `nautobot_run_workflow(workflow_id="firewall_summary", ...)`
- Updated Quick Check section: replaced old tool calls with `nautobot_run_workflow` equivalents
- Added full Workflow IDs reference table

### onboard-router-config/SKILL.md
- Added **Step 0**: `nautobot_api_catalog(domain="workflows")` discovery step
- Replaced `nautobot_onboard_config` → `nautobot_run_workflow(workflow_id="onboard_config", ...)`
- Replaced `nautobot_verify_data_model` → `nautobot_run_workflow(workflow_id="verify_data_model", ...)`
- Updated parameter name: `config_json` → `config_data` (per API spec)
- Added example response envelopes
- Updated key parameters table

### verify-compliance/SKILL.md
- Added **Step 0**: `nautobot_api_catalog(domain="workflows")` discovery step
- Replaced `nautobot_verify_config_compliance` → `nautobot_run_workflow(workflow_id="verify_compliance", ...)`
- Replaced `nautobot_verify_data_model` → `nautobot_run_workflow(workflow_id="verify_data_model", ...)`
- Replaced `nautobot_compare_device` → `nautobot_run_workflow(workflow_id="compare_device", ...)`
- Replaced `nautobot_get_device_ips` → `nautobot_call_nautobot(GET /api/dcim/devices/, ...)`
- Added example response envelopes

## Verification
- ✅ No old tool names remain in any skill file
- ✅ `nautobot_run_workflow`, `nautobot_call_nautobot`, `nautobot_api_catalog` present in all 3 files
- ✅ Each skill has a discovery Step 0
- ✅ Each skill has at least one example response envelope
- ✅ jmcp `execute_junos_command` references unchanged
- ✅ CLI Alternative sections unchanged

## Issues Encountered
None.

## Self-Check: PASSED
