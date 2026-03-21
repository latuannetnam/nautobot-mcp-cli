# Phase 13: CMS Drift Verification - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build drift comparison tools that compare live Juniper device state (via jmcp) against Nautobot CMS model records. Two drift domains: BGP neighbors (DRIFT-01) and static routes (DRIFT-02). Uses DiffSync for semantic diffing and produces structured drift reports with missing/extra/changed categories.

</domain>

<decisions>
## Implementation Decisions

### Live Data Source Strategy
- **Agent-provides-data pattern** — The drift tools accept pre-fetched jmcp output as structured input (dict/list)
- Matches the existing `compare_device` pattern in `drift.py`
- Agent calls jmcp first (`show bgp summary`, `show route static`), then passes output to the drift MCP tool
- Drift tools are decoupled from jmcp — testable with mock data, no live device dependency
- Two MCP tool calls per drift check (jmcp → drift tool), but composable and reliable

### Comparison Field Scope
- **BGP neighbors:** Compare peer IP + peer AS + local-address + group name (identity + config fields)
  - Excludes volatile runtime state: session state (Established/Active), prefix counts (received/accepted/active)
  - Rationale: Runtime state fluctuates and would always show as "drift" on flapping peers
- **Static routes:** Compare destination + next-hop(s) + preference + metric + routing-instance
  - Captures all configurable routing attributes
  - Excludes operational state (active/inactive)

### Drift Report Format
- **New `CMSDriftReport` Pydantic model** with CMS-specific sections
  - Sections: `bgp_neighbors: DriftSection`, `static_routes: DriftSection`
  - Reuses existing `DriftSection` and `DriftItem` building blocks from `models/verification.py`
  - Same missing/extra/changed pattern agents already understand
  - Does NOT reuse `DriftReport` (which has hardcoded `interfaces`/`ip_addresses`/`vlans` sections)
  - Does NOT reuse `QuickDriftReport` (different per-entry flat structure)

### Comparison Engine
- **DiffSync adapters** — Create DiffSync adapter classes for both live and CMS sides
  - `LiveBGPAdapter` / `CMSBGPAdapter` for BGP neighbor comparison
  - `LiveStaticRouteAdapter` / `CMSStaticRouteAdapter` for static route comparison
  - Consistent with the `verification.py` DiffSync pattern (Phase 4)
  - DiffSync handles the diff algorithm, adapter classes handle data loading/normalization

### Claude's Discretion
- Input normalization strategy for jmcp output (auto-detect `show bgp summary` vs `show bgp neighbor` formats)
- DiffSync model field mapping details
- Error handling for malformed jmcp output
- Whether to split into one module or two (bgp_drift.py vs cms_drift.py)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Drift Patterns
- `nautobot_mcp/verification.py` — DiffSync-based drift comparison (interfaces, IPs, VLANs). Reference for adapter pattern.
- `nautobot_mcp/drift.py` — File-free drift comparison. Reference for input normalization and report building.
- `nautobot_mcp/models/verification.py` — `DriftItem`, `DriftSection`, `DriftReport` models to reuse.
- `nautobot_mcp/models/drift.py` — `QuickDriftReport`, `InterfaceDrift`, `DriftSummary` models (reference, not reused).

### CMS Routing Models (data source for Nautobot side)
- `nautobot_mcp/cms/routing.py` — `list_bgp_neighbors()`, `list_static_routes()`, `list_bgp_groups()` CRUD functions.
- `nautobot_mcp/models/cms/routing.py` — BGP/static route Pydantic models (`BGPNeighborSummary`, `StaticRouteSummary`, etc.).

### MCP Tool Patterns
- `nautobot_mcp/server.py` — Existing drift MCP tools (`nautobot_compare_device`) for pattern reference.

### Requirements
- `.planning/REQUIREMENTS.md` §Drift Verification — DRIFT-01 (BGP), DRIFT-02 (static routes)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DriftSection` / `DriftItem` from `models/verification.py` — Inner structure for missing/extra/changed categorization
- `_build_summary()` from `verification.py` — Summary counting logic (adaptable for CMS sections)
- `_diffsync_to_drift_report()` from `verification.py` — DiffSync diff → report translation pattern
- CMS routing CRUD functions — Ready-to-use Nautobot data fetching for the CMS adapter side

### Established Patterns
- DiffSync adapter pattern: `ParsedConfigAdapter` / `NautobotLiveAdapter` in `verification.py`
- `Adapter.load()` method populates DiffSync models from data source
- `nautobot_adapter.diff_from(source_adapter)` produces diff object
- File-free input: `_normalize_input()` in `drift.py` auto-detects input shape

### Integration Points
- New MCP tools registered in `server.py` under `# CMS DRIFT TOOLS` section
- New Pydantic model `CMSDriftReport` in `models/cms/` or `models/`
- New comparison module `nautobot_mcp/cms/drift.py` or `nautobot_mcp/cms_drift.py`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following the established DiffSync pattern.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-cms-drift-verification*
*Context gathered: 2026-03-21*
