---
phase: 7
title: "File-Free Drift Comparison"
decisions:
  input_format: "Both flat map and DeviceIPEntry list (auto-detect), VLANs per-interface"
  drift_response: "Per-interface detail + global summary counts"
  cli_ux: "Flags for quick checks + --data/--file for bulk, table default + --json"
  source_scope: "Generic tool, agent transforms jmcp output, lenient validation with warnings"
---

# Phase 7 Context: File-Free Drift Comparison

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable drift detection using structured data (dicts) instead of requiring `ParsedConfig` objects or config.json files. Agents can chain any data source → drift check without Python scripting. Covers IPs, interfaces, and VLANs with per-interface scoping.

</domain>

<decisions>
## Implementation Decisions

### Input Data Format
- Accept **two input shapes** with auto-detection:
  - **Flat map (primary):** `{"ae0.0": {"ips": ["10.1.1.1/30"], "vlans": [100, 200]}, "ge-0/0/0.0": {"ips": ["192.168.1.1/24"]}}`
  - **DeviceIPEntry list (chaining):** `[{"interface": "ae0.0", "address": "10.1.1.1/30"}, ...]` — output from `get_device_ips()` can be passed directly
- VLANs are **per-interface**, not per-device — compare tagged/untagged VLANs on each interface
- `vlans` key is optional per-interface (only checked when present)

### Drift Response Structure
- **Both** per-interface detail and global summary:
  - Per-interface: `{"ae0.0": {"missing_ips": [...], "extra_ips": [...], "missing_vlans": [...], "extra_vlans": [...]}, ...}`
  - Global summary: `{total_drifts, by_type: {ips: {missing, extra}, vlans: {missing, extra}, interfaces: {missing, extra}}}`
- No unlinked IP reporting — only compare what's explicitly on interfaces
- Creates a new response model (not reusing existing `DriftReport` which is global-scoped)

### CLI Quick-Drift UX
- **Both** flag-based and data-based input:
  - Quick: `nautobot-mcp verify quick-drift HQV-PE-Test --interface ae0.0 --ip 10.1.1.1/30`
  - Bulk: `nautobot-mcp verify quick-drift HQV-PE-Test --data '{"ae0.0": {"ips": [...]}}'`
  - File: `nautobot-mcp verify quick-drift HQV-PE-Test --file drift-input.json`
- Output: **table default + `--json` flag** — colored table with ✅/❌ per interface by default, `--json` for machine-readable

### Source Scope & Validation
- Tool is **vendor-agnostic** — accepts generic `interfaces_data` dict, not tied to JunOS parser
- Agent is responsible for transforming jmcp output into the standard format (documented in tool description + agent skill)
- **Lenient validation with warnings:**
  - Accept IPs with or without prefix length
  - Accept VLAN IDs as int or string
  - Warn when normalizing (e.g., "10.1.1.1 has no prefix length, matching by host only")

### Claude's Discretion
- Internal DiffSync adapter design (whether to reuse `NautobotLiveAdapter` or create new)
- Per-interface comparison algorithm implementation
- Warning message formatting
- Agent skill guide content and structure

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Drift requirements
- `.planning/REQUIREMENTS.md` §DRIFT — DRIFT-01 through DRIFT-04 acceptance criteria

### Existing drift infrastructure
- `nautobot_mcp/verification.py` — Existing DiffSync-based verification engine (DriftReport, adapters)
- `nautobot_mcp/models/verification.py` — DriftItem, DriftSection, DriftReport Pydantic models
- `nautobot_mcp/ipam.py` §get_device_ips — M2M interface→IP traversal (reusable for Nautobot side)

### Parser models (reference for input shape)
- `nautobot_mcp/models/parser.py` — ParsedConfig, ParsedInterface, ParsedIPAddress structure
- `nautobot_mcp/models/ipam.py` — DeviceIPEntry model (chaining input shape)

### Phase context
- `.planning/phases/06-device-summary-enriched-interface-data/06-CONTEXT.md` — Phase 6 decisions on device summary and IP enrichment

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `get_device_ips()` in `ipam.py`: M2M traversal to get Nautobot-side IPs per interface — can feed the "expected" side of comparison
- `list_interfaces()` in `interfaces.py`: Get interfaces from Nautobot for a device
- `list_vlans(device=X)` in `ipam.py`: Get VLANs via interface traversal
- `DriftItem`, `DriftSection` models: Could be adapted for per-interface output
- `_build_summary()` helper: Summary counting pattern to reuse

### Established Patterns
- Core function returns Pydantic model → MCP tool calls `.model_dump()` → CLI formats output
- `NautobotLiveAdapter.load()`: Scoped queries (device-filtered interfaces, VID-filtered VLANs)
- Error handling: `try/except + handle_error(e)` wrapper on all MCP tools
- CLI output: Rich tables with color + `--json` flag pattern (used in Phase 6 `devices summary`)

### Integration Points
- `server.py`: New `nautobot_compare_device` MCP tool registration
- `cli/verify.py`: New `quick-drift` subcommand under `verify` group
- `.agent/skills/`: Update agent skill guide with drift chain workflow

</code_context>

<specifics>
## Specific Ideas

- Input auto-detection: check if `interfaces_data` is a list (DeviceIPEntry shape) or dict (flat map shape) and convert internally
- Per-interface VLAN comparison: compare tagged/untagged VLANs assigned to each interface in Nautobot vs what's in the input
- The original motivation was the HQV-PE-Test MX204 problem where the agent had to write 100 lines of Python — this tool should make that a single MCP call

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-file-free-drift-comparison*
*Context gathered: 2026-03-20*
