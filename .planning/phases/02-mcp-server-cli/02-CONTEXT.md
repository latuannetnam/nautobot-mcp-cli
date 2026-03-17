# Phase 2: MCP Server & CLI - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose all existing core Nautobot operations (devices, interfaces, IPAM, organization, circuits) through two thin interface layers: a FastMCP server for AI agent integration and a Typer CLI for human/script access. Both layers consume the shared core library from Phase 1 — no new Nautobot operations are added.

</domain>

<decisions>
## Implementation Decisions

### MCP Tool Design
- One tool per core function — ~30 individual tools (not grouped)
- Tool names prefixed with `nautobot_` (e.g., `nautobot_list_devices`, `nautobot_get_device`) to avoid collisions with other MCP servers like jmcp
- Rich docstring descriptions including example usage, return format hints, and available filter options
- FastMCP 3.0 with `@mcp.tool()` decorators wrapping core functions
- stdio transport for local agent integration

### CLI Command Structure
- Nested subcommands using Typer: `nautobot-mcp devices list`, `nautobot-mcp ipam prefixes list`
- Entry point: `nautobot-mcp` (single, no short alias)
- Domain groups: `devices`, `interfaces`, `ipam` (with sub: `prefixes`, `addresses`, `vlans`), `org` (with sub: `tenants`, `locations`), `circuits`
- Global flags on every command:
  - `--json` — machine-readable JSON output
  - `--profile` — select config profile (production/staging)
  - `--url` / `--token` — override connection inline
  - `--no-verify` — skip SSL verification
- Shell completion via Typer's built-in support

### Output Formatting
- Agent-first design — CLI is primarily for agent/script consumption
- Table output: plain tabulate (no colors/borders) — agent-parseable, pipe-friendly
- JSON output: wrapped format `{"count": N, "results": [...]}` — consistent with core `ListResponse`
- Default: table output; `--json` flag for machine output
- Agents calling CLI will always use `--json`

### Error Handling
- MCP tools: raise exceptions — FastMCP converts to MCP error responses with `isError: true`. Phase 1 exception hierarchy carries through (`NautobotNotFoundError.hint`, etc.)
- CLI: plain stderr messages (no ANSI colors) for agent compatibility
- CLI exit codes:
  - `0` — success
  - `1` — general error
  - `2` — connection error
  - `3` — not found
  - `4` — validation error

### Claude's Discretion
- Exact Typer app structure (single file vs module per domain)
- MCP server startup/shutdown hooks
- Which tabulate table format (grid, simple, plain)
- How to wire global flags (Typer callback vs context)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Requirements
- `.planning/PROJECT.md` — Architecture: shared core + thin MCP/CLI layers
- `.planning/REQUIREMENTS.md` — MCP-01 through MCP-04, CLI-01 through CLI-04 (8 requirements)
- `.planning/ROADMAP.md` — Phase 2 success criteria

### Research
- `.planning/research/STACK.md` — Stack decisions: FastMCP 3.0, Typer, pynautobot 2.6.x
- `.planning/research/ARCHITECTURE.md` — Component structure and data flows
- `.planning/research/PITFALLS.md` — Known API issues to handle in MCP/CLI layers

### Phase 1 Context
- `.planning/phases/01-core-foundation-nautobot-client/01-CONTEXT.md` — API response format, error handling, config, filtering decisions that MCP/CLI layers must respect

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `nautobot_mcp/__init__.py` — All 30+ core functions already exported via `__all__`; MCP tools wrap these directly
- `nautobot_mcp/client.py` — `NautobotClient` with lazy init and retry; both MCP and CLI instantiate this
- `nautobot_mcp/config.py` — `NautobotSettings` with multi-profile support; CLI global flags map to this
- `nautobot_mcp/models/base.py` — `ListResponse[T]` already matches the JSON output shape decided above
- `nautobot_mcp/exceptions.py` — Full exception hierarchy with `hint` and `code` attributes

### Established Patterns
- All domain functions take `client: NautobotClient` as first argument — MCP tools create client from context, CLI creates from global flags
- Pydantic models with `.from_nautobot()` classmethod — all return types are JSON-serializable
- Consistent CRUD pattern across all 6 domain modules (devices, interfaces, ipam, organization, circuits)

### Integration Points
- `pyproject.toml` — Needs `fastmcp`, `typer`, `tabulate` added to dependencies
- `pyproject.toml [project.scripts]` — Register `nautobot-mcp` CLI entry point
- FastMCP server entry point — new module (e.g., `nautobot_mcp/server.py`)
- Typer CLI entry point — new module (e.g., `nautobot_mcp/cli/`)

</code_context>

<specifics>
## Specific Ideas

- MCP server as primary agent interface, CLI as backup/scripting path
- Agent-first design philosophy — plain output, structured JSON, no interactive prompts
- Both layers are thin wrappers — business logic stays in core library

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-mcp-server-cli*
*Context gathered: 2026-03-17*
