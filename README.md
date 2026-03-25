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
git clone https://github.com/latuannetnam/nautobot-mcp-cli.git
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

> **Endpoint reference:** Use `nautobot_api_catalog(domain="dcim")` (or `ipam`, `cms`, `workflows`) to discover the exact endpoint strings and workflow IDs accepted by the two dispatcher tools. All CRUD operations that were previously individual MCP tools are now routed through `nautobot_call_nautobot` or `nautobot_run_workflow`.

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

# CMS Routing
uv run nautobot-mcp cms routing list-static-routes --device core-rtr-01
uv run nautobot-mcp cms routing bgp-summary --device core-rtr-01
uv run nautobot-mcp cms routing routing-table --device core-rtr-01

# CMS Interfaces
uv run nautobot-mcp cms interfaces list-units --device core-rtr-01
uv run nautobot-mcp cms interfaces detail --device core-rtr-01
uv run nautobot-mcp cms interfaces list-arp-entries --device core-rtr-01

# CMS Firewalls
uv run nautobot-mcp cms firewalls list-filters --device core-rtr-01
uv run nautobot-mcp cms firewalls firewall-summary --device core-rtr-01

# CMS Drift — compare live device data against Nautobot CMS records
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

### Via CLI

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

### Via MCP Agent

AI agents use the `onboard_config` workflow (no filesystem required):

```
nautobot_run_workflow(workflow_id="onboard_config", params={
    "config_data": <ParsedConfig dict>,
    "device_name": "core-rtr-01",
    "dry_run": True    # set False to commit
})
→ {"workflow": "onboard_config", "status": "ok", "data": {...}}
```

See the `onboard-router-config` skill (`.agent/skills/onboard-router-config/SKILL.md`) for the full step-by-step agent workflow.

---

## CMS Drift Detection

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
