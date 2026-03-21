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

## Cross-Milestone Trends

| Milestone | Duration | Commits | Files | Lines Added | MCP Tools | Tests |
|-----------|----------|---------|-------|-------------|-----------|-------|
| v1.0 | 1 day | ~30 | ~60 | ~10k | 44 | 76 |
| v1.1 | 1 day | ~25 | 75 | +8,225 | 46 | 105 |
| v1.2 | 2 days | 62 | 98 | +21,735 | 164 | 293 |

**Trend:** Each milestone roughly doubles the tool count and test count. CMS domain was larger than expected — went from 46 → 164 tools (3.5×).
