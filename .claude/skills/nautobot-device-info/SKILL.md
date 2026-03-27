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

## Core Commands

```bash
# === DEVICES ===
# List all devices
uv run nautobot-mcp --json devices list

# Filter by location and/or role
uv run nautobot-mcp --json devices list --location "HQV" --role "Router"

# Get a single device
uv run nautobot-mcp --json devices get --name "HNI-HITC-PE1"

# Device summary (interface + IP counts)
uv run nautobot-mcp --json devices summary "HNI-HITC-PE1"

# Full detail: interfaces, IPs, VLANs
uv run nautobot-mcp --json devices summary "HNI-HITC-PE1" --detail

# === INTERFACES ===
# All interfaces on a device
uv run nautobot-mcp --json interfaces list --device "HNI-HITC-PE1"

# Single interface
uv run nautobot-mcp --json interfaces get --device-name "HNI-HITC-PE1" --name "ae31.1256"

# === IPAM ===
# IPs assigned to a device
uv run nautobot-mcp --json ipam ips list --device "HNI-HITC-PE1"

# All IP prefixes
uv run nautobot-mcp --json ipam prefixes list

# VLANs at a location
uv run nautobot-mcp --json ipam vlans list --location "HQV"

# === ORGANIZATION ===
# All locations
uv run nautobot-mcp --json org locations list

# All tenants
uv run nautobot-mcp --json org tenants list
```

## Human-Readable Output

When a user explicitly wants a formatted table on Windows:

```bash
PYTHONIOENCODING=utf-8 uv run nautobot-mcp devices summary "HNI-HITC-PE1" --detail
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
  "count": 31,
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

## Common Mistakes

- **`--json` after the subcommand** (wrong): `devices list --json`
  **Correct (global flag before subcommand):** `nautobot-mcp --json devices list`

- **Plain table output on Windows**: Crashes with `charmap codec can't encode \u2192`
  **Fix:** Always use `--json` for structured data

- **Assuming plain text is parseable**: Location `display` fields contain `→` which breaks tabulate
  **Fix:** Use `--json` and parse the structured response

- **Ignoring exit code**: Exit 1 often means encoding error, not API failure
  **Fix:** Check exit code first; retry with `--json` if code is 1

## Configuration

The CLI auto-discovers config from:
1. `NAUTOBOT_URL` + `NAUTOBOT_TOKEN` environment variables
2. `~/.config/nautobot-mcp/config.yaml`
3. `.nautobot-mcp.yaml` in current directory

Override at runtime:
```bash
uv run nautobot-mcp --profile prod --json devices list
uv run nautobot-mcp --url https://nautobot.example.com --token abc123 --json devices list
```
