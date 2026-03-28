# nautobot-mcp-cli

**MCP server + CLI for Nautobot network automation** — AI agents (Claude Code, Cursor, etc.) and humans interact with Nautobot via a **3-tool API Bridge**: discover endpoints, call any REST API, or run composite workflows. Covers inventory, config onboarding, drift detection, and Juniper CMS model audits.

Requires: Python ≥ 3.11, Nautobot ≥ 2.x, a valid API token.

---

## Tech Stack

- **Python ≥ 3.11** — all source under `nautobot_mcp/`
- **CLI framework**: Click (`nautobot_mcp/cli/`)
- **MCP server**: FastMCP / MCP v1.4 (`nautobot_mcp/server.py`)
- **Nautobot client**: `pynautobot`
- **Config**: YAML + environment variables (see Configuration section)
- **Package manager**: `uv` (preferred), `pip` as fallback
- **Testing**: `pytest` — unit tests in `tests/`, live UAT in `tests/test_uat.py`

---

## Key Files

| Path | Purpose |
|------|---------|
| `main.py` | MCP server startup entry point |
| `nautobot_mcp/server.py` | MCP server — registers all 3 tools + workflows |
| `nautobot_mcp/client.py` | Nautobot API client (`NautobotClient`) |
| `nautobot_mcp/workflows/` | Composite workflow implementations (10 workflows) |
| `nautobot_mcp/cms/` | CMS plugin client + JunOS models (routing, interfaces, firewalls) |
| `nautobot_mcp/cli/` | CLI command groups: devices, interfaces, ipam, golden-config, onboard, verify, cms |
| `nautobot_mcp/config.py` | Config loading (YAML → env → CLI flags) |
| `nautobot_mcp/parsers/` | Config parsers (JunOS JSON) |

---

## MCP API Bridge — 3 Tools (Core Contract)

Use these 3 tools for all agentic Nautobot interactions. All other MCP tools are deprecated in favor of this bridge.

### `nautobot_api_catalog`
Discover all available endpoints and workflow IDs. Call this first when exploring capabilities.

### `nautobot_call_nautobot`
Universal REST dispatcher — GET/POST/PATCH/DELETE against any `/api/*` or `cms:*` endpoint.
Returns: `{count, results, endpoint, method}` — with `truncated` + `total_available` when capped.

### `nautobot_run_workflow`
Run composite server-side workflows by ID. **Always returns:** `{workflow, device, status, data, error, timestamp}`

### Available Workflow IDs

| Workflow | Covers | Params |
|----------|--------|--------|
| `bgp_summary` | BGP groups + neighbor counts | `detail`, `limit` |
| `routing_table` | Static routes with next-hops | `detail`, `limit` |
| `firewall_summary` | Firewall filters + term counts | `detail`, `limit` |
| `interface_detail` | Interface units with families, VRRP, ARP | `detail`, `limit` |
| `onboard_config` | Parse + push config to Nautobot | `dry_run` (default True) |
| `compare_device` | File-free drift: live interfaces vs Nautobot | — |
| `verify_data_model` | DiffSync model drift report | — |
| `verify_compliance` | Golden Config compliance check | — |
| `compare_bgp` | Live BGP neighbors vs CMS records | — |
| `compare_routes` | Live static routes vs CMS records | — |

---

## CLI Commands

```bash
nautobot-mcp --json devices list
nautobot-mcp --json devices get --name <name>
nautobot-mcp --json devices summary <name>
nautobot-mcp --json devices summary <name> --detail
nautobot-mcp --json interfaces list --device <name>
nautobot-mcp --json ipam prefixes list
nautobot-mcp --json ipam addresses list --device <name>
nautobot-mcp --json golden-config compliance-results <name>
nautobot-mcp --json onboard config <config.json> <device-name>
nautobot-mcp --json onboard config <config.json> <device-name> --commit
nautobot-mcp --json verify compliance <name>
nautobot-mcp --json verify quick-drift <name> --interface <if> --ip <ip/mask>
nautobot-mcp --json cms routing bgp-summary --device <name>
nautobot-mcp --json cms interfaces detail --device <name>
nautobot-mcp --json cms firewalls firewall-summary --device <name>
```

---

## Configuration

Config sources (highest wins): **CLI flags → env vars → YAML → defaults**

### Profiles (`.nautobot-mcp.yaml`)

| Profile | URL | verify_ssl |
|---------|-----|-----------|
| **prod** | https://nautobot.netnam.vn | true |
| **dev** | http://101.96.85.93 | false |

```bash
# Use prod (default)
nautobot-mcp --json devices list

# Use dev override
nautobot-mcp --profile dev --json devices list

# Env var override
export NAUTOBOT_URL=https://nautobot.example.com
export NAUTOBOT_TOKEN=your-token-here
```

---

## Conventions

- **Always use `--json`** for structured output — avoids Unicode encoding crashes on Windows (`charmap codec can't encode \u2192`)
- **Global `--json` flag** comes BEFORE the subcommand: `nautobot-mcp --json devices list`
- **`--limit 0`** means unlimited (auto-paginated by pynautobot)
- **Agent workflow**: prefer `nautobot_run_workflow` over raw `nautobot_call_nautobot` for multi-step operations

## Common Mistakes to Avoid

| ❌ Wrong | ✅ Correct |
|----------|-----------|
| `devices list --json` | `nautobot-mcp --json devices list` |
| Assuming `count` = total records (it's per-page) | Use `--offset` + `--limit` to paginate |
| Running live tests without credentials | `NAUTOBOT_URL` + `NAUTOBOT_TOKEN` must be set |
| Ignoring exit code 1 on Windows | Exit 1 often means Unicode encoding error, not API failure — retry with `--json` |
| Onboarding without `--commit` | Dry-run by default; `--commit` to apply changes |

---

## Testing

```bash
# Unit tests (default — no credentials needed)
uv run pytest -q

# Unit tests, verbose
uv run pytest -v

# Single test file
uv run pytest tests/test_bridge.py -v

# Live UAT (requires NAUTOBOT_URL + NAUTOBOT_TOKEN)
uv run pytest -m live -v

# Smoke test against live server
python scripts/uat_smoke_test.py
```

---

## MCP Server

```bash
# Recommended
uv run python main.py

# Via fastmcp CLI
uv run fastmcp run nautobot_mcp/server.py

# With custom config
NAUTOBOT_URL=https://nautobot.example.com NAUTOBOT_TOKEN=xxx uv run python main.py
```

### MCP Client Integration (claude_desktop_config.json)

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

---

## Project Skills

Claude Code skills are defined in `.claude/skills/` and `.agent/skills/`:

- **`nautobot-device-info`** — Device/interface/IPAM query guide with Windows encoding notes
- **`gsd:*`** — GSD (Get Shit Done) workflow commands for milestone/phase management
- **`.agent/skills/`** — Agentic workflows: `onboard-router-config`, `cms-device-audit`

Install skills to your Claude Code profile:
```powershell
pwsh scripts/install-skills.ps1
```

---

## Active Milestone

**v1.5 — MCP Server Quality & Agent Performance**

Roadmap: `.planning/ROADMAP.md` | State: `.planning/STATE.md`
