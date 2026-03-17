---
name: onboard-router-config
description: Onboard a JunOS router config into Nautobot — parse, match, create/update device + interfaces + IPs + VLANs
---

# Onboard Router Config

## When to Use
Use this skill when you need to take a JunOS router configuration and push its device, interfaces, IP addresses, and VLANs into Nautobot.

## Prerequisites
- JunOS config as JSON (`show configuration | display json`)
- Nautobot API access via environment variables or config file
- Device name to use in Nautobot

## Workflow

### Step 1: Get router config via jmcp
```
Use execute_junos_command to run:
  command: "show configuration | display json"
  router_name: <router-name>
```

### Step 2: Dry-run onboarding (preview changes)
```
Use nautobot_onboard_config:
  config_json: <json from step 1>
  device_name: <device-name>
  dry_run: true
```

Review the OnboardResult:
- `summary` shows counts (create/update/skip)
- `actions` lists every planned change
- `warnings` shows potential issues

### Step 3: Commit if satisfied
```
Use nautobot_onboard_config:
  config_json: <json from step 1>
  device_name: <device-name>
  dry_run: false
  location: <location-name>
```

### Step 4: Verify with data model check
```
Use nautobot_verify_data_model:
  config_json: <json from step 1>
  device_name: <device-name>
```

Expected: `total_drifts: 0` confirms all objects created correctly.

## CLI Alternative
```bash
nautobot-mcp onboard config router-config.json core-rtr-01
nautobot-mcp onboard config router-config.json core-rtr-01 --commit
```

## Key Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `dry_run` | `true` | Preview without committing |
| `update_existing` | `false` | Update existing objects |
| `location` | auto | Device location name |
| `role` | `Router` | Device role |
| `namespace` | `Global` | IPAM namespace |
