---
name: onboard-router-config
description: Onboard a JunOS router config into Nautobot — parse, match, create/update device + interfaces + IPs + VLANs
---

# Onboard Router Config

## When to Use
Use this skill when you need to take a JunOS router configuration and push its device, interfaces, IP addresses, and VLANs into Nautobot.

## Prerequisites
- JunOS config as JSON (`show configuration | display json`)
- Nautobot API access configured
- Device name to use in Nautobot

## Workflow

### Step 0: Discover Available Workflows
Optional — shows available onboarding workflows:

```
nautobot_api_catalog(domain="workflows")
```

---

### Step 1: Get router config via jmcp
```
execute_junos_command(
    router_name="<router-name>",
    command="show configuration | display json"
)
```

---

### Step 2: Dry-run onboarding (preview changes)
Use `nautobot_run_workflow` with `dry_run: true` to preview changes:

```
nautobot_run_workflow(
    workflow_id="onboard_config",
    params={
        "config_data": <parsed config dict from step 1>,
        "device_name": "<device-name>",
        "dry_run": true
    }
)
```

Required params: `config_data` (dict, ParsedConfig schema), `device_name` (str).
Optional: `dry_run` (bool, default true).

Example response envelope:
```json
{"workflow": "onboard_config", "device": "core-rtr-01", "status": "ok", "data": {"actions": [], "summary": {"created": 5, "updated": 2, "skipped": 10}}, "error": null, "timestamp": "..."}
```

Review the result:
- `summary` shows counts (create/update/skip)
- `actions` lists every planned change
- `warnings` shows potential issues

---

### Step 3: Commit if satisfied
Same call as Step 2 but with `dry_run: false`:

```
nautobot_run_workflow(
    workflow_id="onboard_config",
    params={
        "config_data": <parsed config dict from step 1>,
        "device_name": "<device-name>",
        "dry_run": false
    }
)
```

---

### Step 4: Verify with data model check
Use `nautobot_run_workflow` to confirm all objects were created correctly:

```
nautobot_run_workflow(
    workflow_id="verify_data_model",
    params={"device_name": "<device-name>"}
)
```

Expected: `total_drifts: 0` confirms all objects created correctly.

---

## CLI Alternative
```bash
nautobot-mcp onboard config router-config.json core-rtr-01
nautobot-mcp onboard config router-config.json core-rtr-01 --commit
```

---

## Key MCP Tools Reference

| Tool | Workflow ID | Required Parameters |
|------|-------------|---------------------|
| `nautobot_api_catalog` | — | `domain` (optional) |
| `nautobot_run_workflow` | `onboard_config` | `config_data`, `device_name`, `dry_run` |
| `nautobot_run_workflow` | `verify_data_model` | `device_name` |
| `execute_junos_command` (jmcp) | — | `router_name`, `command` |

### Workflow Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `dry_run` | `true` | Preview without committing |
| `config_data` | required | Parsed JunOS config (dict) |
| `device_name` | required | Device name in Nautobot |
