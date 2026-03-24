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

## Step 0: Discover Available Workflows
Optional — shows available verification workflows:

```
nautobot_api_catalog(domain="workflows")
```

---

## Workflow A: Config Compliance Check

### Step 1: Run compliance check
Use `nautobot_run_workflow` to compare intended vs backup config via Golden Config:

```
nautobot_run_workflow(
    workflow_id="verify_compliance",
    params={"device_name": "<device-name>"}
)
```

Required params: `device_name` (str).

Example response envelope:
```json
{"workflow": "verify_compliance", "device": "rtr-01", "status": "ok", "data": {"config_compliance": {"overall_status": "non-compliant", "features": {"BGP": "compliant", "Interfaces": "non-compliant"}}}, "error": null, "timestamp": "..."}
```

### Step 2: Review results
The response `data.config_compliance` includes:
- `overall_status` — "compliant" or "non-compliant"
- `features` — per-feature compliance status

---

## Workflow B: Data Model Drift Detection

### Step 1: Get router config via jmcp
```
execute_junos_command(
    router_name="<router-name>",
    command="show configuration | display json"
)
```

### Step 2: Run data model verification
```
nautobot_run_workflow(
    workflow_id="verify_data_model",
    params={"device_name": "<device-name>"}
)
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
If stale records found, review and delete from Nautobot via `nautobot_call_nautobot`.

---

## File-Free Drift Check (Quick Drift)

For comparing interface data against Nautobot without config files:

### From jmcp output (most common)
1. Run `execute_junos_command(router_name="<device>", command="show interfaces terse | display json")`
2. Parse the output: extract interface names and IP addresses
3. Build the live_data dict:
   ```json
   {
     "ae0.0": {"ips": ["10.1.1.1/30"], "vlans": [100]},
     "ge-0/0/0.0": {"ips": ["192.168.1.1/24"]}
   }
   ```
4. Call:
   ```
   nautobot_run_workflow(
       workflow_id="compare_device",
       params={
           "device_name": "DEVICE",
           "live_data": {"ae0.0": {"ips": ["10.1.1.1/30"], "vlans": [100]}}
       }
   )
   ```

Required params: `device_name` (str), `live_data` (dict).

### From nautobot_call_nautobot (chain existing tools)
1. Call `nautobot_call_nautobot(method="GET", endpoint="/api/dcim/devices/", params={"name": "DEVICE_A"})` to get source IPs
2. Pass the IP data to `compare_device` workflow for a different device:
   ```
   nautobot_run_workflow(
       workflow_id="compare_device",
       params={"device_name": "DEVICE_B", "live_data": <ip_data>}
   )
   ```

### Reading the result
- `summary.total_drifts`: 0 means no drift detected
- `interface_drifts`: per-interface detail with missing_ips, extra_ips, missing_vlans, extra_vlans
- `warnings`: validation messages (e.g., IPs without prefix length)

---

## CLI Alternative
```bash
nautobot-mcp verify compliance core-rtr-01
nautobot-mcp verify data-model router-config.json core-rtr-01
nautobot-mcp verify data-model router-config.json core-rtr-01 --json
nautobot-mcp verify quick-drift core-rtr-01 -i ae0.0 --ip 10.1.1.1/30
```

---

## Key MCP Tools Reference

| Tool | Workflow ID | Purpose |
|------|-------------|---------|
| `nautobot_api_catalog` | — | Discover available workflows |
| `nautobot_run_workflow` | `verify_compliance` | Golden Config diff |
| `nautobot_run_workflow` | `verify_data_model` | Config vs Data Model comparison |
| `nautobot_run_workflow` | `compare_device` | Fast interface/IP drift check |
| `nautobot_call_nautobot` | — | Direct REST access for device/IP data |
| `execute_junos_command` (jmcp) | — | Collect live device data |
