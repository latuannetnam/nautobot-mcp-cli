---
name: verify-compliance
description: Verify router config compliance and detect drift between device state and Nautobot records
---

# Verify Compliance

## When to Use
Use this skill to:
1. Check if a device's running config matches the intended (golden) config
2. Detect data model drift between a parsed config and Nautobot records
3. Generate a structured drift report for remediation planning

## Workflow A: Config Compliance Check

### Step 1: Run compliance check
```
Use nautobot_verify_config_compliance:
  device: <device-name>
```

This compares intended vs backup config via Golden Config quick diff.

### Step 2: Review results
The DriftReport includes:
- `config_compliance.overall_status` — "compliant" or "non-compliant"
- `config_compliance.features` — per-feature compliance status

## Workflow B: Data Model Drift Detection

### Step 1: Get router config via jmcp
```
Use execute_junos_command:
  command: "show configuration | display json"
  router_name: <router-name>
```

### Step 2: Run data model verification
```
Use nautobot_verify_data_model:
  config_json: <json from step 1>
  device_name: <device-name>
```

### Step 3: Analyze drift report
The DriftReport contains sections for:
- **interfaces** — missing/extra/changed interfaces
- **ip_addresses** — missing/extra/changed IPs
- **vlans** — missing/extra/changed VLANs
- **summary** — `total_drifts` and per-type breakdown

Drift statuses:
| Status | Meaning |
|--------|---------|
| `missing_in_nautobot` | On device but not in Nautobot — needs onboarding |
| `missing_on_device` | In Nautobot but not on device — stale record |
| `changed` | Exists in both but different — needs update |

### Step 4: Remediate
If missing items found, use the `onboard-router-config` skill to add them.
If stale records found, review and delete from Nautobot.

## CLI Alternative
```bash
nautobot-mcp verify compliance core-rtr-01
nautobot-mcp verify data-model router-config.json core-rtr-01
nautobot-mcp verify data-model router-config.json core-rtr-01 --json
```
