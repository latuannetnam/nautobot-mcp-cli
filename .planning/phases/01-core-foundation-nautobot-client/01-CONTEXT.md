# Phase 1: Core Foundation & Nautobot Client - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish the project structure, Nautobot API client (pynautobot wrapper), and core data model operations covering all CRUD for Devices, Interfaces, IPAM (Prefix, IP Address, VLAN), Organization (Tenant, Location), and Circuits. This is the shared core library that MCP server and CLI layers will consume in Phase 2.

</domain>

<decisions>
## Implementation Decisions

### API Response Format
- Pydantic models for all return types — typed, validated, serializable
- Curated fields per model — return only the most useful fields, not raw Nautobot payload
- Related objects as inline summaries: `{"location": {"name": "SGN-DC1", "id": "..."}}`
- List operations always return `{"count": N, "results": [...]}`

### Error Handling Strategy
- Custom exception hierarchy: `NautobotConnectionError`, `NautobotNotFoundError`, `NautobotValidationError`
- Structured error responses with actionable guidance: `{"error": "...", "hint": "...", "code": "..."}`
- Retry with exponential backoff (3 attempts) when Nautobot server is unreachable
- Partial failures in multi-object operations: continue and report (summary of successes + failures)

### Nautobot Connection Config
- Multi-server support with named profiles (e.g., `production`, `staging`)
- Env vars primary (`NAUTOBOT_URL`, `NAUTOBOT_TOKEN`), config file fallback (`.nautobot-mcp.yaml`)
- Env vars override config file values
- SSL verification enabled by default, `--no-verify` flag to disable for self-signed certs
- Auto-detect API version from server — query Nautobot API root

### Data Filtering Approach
- Common named filter params per model (devices: location, tenant, role, platform) + `**extra_filters` for passthrough
- Core library auto-paginates internally (fetches all pages transparently)
- MCP layer adds smart defaults: limit=50 by default, `limit` param for agents, `limit=0` for all
- Count always included so agents know total without fetching everything
- Summary mode available for large lists (name + status only, then get_device for details)
- Common sort fields per model: `--sort name`, `--sort created`
- Both name-based search and full-text search (`--search` for name, `--query` for full-text via Nautobot's `q` param)

### Claude's Discretion
- Exact pydantic model field selection per Nautobot model
- Retry timing (backoff multiplier, max delay)
- Config file format details (YAML structure, profile naming)
- Internal pagination page size for pynautobot calls

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Project vision, architecture (shared core + thin layers), vendor scope
- `.planning/REQUIREMENTS.md` — CORE-01 through CIR-03 (27 requirements for this phase)
- `.planning/ROADMAP.md` — Phase 1 success criteria and dependency ordering

### Research
- `.planning/research/STACK.md` — Stack decisions: FastMCP 3.0, pynautobot 2.6.x, Typer
- `.planning/research/ARCHITECTURE.md` — Component structure, data flows, build order
- `.planning/research/PITFALLS.md` — API pagination trap, object reference resolution, API version mismatch

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main.py` — Placeholder entry point, will be replaced with proper module structure
- `pyproject.toml` — Project config, needs dependencies added (pynautobot, pydantic, etc.)

### Established Patterns
- No existing patterns — greenfield project. This phase establishes the foundational patterns.

### Integration Points
- Nautobot server at `https://nautobot.netnam.vn/` — REST API v2
- jmcp (Juniper MCP server) — already configured, provides router config access. Phase 4 will chain with this.

</code_context>

<specifics>
## Specific Ideas

- MCP layer as a "context-aware gateway" — smart defaults that reduce agent token usage
- Curated fields approach means agents don't need to parse through 50+ Nautobot fields per object

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-core-foundation-nautobot-client*
*Context gathered: 2026-03-17*
