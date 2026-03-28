---
name: nautobot-device-info
description: Use when querying devices, interfaces, IP addresses, prefixes, VLANs, locations, tenants, or circuits from Nautobot via nautobot-mcp-cli -- especially on Windows where Unicode characters crash the CLI with charmap encoding errors
---

# Nautobot Device Info

## Overview

Query device inventory, interfaces, IPAM, and organizational data from Nautobot using the `nautobot-mcp-cli` CLI. **Always prefer JSON output** to avoid Windows encoding crashes.

## The Encoding Problem

Two distinct Unicode characters crash the CLI on Windows:
2
| Character | Source | Effect |
|-----------|--------|--------|
| `→` (`\u2192`) | Nautobot API location paths (e.g. `"Asia → VietNam → North"`) | `charmap codec can't encode` → exit 1 |
| `↑` `↓` (`\u2191` `\u2193`) | Hard-coded in CLI summary output | `charmap codec can't encode` → exit 1 |

**Rule: For agentic/structured use, always use `--json`.** For human-readable terminal output, prefix with `PYTHONIOENCODING=utf-8`.

## The 3-Tool API Bridge (MCP)

For AI agents using the MCP server, prefer these three tools over raw REST calls:

```
nautobot_api_catalog(domain=None)     # Discover all endpoints + workflow IDs
nautobot_call_nautobot(endpoint, ...) # GET/POST/PATCH/DELETE any endpoint
nautobot_run_workflow(workflow_id, ...) # Composite workflows
```

The bridge handles pagination, device-name→UUID resolution for CMS endpoints, and response wrapping. See `CLAUDE.md` for full workflow table.

## CLI Output Modes

CLI commands have two output modes — table (human) and JSON (machine):

```bash
# Table (human) — crashes on Windows with Unicode in location paths
nautobot-mcp devices list

# JSON (machine / agent) — always safe, always structured
nautobot-mcp --json devices list
```

**Global `--json` flag comes BEFORE the subcommand**, not after:
- Wrong: `devices list --json`
- Correct: `nautobot-mcp --json devices list`

## Pagination

Server-side `--limit` and `--offset` work the same across all list commands.

```bash
# Page 1 of 20
nautobot-mcp --json devices list --limit 20

# Page 2
nautobot-mcp --json devices list --limit 20 --offset 20

# --limit 0 means "no limit" — fetches all (auto-paginated by pynautobot)
nautobot-mcp --json devices list --limit 0
```

> **Note on `count`:** When using `--limit N > 0`, `count` reflects records in the current page. When `--limit 0` (no limit), pynautobot auto-paginates and `count` reflects all matching records.

The `default_limit` setting in your config (`.nautobot-mcp.yaml`) controls behavior when `--limit` is omitted.

## Core Commands

### Devices

```bash
# === LIST with filters ===
nautobot-mcp --json devices list
nautobot-mcp --json devices list --location "HCMV" --role "Router" --limit 20
nautobot-mcp --json devices list --tenant "TelecomCo" --platform "juniper_junos"
nautobot-mcp --json devices list --q "search-term"   # full-text search

# === CRUD ===
nautobot-mcp --json devices get --name "Router"
nautobot-mcp --json devices create --name "NEW-PE1" --type "Juniper MX204" --location "HCMV" --role "Router"
nautobot-mcp --json devices update --id "<uuid>" --status "Decommissioned"
nautobot-mcp --json devices delete --id "<uuid>"

# === Device summary (stats only — fast, ~4 API calls) ===
nautobot-mcp --json devices summary "Router"
# Returns: device metadata + interface_count, ip_count, vlan_count, enabled_count, disabled_count

# === Full paginated device inventory ===
nautobot-mcp --json devices inventory "Router" --detail interfaces --limit 50
nautobot-mcp --json devices inventory "Router" --detail ips       --limit 50
nautobot-mcp --json devices inventory "Router" --detail vlans      --limit 50
nautobot-mcp --json devices inventory "Router" --detail all        --limit 50 --offset 0
# Returns: device + paginated section + total_*/has_more metadata
```

> **`devices summary --detail` was removed in v1.5.** Use `devices inventory --detail interfaces|ips|vlans|all` instead for paginated full detail.

### Interfaces

```bash
# List interfaces on a device
nautobot-mcp --json interfaces list --device "Router" --limit 20

# Filter by device UUID
nautobot-mcp --json interfaces list --device-id "<uuid>" --limit 20

# Get a single interface
nautobot-mcp --json interfaces get --device "Router" --name "ae31.1256"

# CRUD
nautobot-mcp --json interfaces create --device "Router" --name "xe-0/0/0" --type "1000base-t"
nautobot-mcp --json interfaces update --id "<uuid>" --description "Uplink to core"
nautobot-mcp --json interfaces assign-ip --interface-id "<uuid>" --ip-address-id "<uuid>"
```

### IPAM

```bash
# === Prefixes ===
nautobot-mcp --json ipam prefixes list --limit 20
nautobot-mcp --json ipam prefixes list --location "HCMV" --tenant "TelecomCo"
nautobot-mcp --json ipam prefixes create --prefix "10.200.0.0/24" --namespace "Global"

# === IP Addresses ===
nautobot-mcp --json ipam addresses list --limit 20
nautobot-mcp --json ipam addresses list --device "Router" --limit 20
nautobot-mcp --json ipam addresses list --prefix "10.96.0.0/16"
nautobot-mcp --json ipam addresses create --address "10.200.0.1/24" --namespace "Global"

# === Bulk device IPs (M2M-based, no N+1) ===
nautobot-mcp --json ipam addresses device-ips "Router" --limit 50
# Returns: interface_ips[] (interface_name, address, status) + unlinked_ips[]

# === VLANs ===
nautobot-mcp --json ipam vlans list --limit 20
nautobot-mcp --json ipam vlans list --location "HCMV" --tenant "TelecomCo"
nautobot-mcp --json ipam vlans list --device "Router"  # via device interfaces
nautobot-mcp --json ipam vlans create --vid 100 --name "Management"
```

### Organization

```bash
nautobot-mcp --json org locations list
nautobot-mcp --json org tenants list
```

### Circuits

```bash
nautobot-mcp --json circuits list
nautobot-mcp --json circuits get --id "<uuid>"
```

### Golden Config

```bash
nautobot-mcp --json golden-config intended-config "Router"
nautobot-mcp --json golden-config backup-config "Router"
nautobot-mcp --json golden-config compliance "Router"
nautobot-mcp --json golden-config quick-diff "Router"
nautobot-mcp --json golden-config list-features
nautobot-mcp --json golden-config list-rules
nautobot-mcp --json golden-config create-feature "bgp-config" "bgp-config" --description "BGP configuration compliance"
```

### Verification & Drift

```bash
# Config compliance check (Golden Config quick-diff)
nautobot-mcp --json verify compliance "Router"

# File-based data model comparison (DiffSync)
nautobot-mcp --json verify data-model config.json "Router"

# Quick drift check (no config file needed)
nautobot-mcp --json verify quick-drift "Router" -i ae0.0 --ip 10.1.1.1/30
nautobot-mcp --json verify quick-drift "Router" -d '{"ae0.0": {"ips": ["10.1.1.1/30"]}}'
nautobot-mcp --json verify quick-drift "Router" -f drift-input.json
cat drift.json | nautobot-mcp --json verify quick-drift "Router"
```

### Config Onboarding

```bash
# Dry-run (default — shows planned changes, no Nautobot writes)
nautobot-mcp --json onboard config config.json "Router"

# Actually commit to Nautobot
nautobot-mcp --json onboard config config.json "Router" --commit

# With options
nautobot-mcp --json onboard config config.json "Router" --commit \
  --location "HCMV" --device-type "Juniper MX204" --role "Router" --namespace "Global"
```

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| `0` | Success | Parse output |
| `1` | General error | Check error message |
| `2` | Connection or auth error | Check URL, token, network |
| `3` | Not found | Verify device name or UUID |
| `4` | Validation error | Check parameters |

> On Windows, exit code `1` often means a Unicode encoding crash, not an API failure — retry with `--json`.

## JSON Output Structure

**`--json devices list`**:
```json
{
  "count": 20,
  "results": [
    {
      "id": "uuid",
      "name": "Router",
      "status": "Active",
      "device_type": { "name": "Juniper MX204" },
      "location": { "name": "HITC", "display": "Asia → VietNam → ..." },
      "role": { "name": "PE" },
      "platform": "juniper_junos_mx204",
      "serial": "GK475",
      "primary_ip": null
    }
  ]
}
```

**`--json devices summary`**:
```json
{
  "device": { "name": "Router", ... },
  "interface_count": 202,
  "ip_count": 214,
  "vlan_count": 0,
  "enabled_count": 200,
  "disabled_count": 2
}
```

**`--json devices inventory --detail all`**:
```json
{
  "device": { "name": "Router", ... },
  "interfaces": [ { "name": "ae31.1256", "type": "LAG", "enabled": true, ... } ],
  "interface_ips": [ { "interface_name": "ae31.1256", "address": "101.96.69.20/29", "status": "Active" } ],
  "vlans": [],
  "total_interfaces": 202,
  "total_ips": 214,
  "total_vlans": 0,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

**`--json ipam addresses device-ips DEVICE`**:
```json
{
  "device_name": "Router",
  "total_ips": 214,
  "interface_ips": [ { "interface_name": "ae31.1256", "address": "101.96.69.20/29", "status": "Active" } ],
  "unlinked_ips": []
}
```

## Common Mistakes

- **`--json` after the subcommand** (wrong): `devices list --json`
  **Correct (global flag before subcommand):** `nautobot-mcp --json devices list`

- **`devices summary --detail`** — this flag was removed in v1.5
  **Fix:** Use `devices inventory DEVICE --detail interfaces|ips|vlans|all`

- **Plain table output on Windows**: Crashes with `charmap codec can't encode \u2192`
  **Fix:** Always use `--json` for structured data

- **Ignoring exit code**: Exit 1 on Windows often means encoding error, not API failure
  **Fix:** Check exit code; retry with `--json` if code is 1

## Configuration

```bash
nautobot-mcp --profile prod --json devices list
nautobot-mcp --url https://nautobot.example.com --token abc123 --json devices list
```

Config sources (highest wins): **CLI flags → env vars → YAML → defaults**

```yaml
# .nautobot-mcp.yaml
profiles:
  prod:
    url: "https://nautobot.netnam.vn"
    token: "..."
    verify_ssl: true
active_profile: prod
default_limit: 50   # applied when --limit is omitted
```
