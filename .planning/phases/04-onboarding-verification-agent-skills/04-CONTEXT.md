# Phase 4: Onboarding, Verification & Agent Skills - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the high-value workflows: config onboarding (parse → push to Nautobot), compliance verification (live vs golden/data model), and agent skills that chain nautobot-mcp + jmcp tools. Skills are agent-side orchestration guides, not compound MCP tools. All onboarding operations support dry-run (default) and commit modes.

</domain>

<decisions>
## Implementation Decisions

### Onboarding Object Resolution Strategy
- Support both **existing device update** and **new device creation** during onboarding
- Dry-run + commit modes available for **all** onboarding operations (dry-run is the default)
- **Interfaces**: dry-run shows plan ("will create / will update / will skip"), commit executes creates/updates
- **IP addresses**: auto-create the smallest containing prefix if the parent prefix doesn't exist in Nautobot
- **Prerequisites** (device type, manufacturer, location): auto-detect from parsed config → search Nautobot for matching objects → offer to create if not found
- **Idempotency matching**: match by name + device (`(device_name, interface_name)` for interfaces, `(address, device)` for IPs)
- **Attribute conflicts**: default is skip and report; `--update-existing` flag to update existing objects to match parsed config

### Dry-Run & Commit Behavior
- **Default mode**: dry-run (safe by default, user must explicitly commit)
- **Dry-run output format**: summary first (`Will create: 3 interfaces, 5 IPs. Will update: 2 interfaces. Will skip: 12 unchanged.`), then detail action table (`| Action | Type | Name | Details |`)
- **Commit mode**: explicit `--commit` / `dry_run=False` parameter required

### Drift Report Format & Granularity
- **Config compliance** (VERIFY-01): use existing `quick_diff_config` text-level diff approach for live vs Golden Config intended comparison
- **Data model verification** (VERIFY-02): object-by-object comparison — for each Nautobot interface, check live router (and vice versa), compare attributes
- **Research**: investigate **DiffSync** model from Nautobot Device Onboarding app for the comparison engine
- **Report structure** (VERIFY-03): grouped by type — `{interfaces: {missing: [...], extra: [...], changed: [...]}, ip_addresses: {...}}`
- **Report format** (VERIFY-04): suitable for both human reading (formatted table) and agent processing (JSON)
- **Live config source**: accept pre-fetched config if provided, otherwise try jmcp directly (flexible input)

### Agent Skill Orchestration Model
- Skills live in a **separate `skills/` package** — not in core library
- **Loose coupling with jmcp**: skills expect the AI agent to call jmcp separately and provide config output as input. Skills only handle parse + push / compare + report
- **Progress reporting**: yield/callback progress events as each step completes
- **Skills as agent-side orchestration guides**: implemented as `.agent/skills/` markdown files with step-by-step instructions. The AI agent reads the guide and calls individual MCP tools in sequence
- **No CLI skill commands**: CLI already covers automation needs; skills are for AI agent workflows only
- **No compound MCP tools for skills**: agents call existing granular tools orchestrated by the skill guide

### Claude's Discretion
- DiffSync integration approach and adapter implementation details
- Exact onboarding function signatures and parameter validation
- Progress callback mechanism (Python generators, async callbacks, etc.)
- Prefix auto-creation logic (how to compute smallest containing prefix)
- Device type / manufacturer auto-detection heuristics from parsed config
- Skill guide markdown format and step-by-step structure
- Dry-run report rendering (tabulate format, column widths, etc.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Requirements
- `.planning/PROJECT.md` — Architecture: shared core + thin MCP/CLI layers, vendor scope
- `.planning/REQUIREMENTS.md` — ONBOARD-01 through ONBOARD-04, VERIFY-01 through VERIFY-04, SKILL-01 through SKILL-03
- `.planning/ROADMAP.md` — Phase 4 success criteria

### Prior Phase Context
- `.planning/phases/01-core-foundation-nautobot-client/01-CONTEXT.md` — API response format (pydantic models), error handling (exception hierarchy with hints), config patterns, filtering approach
- `.planning/phases/02-mcp-server-cli/02-CONTEXT.md` — MCP tool design (one per function, `nautobot_` prefix), CLI structure (Typer nested commands), output formatting, error handling patterns
- `.planning/phases/03-golden-config-config-parsing/03-CONTEXT.md` — Golden Config API access, parser strategy (JSON-first), VendorParser ABC, ParsedConfig models, compliance check behavior

### Research (Phase 4-specific)
- Nautobot Device Onboarding app — DiffSync model for object-by-object comparison
- DiffSync library — adapter pattern for source/target synchronization

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `nautobot_mcp/models/parser.py` — `ParsedConfig`, `ParsedInterface`, `ParsedIPAddress`, `ParsedVLAN` etc. — Nautobot-aligned field names, direct mapping targets for onboarding
- `nautobot_mcp/parsers/` — `VendorParser` ABC + `ParserRegistry` + `JunOSParser` — parse jmcp output into `ParsedConfig`
- `nautobot_mcp/golden_config.py` — `quick_diff_config()` for text-level config diff, `get_intended_config()` / `get_backup_config()` for config retrieval
- `nautobot_mcp/models/golden_config.py` — `ComplianceResult`, `ComplianceFeatureResult` — reusable for drift report structure
- `nautobot_mcp/client.py` — `NautobotClient` with all CRUD methods for devices, interfaces, IPAM
- `nautobot_mcp/devices.py` — `create_device()`, `update_device()`, `get_device()` — onboarding target operations
- `nautobot_mcp/interfaces.py` — `create_interface()`, `update_interface()`, `list_device_interfaces()` — onboarding target operations
- `nautobot_mcp/ipam.py` — `create_ip_address()`, `create_prefix()`, `list_ip_addresses()` — IP/prefix onboarding
- `nautobot_mcp/exceptions.py` — `NautobotNotFoundError`, `NautobotValidationError` — error handling with hints

### Established Patterns
- Domain module per area (`devices.py`, `interfaces.py`, etc.) — onboarding gets its own module, verification gets its own module
- All domain functions take `client: NautobotClient` as first argument
- Pydantic models with `.from_nautobot()` classmethod for return types
- `ListResponse[T]` pattern for consistent list responses
- MCP tools wrap core functions with `@mcp.tool()` decorators
- CLI commands use Typer with domain groups

### Integration Points
- `nautobot_mcp/__init__.py` — New onboarding and verification functions added to `__all__`
- `nautobot_mcp/server.py` — New MCP tools for onboarding and verification operations
- `nautobot_mcp/cli/` — New CLI subcommands: `onboard` and `verify`
- `.agent/skills/` — New skill guide markdown files for agent orchestration
- `pyproject.toml` — May need `diffsync` dependency (pending research)

</code_context>

<specifics>
## Specific Ideas

- DiffSync from Nautobot ecosystem could provide a battle-tested adapter pattern for object-by-object comparison
- `ParsedConfig` models already mirror Nautobot objects — onboarding is largely a matter of mapping + CRUD calls
- Loose coupling with jmcp means skills work even if jmcp is unavailable (user can provide config from any source)
- Default dry-run mode prevents accidental data creation — safety-first approach
- Skill guides as markdown files align with the existing `.agent/skills/` pattern in the project

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-onboarding-verification-agent-skills*
*Context gathered: 2026-03-17*
