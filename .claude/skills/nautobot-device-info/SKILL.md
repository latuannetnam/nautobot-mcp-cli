---
name: nautobot-device-info
description: Use when querying devices, interfaces, IP addresses, prefixes, locations, or tenants from Nautobot via nautobot-mcp-cli -- especially on Windows where Unicode characters crash the CLI with charmap encoding errors
---

# Nautobot Device Info

## Overview

Query device inventory, interfaces, and IPAM data from Nautobot using the `nautobot-mcp-cli` CLI. **Always prefer JSON output** to avoid Windows encoding crashes.

## The Encoding Problem

Two distinct Unicode characters crash the CLI on Windows:

| Character | Source | Effect |
|-----------|--------|--------|
| `→` (`\u2192`) | Nautobot API location paths (e.g. `"Asia → VietNam → North"`) | `charmap codec can't encode` → exit 1 |
| `↑` `↓` (`\u2191` `\u2193`) | Hard-coded in `cli/devices.py` lines 137, 144 | `charmap codec can't encode` → exit 1 |

**Rule: For agentic/structured use, always use `--json`.** For human-readable terminal output, prefix with `PYTHONIOENCODING=utf-8`.

## Pagination

All list commands support server-side `--limit` and `--offset` — Nautobot returns only the requested page, not all records.

```bash
# --limit N: server-side max results (default from config, typically 50)
# --offset N: skip N results for pagination

# Page 1 of 20
nautobot-mcp --json devices list --limit 20

# Page 2
nautobot-mcp --json devices list --limit 20 --offset 20

# Page 3
nautobot-mcp --json devices list --limit 20 --offset 40

# --limit 0 means "no limit" — fetches all (auto-paginated by pynautobot)
nautobot-mcp --json devices list --limit 0
```

**`count` field in JSON output** reflects the number of records in the current page, not the total matching records. Use `--offset` to paginate through results.

## Core Commands

```bash
# === DEVICES ===
# List all devices (paginated — default 50)
nautobot-mcp --json devices list

# Paginate through all devices
nautobot-mcp --json devices list --limit 20 --offset 0
nautobot-mcp --json devices list --limit 20 --offset 20

# Filter + paginate
nautobot-mcp --json devices list --location "HQV" --role "Router" --limit 10

# Get a single device
nautobot-mcp --json devices get --name "HNI-HITC-PE1"

# Device summary (interface + IP counts)
nautobot-mcp --json devices summary "HNI-HITC-PE1"

# Full detail: interfaces, IPs, VLANs
nautobot-mcp --json devices summary "HNI-HITC-PE1" --detail

# === INTERFACES ===
# All interfaces on a device (paginated)
nautobot-mcp --json interfaces list --device "HNI-HITC-PE1" --limit 20

# Single interface
nautobot-mcp --json interfaces get --device-name "HNI-HITC-PE1" --name "ae31.1256"

# === IPAM ===
# IPs assigned to a device — server-side limited (e.g. first 20 IPs)
nautobot-mcp --json ipam addresses list --device "HNI-HITC-PE1" --limit 20

# Page 2 of IPs
nautobot-mcp --json ipam addresses list --device "HNI-HITC-PE1" --limit 20 --offset 20

# All IP prefixes (paginated)
nautobot-mcp --json ipam prefixes list --limit 10
nautobot-mcp --json ipam prefixes list --limit 10 --offset 10

# VLANs at a location (paginated)
nautobot-mcp --json ipam vlans list --location "HQV" --limit 10

# === ORGANIZATION ===
# All locations
nautobot-mcp --json org locations list

# All tenants
nautobot-mcp --json org tenants list
```

## Human-Readable Output

When a user explicitly wants a formatted table on Windows:

```bash
PYTHONIOENCODING=utf-8 nautobot-mcp devices summary "HNI-HITC-PE1" --detail
```

Note: `interfaces list` does not use Unicode arrows and renders fine without the prefix.

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| `0` | Success | Parse output |
| `1` | Encoding crash | Retry with `--json` (or set `PYTHONIOENCODING=utf-8`) |
| `2` | Connection or auth error | Check URL, token, network |
| `3` | Not found | Verify device name |
| `4` | Validation error | Check parameters |

## JSON Output Structure

**`--json devices list`**:
```json
{
  "count": 20,
  "results": [
    {
      "id": "uuid",
      "name": "HNI-HITC-PE1",
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

> **Note:** `count` = number of records in this page. Use `--offset` to paginate.

**`--json devices summary`**:
```json
{
  "device": { "name": "HNI-HITC-PE1", ... },
  "interfaces": [ { "id": "uuid", "name": "ae31.1256", "type": "LAG", "enabled": true, "mac_address": "48:5A:0D:...", "mtu": 9192, "ip_addresses": [] } ],
  "interface_ips": [ { "interface_name": "ae31.1256", "address": "101.96.69.20/29" } ],
  "vlans": [],
  "interface_count": 202,
  "ip_count": 214,
  "vlan_count": 0,
  "enabled_count": 200,
  "disabled_count": 2
}
```

**`--json ipam addresses list --device X --limit 20`**:
```json
{
  "count": 20,
  "results": [
    { "id": "uuid", "address": "192.168.69.186/30", "status": "Active", ... },
    ...
  ]
}
```

## Common Mistakes

- **`--json` after the subcommand** (wrong): `devices list --json`
  **Correct (global flag before subcommand):** `nautobot-mcp --json devices list`

- **Plain table output on Windows**: Crashes with `charmap codec can't encode \u2192`
  **Fix:** Always use `--json` for structured data

- **Assuming plain text is parseable**: Location `display` fields contain `→` which breaks tabulate
  **Fix:** Use `--json` and parse the structured response

- **Ignoring exit code**: Exit 1 often means encoding error, not API failure
  **Fix:** Check exit code first; retry with `--json` if code is 1

- **Expecting `count` to be the total**: With server-side pagination, `count` reflects records in the current page only
  **Fix:** Use `--limit` and `--offset` to page through results; `--limit 0` to fetch all

## Configuration

The CLI auto-discovers config from:
1. `NAUTOBOT_URL` + `NAUTOBOT_TOKEN` environment variables
2. `~/.config/nautobot-mcp/config.yaml`
3. `.nautobot-mcp.yaml` in current directory

Override at runtime:
```bash
nautobot-mcp --profile prod --json devices list
nautobot-mcp --url https://nautobot.example.com --token abc123 --json devices list
```

### `default_limit` in `.nautobot-mcp.yaml`

The `default_limit` setting controls how many results are fetched when `--limit` is not specified. Set it in your config:

```yaml
profiles:
  prod:
    url: "https://nautobot.example.com"
    token: "..."
    verify_ssl: true
active_profile: prod
default_limit: 50   # applied to --limit when not specified
```
