# Phase 3: Golden Config & Config Parsing - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate with Nautobot Golden Config plugin and build a JunOS config parser. This enables reading intended/backup configs from Golden Config, managing compliance rules and features, triggering compliance checks, and structured parsing of router configurations via JSON output from jmcp. Both Golden Config operations and parser are exposed through MCP tools and CLI commands.

</domain>

<decisions>
## Implementation Decisions

### Golden Config API Access
- Use pynautobot's plugin support (`api.plugins.golden_config`) — extensible pattern for future Nautobot app/plugin MCP integrations
- Read-heavy + compliance management scope: intended/backup config retrieval (GC-01, GC-02), compliance rules CRUD (GC-03, GC-04), compliance check trigger + status (GC-05, GC-06)
- Feature-centric compliance rule organization: features as first-class objects, rules nested under features
- Separate functions for config retrieval: `get_intended_config(device)` and `get_backup_config(device)` — explicit, clear for agents

### Config Parser Strategy
- JSON-first via jmcp: use `show configuration | display json` to get structured JSON directly from routers — no text parsing needed
- Network infrastructure extraction scope: interfaces, IPs, VLANs + routing instances, protocols (BGP/OSPF), firewall filters, system settings
- Auto-detect platform from config tree: infer MX/EX/SRX from JSON structure (e.g., `security` block → SRX, `ethernet-switching` → EX)
- Protocol-based ABC aligned with netutils: `VendorParser` abstract base class with registry pattern, platform identified by `network_os` (consistent with Golden Config's platform mapping)

### Parser Output Structure
- Nautobot-aligned pydantic models: parser returns models that mirror Nautobot objects (`ParsedInterface`, `ParsedIPAddress`, etc.) — eliminates translation step in Phase 4 onboarding
- Single `ParsedConfig` container: one top-level model with all extracted data (`hostname`, `platform`, `interfaces`, `ip_addresses`, `vlans`, `routing_instances`, `protocols`)
- Strict + warnings for unknown sections: only recognized data in typed models, `ParsedConfig.warnings: list[str]` captures skipped sections
- Core + MCP + CLI exposure in Phase 3: parser tools available to agents and users immediately (e.g., `nautobot_parse_junos_config`, `nautobot-mcp parse junos`)

### Compliance Check Behavior
- Hybrid approach: server-side full compliance via Golden Config API + lightweight client-side quick diff for on-demand spot checks
- Quick diff uses text diff of config sections: pull intended + backup, compare added/removed/changed lines
- Structured `ComplianceResult` model: same shape for both full compliance and quick diff (`device`, `overall_status`, `features=[ComplianceFeature(name, status, missing_lines, extra_lines)]`)
- Both sync and async execution modes: synchronous with timeout for single device, async with polling (`job_id` → `get_compliance_status()`) for multi-device batch checks

### Claude's Discretion
- Exact pydantic model field names and types for parsed config objects
- JunOS JSON path mappings for each config section
- Platform detection heuristics (which JSON keys trigger which platform)
- Quick diff algorithm (Python difflib vs custom sectional diff)
- Compliance job polling interval and timeout defaults
- How to extend `NautobotClient` for plugin endpoint access

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Requirements
- `.planning/PROJECT.md` — Architecture: shared core + thin MCP/CLI layers, vendor scope
- `.planning/REQUIREMENTS.md` — GC-01 through GC-06 (Golden Config), PARSE-01 through PARSE-04 (Config Parsing)
- `.planning/ROADMAP.md` — Phase 3 success criteria

### Prior Phase Context
- `.planning/phases/01-core-foundation-nautobot-client/01-CONTEXT.md` — API response format (pydantic models), error handling (exception hierarchy with hints), config patterns, filtering approach
- `.planning/phases/02-mcp-server-cli/02-CONTEXT.md` — MCP tool design (one per function, `nautobot_` prefix), CLI structure (Typer nested commands), output formatting, error handling patterns

### Research
- `.planning/research/STACK.md` — Stack decisions: FastMCP 3.0, pynautobot 2.6.x, Typer
- `.planning/research/ARCHITECTURE.md` — Component structure and data flows

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `nautobot_mcp/client.py` — `NautobotClient` with lazy init, `api` property for pynautobot access. Needs `plugins` property or similar for Golden Config endpoints.
- `nautobot_mcp/models/base.py` — `ListResponse[T]` pattern for consistent list responses
- `nautobot_mcp/exceptions.py` — Full exception hierarchy (`NautobotNotFoundError`, `NautobotAPIError`, etc.) with `hint` and `code` attributes
- `nautobot_mcp/server.py` — FastMCP server with 30+ tools; new GC + parser tools extend this
- `nautobot_mcp/cli/` — Typer CLI with domain subcommands; new `golden-config` and `parse` subgroups extend this

### Established Patterns
- Domain module per area (`devices.py`, `interfaces.py`, etc.) — Golden Config gets its own module (e.g., `golden_config.py`), parser gets a `parsers/` package
- All domain functions take `client: NautobotClient` as first argument
- Pydantic models with `.from_nautobot()` classmethod for return types
- Consistent CRUD pattern across all domain modules
- MCP tools wrap core functions with `@mcp.tool()` decorators
- CLI commands use Typer with domain groups

### Integration Points
- `nautobot_mcp/__init__.py` — New Golden Config and parser functions added to `__all__`
- `nautobot_mcp/server.py` — New MCP tools for GC operations and parsing
- `nautobot_mcp/cli/` — New CLI subcommands: `golden-config` and `parse`
- `pyproject.toml` — May need `netutils` dependency for platform identification

</code_context>

<specifics>
## Specific Ideas

- JSON-first parsing via jmcp eliminates fragile text parsing — structured data from the source
- pynautobot plugin pattern enables future MCP integrations with other Nautobot apps/plugins beyond Golden Config
- `network_os` alignment with netutils ensures compatibility with Golden Config's compliance engine
- Quick diff provides immediate value for agents doing spot checks without waiting for full compliance jobs

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-golden-config-config-parsing*
*Context gathered: 2026-03-17*
