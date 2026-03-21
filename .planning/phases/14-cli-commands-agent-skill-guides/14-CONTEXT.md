# Phase 14: CLI Commands & Agent Skill Guides - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose all CMS model tools, composite summary tools, and CMS drift verification via CLI commands. Create an agent skill guide for CMS-aware device audit workflows. All MCP tool registrations in server.py are already complete — this phase is CLI + skill only.

</domain>

<decisions>
## Implementation Decisions

### Drift CLI Module
- New dedicated `cms_drift.py` CLI module registered at `nautobot-mcp cms drift ...`
- Subcommands: `drift bgp` and `drift routes`
- Separate from `cms_routing.py` because drift is its own concern and may expand to interfaces/firewalls later
- Input format: `--from-file` JSON file AND piped stdin support for scripting flexibility
- Both commands accept `--device` (required) and `--from-file` (optional, falls back to stdin)

### Composite Summary CLI
- Claude's discretion on module organization — may add to each domain's existing CLI or create a new `cms_summary.py`
- Must expose: `bgp-summary`, `routing-table`, `interface-detail`, `firewall-summary`
- All commands accept `--device` as the primary filter

### MCP Tool Registration
- All MCP tools are ALREADY registered in `server.py` — no MCP changes needed:
  - Drift: `nautobot_cms_compare_bgp_neighbors` (L3814), `nautobot_cms_compare_static_routes` (L3845)
  - Composites: `nautobot_cms_get_device_bgp_summary`, `nautobot_cms_get_device_routing_table`, `nautobot_cms_get_interface_detail`, `nautobot_cms_get_device_firewall_summary`
  - All routing/interfaces/firewalls/policies/ARP CRUD tools registered

### Agent Skill Guide
- Full device audit workflow — step-by-step guide for agent to perform BGP + routes + interfaces + firewall drift comparison
- Location: `.agent/skills/cms-device-audit/SKILL.md` following existing skill pattern (like `onboard-router-config`)
- Focus on workflow orchestration: which tools to call, in what order, how to interpret results

### Claude's Discretion
- Composite CLI module organization (new `cms_summary.py` vs distributed across domain modules)
- CLI output formatting (table vs JSON default)
- ARP CLI commands (whether to add a dedicated `cms_arp.py` or fold into another module)
- Skill guide detail level for drift interpretation guidance

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CLI Patterns
- `nautobot_mcp/cli/app.py` — CLI root, CMS sub-group registration pattern (L144-150)
- `nautobot_mcp/cli/cms_routing.py` — Existing CMS CLI module pattern (23KB, most feature-complete)
- `nautobot_mcp/cli/verify.py` — Drift output formatting in existing verify CLI

### CMS Core Functions
- `nautobot_mcp/cms/cms_drift.py` — Drift engine: `compare_bgp_neighbors()`, `compare_static_routes()`
- `nautobot_mcp/cms/routing.py` — `get_device_bgp_summary()`, `get_device_routing_table()`
- `nautobot_mcp/cms/interfaces.py` — `get_interface_detail()`
- `nautobot_mcp/cms/firewalls.py` — `get_device_firewall_summary()`
- `nautobot_mcp/cms/arp.py` — ARP CRUD functions

### Skill Reference
- `.agent/skills/onboard-router-config/SKILL.md` — Existing agent skill pattern
- `.agent/skills/verify-compliance/SKILL.md` — Related compliance verification skill

### Requirements
- `.planning/REQUIREMENTS.md` §CLI & Skills — CLI-01, CLI-02, CLI-03, SKILL-01

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `nautobot_mcp/cli/formatters.py` — CLI output formatting helpers (JSON/table toggle)
- `nautobot_mcp/cli/app.py:get_client_from_ctx()` — Client factory from CLI context with profile/URL/token overrides
- `nautobot_mcp/cli/app.py:handle_cli_error()` — Unified error handler mapping exceptions to exit codes
- All CMS domain CLI modules: `cms_routing.py`, `cms_interfaces.py`, `cms_firewalls.py`, `cms_policies.py`

### Established Patterns
- CMS CLI modules use Typer with `routing_app = typer.Typer(...)` pattern
- Commands accept `--device` as primary filter with `typer.Option(...)`
- JSON output via `--json` global flag from `ctx.obj["json"]`
- Error handling via `try/except` with `handle_cli_error(e)` wrapper

### Integration Points
- `app.py` L144-150: CMS sub-group registration — new modules register here
- `cms_drift.py` CLI module needs import + `cms_app.add_typer(drift_app, name="drift")`
- Potential `cms_summary.py` or additions to existing domain CLIs for composite commands

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following established CLI patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-cli-commands-agent-skill-guides*
*Context gathered: 2026-03-21*
