# nautobot-mcp-cli

**MCP server and CLI for Nautobot network automation** — lets AI agents (and humans) interact with [Nautobot](https://nautobot.readthedocs.io/) via a **3-tool API Bridge**: discover endpoints, call any REST API, or run composite workflows. Covers inventory, config onboarding, drift detection, and full Juniper CMS model audits — no config files required.

---

## Features

### MCP Tools (v1.3 API Bridge — 3 tools)

| Tool | Purpose |
|---|---|
| `nautobot_api_catalog` ✨ | Discover all available endpoints and workflows, filtered by domain (`dcim`, `ipam`, `cms`, `workflows`, …) |
| `nautobot_call_nautobot` ✨ | Universal REST dispatcher — GET, POST, PATCH, DELETE against any `/api/*` or `cms:*` endpoint |
| `nautobot_run_workflow` ✨ | Run a composite server-side workflow by ID; returns `{workflow, device, status, data, error, timestamp}` |

### Available Workflows

| Workflow ID | Covers |
|---|---|
| `bgp_summary` | BGP groups + neighbor counts |
| `routing_table` | Static routes with next-hops |
| `firewall_summary` | Firewall filters + term counts |
| `interface_detail` | Interface units with families, VRRP, ARP |
| `onboard_config` | Parse + push config to Nautobot (dry-run safe) |
| `compare_device` | File-free drift: live interfaces vs Nautobot |
| `verify_data_model` | DiffSync model drift report |
| `verify_compliance` | Golden Config compliance check |
| `compare_bgp` | Live BGP neighbors vs CMS records |
| `compare_routes` | Live static routes vs CMS records |

### CLI Commands

| Capability | CLI Command |
|---|---|
| **Devices** — list, get, create, update, delete | `nautobot-mcp devices` |
| **Interfaces** — list, get, create, update | `nautobot-mcp interfaces` |
| **IPAM** — prefixes, IPs, VLANs | `nautobot-mcp ipam` |
| **Golden Config** — intended/backup/compliance | `nautobot-mcp golden-config` |
| **Config Parsing** — parse JunOS JSON | `nautobot-mcp parse` |
| **Onboarding** — device config to Nautobot | `nautobot-mcp onboard config` |
| **Verification** — compliance + drift | `nautobot-mcp verify` |
| **CMS** — routing, interfaces, firewalls, policies, drift | `nautobot-mcp cms` |

---

## Requirements

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Nautobot ≥ 2.x with a valid API token
- (Optional) Nautobot Golden Config plugin — required for Golden Config / compliance features

---

## Installation

### Using uv (recommended)

```bash
# Clone the repo
git clone https://github.com/your-org/nautobot-mcp-cli.git
cd nautobot-mcp-cli

# Create virtual environment and install
uv sync

# Install with dev dependencies
uv sync --extra dev
```

### Using pip

```bash
pip install -e .
# or with dev deps
pip install -e ".[dev]"
```

After installation the `nautobot-mcp` CLI entry point is available in your environment.

---

## Configuration

Configuration is loaded from multiple sources. **Higher-numbered sources override lower ones:**

1. Default values
2. YAML config file
3. Environment variables
4. CLI flags (`--url`, `--token`, `--profile`, `--no-verify`)

### Option 1 — YAML config file

The app automatically discovers config files in this order (first found wins):

| Priority | Path |
|---|---|
| 1 | `.nautobot-mcp.yaml` in the current working directory |
| 2 | `~/.config/nautobot-mcp/config.yaml` |

Create a YAML file at either location:

```yaml
profiles:
  default:
    url: "https://nautobot.example.com"
    token: "your-api-token-here"
    verify_ssl: true
    # api_version: "2.0"   # optional — auto-detected if omitted

  staging:
    url: "https://nautobot-staging.example.com"
    token: "staging-token-here"
    verify_ssl: false

active_profile: default    # which profile to use by default
default_limit: 50          # max results per query (0 = unlimited)
```

**Profile fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `url` | string | *required* | Nautobot server base URL |
| `token` | string | *required* | API authentication token |
| `verify_ssl` | bool | `true` | Verify SSL certificates |
| `api_version` | string | `null` | API version (auto-detected from server when omitted) |

You can also load a specific YAML file programmatically:

```python
from nautobot_mcp.config import NautobotSettings

settings = NautobotSettings.load_from_yaml("/path/to/config.yaml")
```

### Option 2 — Environment variables

Set environment variables to configure without a file, or to override file values:

```bash
export NAUTOBOT_URL="https://nautobot.example.com"
export NAUTOBOT_TOKEN="your-token-here"
export NAUTOBOT_VERIFY_SSL="true"         # true/1/yes to enable
export NAUTOBOT_PROFILE="staging"         # select a named profile
```

| Variable | Description |
|---|---|
| `NAUTOBOT_URL` | Nautobot base URL |
| `NAUTOBOT_TOKEN` | API token |
| `NAUTOBOT_VERIFY_SSL` | SSL verification (`true`/`false`/`1`/`0`/`yes`/`no`) |
| `NAUTOBOT_PROFILE` | Active profile name |

> **Note:** When both `NAUTOBOT_URL` and `NAUTOBOT_TOKEN` are set, they create or overwrite the active profile in memory — the YAML file is not modified.

### Option 3 — CLI flags

Override any setting per-invocation:

```bash
# Use a different profile
nautobot-mcp --profile staging devices list

# Provide URL and token directly (no config file needed)
nautobot-mcp --url https://nautobot.example.com --token abc123 devices list

# Skip SSL verification
nautobot-mcp --no-verify devices list
```

### Option 4 — Programmatic (Python API)

```python
from nautobot_mcp.client import NautobotClient
from nautobot_mcp.config import NautobotProfile, NautobotSettings

# Direct profile — no file or env vars needed
profile = NautobotProfile(
    url="https://nautobot.example.com",
    token="your-token",
    verify_ssl=True,
)
client = NautobotClient(profile=profile)

# Or auto-discover from file + env vars
settings = NautobotSettings.discover()
client = NautobotClient(settings=settings)
```

---

## MCP Server

The MCP server exposes all Nautobot operations as tools that AI agents (Claude, Cursor, etc.) can call directly.

### Starting the server

```bash
# Recommended — uses the project venv automatically
uv run python main.py

# Alternative — via fastmcp CLI
uv run fastmcp run nautobot_mcp/server.py
```

### Integrating with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nautobot": {
      "command": "uv",
      "args": ["run", "python", "main.py"],
      "cwd": "/path/to/nautobot-mcp-cli"
    }
  }
}
```

### Integrating with Antigravity / other MCP clients

```json
{
  "servers": {
    "nautobot": {
      "command": "uv",
      "args": ["--directory", "/path/to/nautobot-mcp-cli", "run", "python", "main.py"],
      "transport": "stdio"
    }
  }
}
```

### Available MCP tools (v1.3)

The server exposes **3 tools**. Use `nautobot_api_catalog` to discover all endpoints and workflow IDs before calling the other two.

<details>
<summary><strong>nautobot_api_catalog — Endpoint & Workflow Discovery</strong></summary>

| Parameter | Type | Description |
|---|---|---|
| `domain` | string (optional) | Filter by domain: `dcim`, `ipam`, `circuits`, `tenancy`, `cms`, `workflows` |

Returns a token-efficient catalog of all available endpoints grouped by domain. Includes workflow stub signatures.

```python
# Discover all workflows
nautobot_api_catalog(domain="workflows")

# Discover CMS endpoints
nautobot_api_catalog(domain="cms")
```

</details>

<details>
<summary><strong>nautobot_call_nautobot — Universal REST Dispatcher</strong></summary>

| Parameter | Type | Description |
|---|---|---|
| `endpoint` | string | `/api/dcim/devices/` or `cms:juniper_bgp_groups` |
| `method` | string | `GET`, `POST`, `PATCH`, `DELETE` |
| `params` | dict (optional) | Query filters for GET |
| `data` | dict (optional) | Request body for POST/PATCH |
| `id` | string (optional) | Object UUID for single-object operations |
| `limit` | int (optional) | Max results for GET list (default 50, hard cap 200) |

Routes to pynautobot core (`/api/*`) or CMS plugin (`cms:*`) automatically.

```python
# List devices
nautobot_call_nautobot(endpoint="/api/dcim/devices/", method="GET")

# Get specific device
nautobot_call_nautobot(endpoint="/api/dcim/devices/", method="GET", params={"name": "core-rtr-01"})

# Get CMS BGP groups for a device
nautobot_call_nautobot(endpoint="cms:juniper_bgp_groups", method="GET", params={"device": "core-rtr-01"})
```

Response: `{count, results, endpoint, method}` — with optional `truncated` + `total_available` when capped.

</details>

<details>
<summary><strong>nautobot_run_workflow — Composite Workflow Runner</strong></summary>

| Parameter | Type | Description |
|---|---|---|
| `workflow_id` | string | One of the 10 registered workflow IDs |
| `params` | dict | Workflow-specific parameters |

Always returns: `{workflow, device, status, data, error, timestamp}`

```python
# BGP summary
nautobot_run_workflow(workflow_id="bgp_summary", params={"device": "core-rtr-01"})

# Onboard config (dry-run)
nautobot_run_workflow(workflow_id="onboard_config", params={
    "config_data": {...},
    "device_name": "core-rtr-01",
    "dry_run": True
})

# CMS BGP drift
nautobot_run_workflow(workflow_id="compare_bgp", params={
    "device_name": "core-rtr-01",
    "live_neighbors": [{"peer_ip": "10.0.0.1", "peer_as": 65001, ...}]
})
```

</details>

<details>
<summary><strong>Devices</strong> (CLI-only, also accessible via nautobot_call_nautobot)</summary>

| Tool | Description |
|---|---|
| `nautobot_list_devices` | List devices with optional filters (location, tenant, role, platform, search) |
| `nautobot_get_device` | Get a single device by name or UUID |
| `nautobot_create_device` | Create a new device |
| `nautobot_update_device` | Update device name, status, or role |
| `nautobot_delete_device` | Delete a device by UUID |

</details>

<details>
<summary><strong>Interfaces</strong></summary>

| Tool | Description |
|---|---|
| `nautobot_list_interfaces` | List interfaces, optionally filtered by device |
| `nautobot_get_interface` | Get interface by ID or device_name + name |
| `nautobot_create_interface` | Create a new interface on a device |
| `nautobot_update_interface` | Update interface name, enabled state, or description |
| `nautobot_assign_ip_to_interface` | Assign an IP address to an interface (M2M) |

</details>

<details>
<summary><strong>IPAM</strong></summary>

| Tool | Description |
|---|---|
| `nautobot_list_prefixes` | List IP prefixes |
| `nautobot_create_prefix` | Create a prefix in CIDR notation |
| `nautobot_list_ip_addresses` | List IP addresses |
| `nautobot_create_ip_address` | Create an IP address |
| `nautobot_list_vlans` | List VLANs |
| `nautobot_create_vlan` | Create a VLAN |

</details>

<details>
<summary><strong>Organization</strong></summary>

| Tool | Description |
|---|---|
| `nautobot_list_tenants` | List tenants |
| `nautobot_get_tenant` | Get a single tenant |
| `nautobot_create_tenant` | Create a tenant |
| `nautobot_update_tenant` | Update a tenant |
| `nautobot_list_locations` | List locations |
| `nautobot_get_location` | Get a single location |
| `nautobot_create_location` | Create a location |
| `nautobot_update_location` | Update a location |

</details>

<details>
<summary><strong>Circuits</strong></summary>

| Tool | Description |
|---|---|
| `nautobot_list_circuits` | List circuits |
| `nautobot_get_circuit` | Get a circuit by CID or UUID |
| `nautobot_create_circuit` | Create a circuit |
| `nautobot_update_circuit` | Update a circuit |

</details>

<details>
<summary><strong>Golden Config &amp; Compliance</strong></summary>

| Tool | Description |
|---|---|
| `nautobot_get_intended_config` | Retrieve the intended (golden) config for a device |
| `nautobot_get_backup_config` | Retrieve the last collected backup config |
| `nautobot_list_compliance_features` | List compliance features |
| `nautobot_create_compliance_feature` | Create a compliance feature |
| `nautobot_delete_compliance_feature` | Delete a compliance feature |
| `nautobot_list_compliance_rules` | List compliance rules |
| `nautobot_create_compliance_rule` | Create a compliance rule |
| `nautobot_update_compliance_rule` | Update a compliance rule |
| `nautobot_delete_compliance_rule` | Delete a compliance rule |
| `nautobot_get_compliance_results` | Get compliance results for a device |
| `nautobot_quick_diff_config` | Quick intended vs. backup diff |

</details>

<details>
<summary><strong>Device Queries</strong></summary>

| Tool | Description |
|---|---|
| `nautobot_get_device_summary` | Interface count, IP count, VLAN count, link-state stats — one call |
| `nautobot_get_device_ips` | All IP addresses on all interfaces for a device (M2M traversal) |
| `nautobot_list_interfaces` | List interfaces; pass `include_ips=True` to embed IPs inline (batch query) |
| `nautobot_list_ip_addresses` | List IPs with optional `device` filter |
| `nautobot_list_vlans` | List VLANs with optional `device` filter |

</details>

<details>
<summary><strong>Onboarding, Verification & Drift</strong></summary>

| Tool | Description |
|---|---|
| `nautobot_parse_config` | Parse a JunOS JSON config into structured data |
| `nautobot_onboard_config` | Onboard parsed config to Nautobot (supports dry-run) |
| `nautobot_verify_compliance` | Check config compliance via Golden Config |
| `nautobot_verify_data_model` | Run DiffSync drift report (interfaces, IPs, VLANs) |
| `nautobot_compare_device` | **File-free drift** — compare structured interface data vs Nautobot, no config file needed |

</details>

<details>
<summary><strong>CMS Routing (v1.2 ✨)</strong></summary>

| Tool | Description |
|---|---|
| `nautobot_cms_list_static_routes` | List static routes for a device (inlines next-hops) |
| `nautobot_cms_get_static_route` | Get a single static route by ID |
| `nautobot_cms_create_static_route` | Create a static route with next-hops |
| `nautobot_cms_delete_static_route` | Delete a static route |
| `nautobot_cms_list_bgp_groups` | List BGP groups for a device |
| `nautobot_cms_get_bgp_group` | Get a single BGP group |
| `nautobot_cms_create_bgp_group` | Create a BGP group |
| `nautobot_cms_delete_bgp_group` | Delete a BGP group |
| `nautobot_cms_list_bgp_neighbors` | List BGP neighbors for a device or group |
| `nautobot_cms_get_bgp_neighbor` | Get a single BGP neighbor |
| `nautobot_cms_create_bgp_neighbor` | Create a BGP neighbor |
| `nautobot_cms_delete_bgp_neighbor` | Delete a BGP neighbor |
| `nautobot_cms_list_bgp_address_families` | List address families for a BGP neighbor |
| `nautobot_cms_list_bgp_policy_associations` | List policy associations for a group or neighbor |
| `nautobot_cms_list_bgp_received_routes` | List received routes for a BGP neighbor |
| `nautobot_cms_list_routing_instances` | List routing instances for a device |
| `nautobot_cms_list_static_route_nexthops` | List next-hops for a static route |

</details>

<details>
<summary><strong>CMS Interfaces (v1.2 ✨)</strong></summary>

| Tool | Description |
|---|---|
| `nautobot_cms_list_interface_units` | List interface units for a device |
| `nautobot_cms_get_interface_unit` | Get a single interface unit |
| `nautobot_cms_create_interface_unit` | Create an interface unit |
| `nautobot_cms_delete_interface_unit` | Delete an interface unit |
| `nautobot_cms_list_interface_families` | List address families for an interface unit |
| `nautobot_cms_get_interface_family` | Get a single interface family |
| `nautobot_cms_list_ff_associations` | List filter-family associations (input/output filters) |
| `nautobot_cms_create_ff_association` | Add a filter to an interface family |
| `nautobot_cms_delete_ff_association` | Remove a filter from an interface family |
| `nautobot_cms_list_fp_associations` | List policer-family associations |
| `nautobot_cms_create_fp_association` | Add a policer to an interface family |
| `nautobot_cms_delete_fp_association` | Remove a policer from an interface family |
| `nautobot_cms_list_vrrp_groups` | List VRRP groups for an interface unit |
| `nautobot_cms_get_vrrp_group` | Get a single VRRP group |
| `nautobot_cms_create_vrrp_group` | Create a VRRP group |
| `nautobot_cms_delete_vrrp_group` | Delete a VRRP group |
| `nautobot_cms_list_arp_entries` | List ARP entries for a device or interface |
| `nautobot_cms_get_arp_entry` | Get a single ARP entry |
| `nautobot_cms_create_arp_entry` | Create an ARP entry |
| `nautobot_cms_delete_arp_entry` | Delete an ARP entry |

</details>

<details>
<summary><strong>CMS Firewalls & Policies (v1.2 ✨)</strong></summary>

| Tool | Description |
|---|---|
| `nautobot_cms_list_firewall_filters` | List firewall filters for a device |
| `nautobot_cms_get_firewall_filter` | Get a single firewall filter |
| `nautobot_cms_create_firewall_filter` | Create a firewall filter |
| `nautobot_cms_delete_firewall_filter` | Delete a firewall filter |
| `nautobot_cms_list_firewall_terms` | List terms for a firewall filter |
| `nautobot_cms_create_firewall_term` | Create a term in a firewall filter |
| `nautobot_cms_delete_firewall_term` | Delete a firewall term |
| `nautobot_cms_list_firewall_policers` | List firewall policers for a device |
| `nautobot_cms_create_firewall_policer` | Create a firewall policer |
| `nautobot_cms_delete_firewall_policer` | Delete a firewall policer |
| `nautobot_cms_list_policy_statements` | List policy statements for a device |
| `nautobot_cms_create_policy_statement` | Create a policy statement |
| `nautobot_cms_delete_policy_statement` | Delete a policy statement |

</details>

<details>
<summary><strong>CMS Composite Summaries (v1.2 ✨)</strong></summary>

| Tool | Description |
|---|---|
| `nautobot_cms_get_device_bgp_summary` | All BGP groups + neighbors in one call; `detail=True` expands address families and policy associations |
| `nautobot_cms_get_device_routing_table` | All static routes with inlined next-hops and routing instances |
| `nautobot_cms_get_interface_detail` | Full interface unit view: families, filters, policers, VRRP groups, ARP entries |
| `nautobot_cms_get_device_firewall_summary` | All firewall filters with term counts and policer associations |

</details>

<details>
<summary><strong>CMS Drift Verification (v1.2 ✨)</strong></summary>

| Tool | Description |
|---|---|
| `nautobot_cms_compare_bgp_neighbors` | Compare live BGP neighbors (from jmcp) against Nautobot CMS records — returns `CMSDriftReport` with missing, extra, changed |
| `nautobot_cms_compare_static_routes` | Compare live static routes against Nautobot CMS records — nexthop comparison is order-independent |

</details>

---

## CLI Usage

```
uv run nautobot-mcp [OPTIONS] COMMAND [ARGS]...
```

> **Tip:** `uv run` automatically uses the project venv. Alternatively, activate it first (`source .venv/bin/activate` or `.venv\Scripts\activate`) and then use `nautobot-mcp` directly.

### Global options

| Option | Description |
|---|---|
| `--profile NAME` | Use a specific config profile |
| `--url URL` | Override Nautobot URL |
| `--token TOKEN` | Override API token |
| `--no-verify` | Skip SSL certificate verification |
| `--json` | Output as JSON instead of table |

### Commands

```bash
# Devices
uv run nautobot-mcp devices list
uv run nautobot-mcp devices list --location "HAN DC1" --role Router
uv run nautobot-mcp devices get --name core-rtr-01
uv run nautobot-mcp devices create --name new-rtr --device-type "MX480" --location "HAN DC1" --role Router

# Interfaces
uv run nautobot-mcp interfaces list --device core-rtr-01
uv run nautobot-mcp interfaces get --device-name core-rtr-01 --name ge-0/0/0

# IPAM
uv run nautobot-mcp ipam prefixes list
uv run nautobot-mcp ipam ips list
uv run nautobot-mcp ipam ips list --device core-rtr-01   # device-scoped
uv run nautobot-mcp ipam vlans list --location "HAN DC1"
uv run nautobot-mcp ipam vlans list --device core-rtr-01  # device-scoped

# Organization
uv run nautobot-mcp org tenants list
uv run nautobot-mcp org locations list

# Circuits
uv run nautobot-mcp circuits list --provider "VNPT"

# Golden Config
uv run nautobot-mcp golden-config show-intended core-rtr-01
uv run nautobot-mcp golden-config show-backup core-rtr-01
uv run nautobot-mcp golden-config compliance-results core-rtr-01

# Device summary
uv run nautobot-mcp devices summary core-rtr-01
uv run nautobot-mcp devices summary core-rtr-01 --detail  # includes interfaces + IPs

# Parse JunOS config
uv run nautobot-mcp parse junos config.json

# Onboard device config (dry-run by default)
uv run nautobot-mcp onboard config config.json core-rtr-01
uv run nautobot-mcp onboard config config.json core-rtr-01 --commit        # apply changes
uv run nautobot-mcp onboard config config.json core-rtr-01 --commit --update  # also update existing

# Verify compliance
uv run nautobot-mcp verify compliance core-rtr-01

# Verify data model drift (requires config file)
uv run nautobot-mcp verify data-model config.json core-rtr-01

# File-free drift check — no config file needed
uv run nautobot-mcp verify quick-drift core-rtr-01 --interface ae0.0 --ip 10.1.1.1/30
uv run nautobot-mcp verify quick-drift core-rtr-01 -d '{"ae0.0": {"ips": ["10.1.1.1/30"]}}'
uv run nautobot-mcp verify quick-drift core-rtr-01 -f drift-input.json --json

# CMS Routing (v1.2)
uv run nautobot-mcp cms routing list-static-routes --device core-rtr-01
uv run nautobot-mcp cms routing bgp-summary --device core-rtr-01
uv run nautobot-mcp cms routing routing-table --device core-rtr-01

# CMS Interfaces (v1.2)
uv run nautobot-mcp cms interfaces list-units --device core-rtr-01
uv run nautobot-mcp cms interfaces detail --device core-rtr-01
uv run nautobot-mcp cms interfaces list-arp-entries --device core-rtr-01

# CMS Firewalls (v1.2)
uv run nautobot-mcp cms firewalls list-filters --device core-rtr-01
uv run nautobot-mcp cms firewalls firewall-summary --device core-rtr-01

# CMS Drift (v1.2) — compare live device data against Nautobot CMS records
uv run nautobot-mcp cms drift bgp --device core-rtr-01 --from-file live-bgp.json
uv run nautobot-mcp cms drift routes --device core-rtr-01 --from-file live-routes.json
```

---

## Config Onboarding Workflow

The onboarding engine parses a JunOS device config and creates/updates the corresponding Nautobot objects.

### Supported parsers

| Parser ID | Platform |
|---|---|
| `juniper_junos` | Juniper JunOS (JSON output) |

### Steps

1. Export the device config as JSON from the router:

   ```bash
   # On JunOS device
   show configuration | display json | save /tmp/config.json
   # or fetch via jmcp MCP server
   ```

2. Run a **dry-run** to preview changes:

   ```bash
   nautobot-mcp onboard config config.json core-rtr-01 \
     --location "HAN DC1" \
     --device-type "MX480" \
     --role Router \
     --namespace Global
   ```

3. Review the planned actions (create / update / skip per object).

4. Apply with `--commit`:

   ```bash
   nautobot-mcp onboard config config.json core-rtr-01 --commit
   ```

Objects created: **Device → Interfaces → IP Addresses → VLANs**

---

## CMS Drift Detection (v1.2)

Compare live Juniper device state (collected via jmcp) against Nautobot CMS model records.
No config files required — data flows directly between tools.

### BGP Drift

```bash
# Collect live BGP output from jmcp and save to file
# Then compare against Nautobot CMS records
nautobot-mcp cms drift bgp --device core-rtr-01 --from-file live-bgp.json

# Machine-readable output
nautobot-mcp --json cms drift bgp --device core-rtr-01 --from-file live-bgp.json
```

Input (`live-bgp.json`) is a list of BGP neighbor records:
```json
[{"peer_ip": "10.0.0.1", "peer_as": 65001, "local_address": "10.0.0.2", "group_name": "EXTERNAL"}]
```

### Route Drift

```bash
nautobot-mcp cms drift routes --device core-rtr-01 --from-file live-routes.json
```

### Agent Workflow (no filesystem, v1.3 API Bridge)

AI agents chain jmcp + the 3 API Bridge tools directly:

```
# Step 0: Discover workflows
nautobot_api_catalog(domain="workflows")
→ Returns all 10 workflow IDs with signatures

# Step 1: Collect live BGP from jmcp
execute_junos_command(router_name="core-rtr-01", command="show bgp summary | display json")
→ Returns live BGP neighbor list

# Step 2: Compare against CMS (single workflow call)
nautobot_run_workflow(workflow_id="compare_bgp", params={
    "device_name": "core-rtr-01",
    "live_neighbors": <output from step 1>
})
→ {"workflow": "compare_bgp", "status": "ok", "data": {
     "total_drifts": 0, "missing": [], "extra": [], "changed": []
   }}
```

See `cms-device-audit` (`.agent/skills/cms-device-audit/SKILL.md`) for the full 6-step audit workflow.

---

## Drift Detection

### File-based (DiffSync, requires parsed config)

Compare a parsed JunOS config against Nautobot:

```bash
# Human-readable drift table
nautobot-mcp verify data-model config.json core-rtr-01

# JSON output for scripting
nautobot-mcp verify data-model config.json core-rtr-01 --json
```

Output shows **missing**, **extra**, and **changed** items across Interfaces, IP Addresses, and VLANs.

### File-free — no config file needed

Pass interface data directly — as CLI flags, a JSON string, a file, or piped stdin:

```bash
# Quick single-interface check
nautobot-mcp verify quick-drift core-rtr-01 -i ae0.0 --ip 10.1.1.1/30 --vlan 100

# Bulk check via JSON string
nautobot-mcp verify quick-drift core-rtr-01 -d '{"ae0.0": {"ips": ["10.1.1.1/30"], "vlans": [100]}, "ge-0/0/0.0": {"ips": ["192.168.1.1/24"]}}'

# From a file
nautobot-mcp verify quick-drift core-rtr-01 -f drift-input.json

# JSON output for agent consumption
nautobot-mcp verify quick-drift core-rtr-01 -f drift-input.json --json
```

Output shows per-interface ✅ OK / ❌ DRIFT with details on missing/extra IPs and VLANs.

#### Agent workflow (no filesystem, v1.3 API Bridge)

AI agents use the workflow runner directly:

```
# File-free drift via workflow
nautobot_run_workflow(workflow_id="compare_device", params={
    "device_name": "core-rtr-01",
    "live_data": <structured interface dict from jmcp>
})
→ {"workflow": "compare_device", "status": "ok", "data": {
     "summary": {"total_drifts": 0, ...},
     "interface_drifts": [...]
   }}
```

---

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests (excludes live UAT tests by default)
uv run pytest

# Run tests with output
uv run pytest -v

# Run a single test file
uv run pytest tests/test_bridge.py

# Run live UAT tests (requires NAUTOBOT_UAT_URL + NAUTOBOT_TOKEN)
pytest tests/test_uat.py -m live -v

# Quick smoke test against live server
python scripts/uat_smoke_test.py
```

---

## Deployment

### As a systemd service (Linux)

```ini
# /etc/systemd/system/nautobot-mcp.service
[Unit]
Description=Nautobot MCP Server
After=network.target

[Service]
Type=simple
User=nautobot-mcp
WorkingDirectory=/opt/nautobot-mcp-cli
ExecStart=/opt/nautobot-mcp-cli/.venv/bin/python main.py
Restart=on-failure
Environment=NAUTOBOT_URL=https://nautobot.example.com
Environment=NAUTOBOT_TOKEN=your-token-here

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable nautobot-mcp
sudo systemctl start nautobot-mcp
```

### Using Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
CMD ["uv", "run", "python", "main.py"]
```

```bash
docker build -t nautobot-mcp-cli .
docker run -e NAUTOBOT_URL=https://nautobot.example.com \
           -e NAUTOBOT_TOKEN=your-token-here \
           nautobot-mcp-cli
```

---

## License

MIT — see [LICENSE](LICENSE).
