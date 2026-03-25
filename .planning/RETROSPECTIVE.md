# Retrospective

Living milestone retrospective for nautobot-mcp-cli.

---

## Milestone: v1.2 — Juniper CMS Model MCP Tools

**Shipped:** 2026-03-21
**Phases:** 6 | **Plans:** 18 | **Commits:** 62

### What Was Built

- Full CRUD for 5 Juniper CMS model domains: routing (BGP + static routes), interfaces (units, families, VRRP), firewalls, policies, ARP — 118 MCP tools total
- 4 composite summary tools: `get_device_bgp_summary`, `get_device_routing_table`, `get_interface_detail`, `get_device_firewall_summary`
- DiffSync-based CMS drift engine: `compare_bgp_neighbors` + `compare_static_routes`
- `nautobot-mcp cms` CLI covering all new model domains + drift
- `cms-device-audit` agent skill for 8-step jmcp → CMS audit workflow
- 293 unit tests (up from 105 at v1.1)

### What Worked

- **1:1 Pydantic model strategy** — mirroring the API shape exactly eliminated impedance mismatch friction; adding new endpoints was mechanical and fast
- **Phase-by-domain split** — one phase per model domain (routing/interfaces/firewalls/policies) kept each session focused; no cross-domain coordination overhead
- **Composite tools planned from the start** — building composite aggregators in Phase 12 *after* all primitive CRUD was in place was the right order; composites were thin wrappers
- **DiffSync for drift** — reusing DiffSync patterns from v1.1 `nautobot_compare_device` made the CMS drift engine natural; same report format, same adapter pattern
- **Tests written per-phase** — never accumulated a test debt, each plan included its own tests

### What Was Inefficient

- **CLI extraction needed a separate phase** — CLI commands for CMS tools were scattered across model phases; Phase 14 had to extract drift CLI from routing CLI; better to define CLI modules as part of each model phase from the start
- **REQUIREMENTS.md never ticked during execution** — 35 requirements were all left `[ ]` and had to be bulk-ticked at milestone completion; next milestone should tick off requirements as each plan completes
- **Phase 12 scope grew mid-phase** — composite tools + ARP were combined; ended up being 4 plans instead of 2; should be separate phases next time

### Patterns Established

- `nautobot_mcp/cms/<domain>.py` — one module per CMS model domain, with CRUD functions and composite helpers
- `nautobot_mcp/models/cms/<domain>.py` — one Pydantic model file per domain
- `nautobot_mcp/cli/cms_<domain>.py` — one CLI module per domain, registered under `nautobot-mcp cms <domain>`
- DiffSync adapters: `Live<Model>Adapter` + `CMS<Model>Adapter` pair per drift comparison
- Composite tools return a typed `*Response` model with counts + nested data

### Key Lessons

- Always include CLI module stub as part of each model domain plan — not as a separate phase
- Tick REQUIREMENTS.md requirements off during execution, not at milestone completion
- Define composite tools in their own phase *after* all primitive CRUD is done — this worked well, keep it
- For CMS-style APIs: start with endpoint registry first (Phase 8 pattern) before adding models — this paid dividends for 14+ subsequent plans

### Cost Observations

- Sessions: ~15 conversations across 2 days (2026-03-20 to 2026-03-21)
- Notable: 62 commits, 98 files, +21,735 lines in under 2 days — high throughput due to mechanical nature of CRUD + Pydantic pattern

---

## Milestone: v1.3 — API Bridge MCP Server

**Shipped:** 2026-03-25
**Phases:** 4 (Phases 15-18) | **Plans:** 8 | **Commits:** 38

### What Was Built

- API Catalog engine (`nautobot_api_catalog`) — static core endpoints + dynamic CMS plugin discovery, domain filtering, workflow stubs
- Universal REST bridge (`nautobot_call_nautobot`) — endpoint routing, fuzzy-matching error hints, auto-pagination, CMS prefix routing
- Workflow registry (`nautobot_run_workflow`) — 10 composite workflows wrapping existing domain functions with parameter normalization and response envelopes
- `server.py` consolidated from 3,883 lines / 165 tools to ~200 lines / 3 tools (96% token reduction)
- All 3 agent skills rewritten for 3-tool API: `cms-device-audit`, `onboard-router-config`, `verify-compliance`
- UAT test suite: 11 pytest tests (`@pytest.mark.live`) + 9-check standalone smoke script; both validated against dev server
- 397 unit tests passing, CI/CD clean with `live` marker exclusion

### What Worked

- **Rejected milestone pivot worked cleanly** — Generic Resource Engine was rejected and replaced by API Bridge in the same sprint day; the GSD planning structure made this pivot cost-free (no code written, just planning artifacts)
- **3-tool architecture proved correct** — the catalog → call → workflow progression matched how agents actually reason about unfamiliar APIs; zero backwards-compat aliases needed
- **CMS routing via `cms:` prefix** — elegant extension point; agents use the same `call_nautobot` tool for both Nautobot core REST and CMS plugin endpoints
- **UAT as first-class gate** — requiring 11 live tests to pass against dev server before closing the milestone caught real integration issues that unit tests would have missed
- **Smoke script for quick validation** — standalone `uat_smoke_test.py` is useful for non-pytest verification (ops team, CI without test deps)

### What Was Inefficient

- **REQUIREMENTS.md traceability lag** — WFL-* and SVR-* requirements were all implemented in Phase 17 but not ticked; had to bulk-tick at milestone completion again (same v1.2 problem — not yet fixed as a habit)
- **Smoke script Windows encoding bug** — Unicode ✓/✗ characters broke on Windows CP1252 terminal; should default to ASCII-safe output from the start on any cross-platform script
- **Architecture pivot consumed 1 session** — the Generic Resource Engine research session was not wasted (informed the API Bridge design) but ideally the pivot decision should be faster

### Patterns Established

- 3-tool pattern: `catalog` (discover) → `call_nautobot` (CRUD) → `run_workflow` (composite) — add new workflows to `WORKFLOW_REGISTRY`, never new MCP tools
- Response envelope: `{"status": "ok|error", "workflow": "id", "data": {...}}` — all workflow outputs standardized
- `@pytest.mark.live` + `addopts = "-m 'not live'"` — live server tests always excluded from CI by default; run explicitly with `-m live`
- Agent skills as `.md` files in `nautobot_mcp/skills/` — not served via MCP, distributed as part of the package

### Key Lessons

- Tick REQUIREMENTS.md at plan completion, not milestone completion — set this as a habit in the phase execution workflow
- Use ASCII-safe output for cross-platform scripts from day 1 (avoid Unicode symbols)
- The "clean break" migration (no backwards-compat aliases) was the right call — made the code dramatically simpler
- UAT smoke scripts should be OS-agnostic and test the same logic as pytest UAT for redundancy

### Cost Observations

- Sessions: ~8 conversations across 1 day (2026-03-24 to 2026-03-25)
- Notable: 38 commits, 54 files changed, +8,169 lines — significantly more efficient than v1.2 despite architectural complexity; API Bridge design was well-specified before implementation began

---

## Cross-Milestone Trends

| Milestone | Duration | Commits | Files | Lines Added | MCP Tools | Tests |
|-----------|----------|---------|-------|-------------|-----------|-------|
| v1.0 | 1 day | ~30 | ~60 | ~10k | 44 | 76 |
| v1.1 | 1 day | ~25 | 75 | +8,225 | 46 | 105 |
| v1.2 | 2 days | 62 | 98 | +21,735 | 164 | 293 |
| v1.3 | 1 day | 38 | 54 | +8,169 | 3 (+ 10 workflows) | 397+11 UAT |

**Trend:** v1.3 reversed the tool sprawl curve — from 164 tools back to 3, while tests increased to 397+11 live UAT. The API Bridge trades tool count for architectural elegance. Future milestones should add workflows, not tools.
