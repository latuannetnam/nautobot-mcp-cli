# Roadmap: nautobot-mcp-cli

**Created:** 2026-03-17
**Granularity:** Coarse (3-5 phases per milestone)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-18) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Agent-Native MCP Tools** — Phases 5-7 (shipped 2026-03-20) — [Archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Juniper CMS Model MCP Tools** — Phases 8-14 (shipped 2026-03-21) — [Archive](milestones/v1.2-ROADMAP.md)
- ❌ **v1.3 Generic Resource Engine** — REJECTED (superseded by API Bridge design, 2026-03-24)
- ✅ **v1.3 API Bridge MCP Server** — Phases 15-18 (shipped 2026-03-25) — [Archive](milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 Operational Robustness** — Phases 19-22 (shipped 2026-03-26)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-03-18</summary>

- [x] Phase 1: Core Foundation & Nautobot Client (4/4 plans)
- [x] Phase 2: MCP Server & CLI (3/3 plans)
- [x] Phase 3: Golden Config & Config Parsing (3/3 plans)
- [x] Phase 4: Onboarding, Verification & Agent Skills (3/3 plans)

</details>

<details>
<summary>✅ v1.1 Agent-Native MCP Tools (Phases 5-7) — SHIPPED 2026-03-20</summary>

- [x] Phase 5: Device-Scoped IP Queries & Cross-Entity Filters (2/2 plans)
- [x] Phase 6: Device Summary & Enriched Interface Data (2/2 plans)
- [x] Phase 7: File-Free Drift Comparison (2/2 plans)

</details>

<details>
<summary>✅ v1.2 Juniper CMS Model MCP Tools (Phases 8-14) — SHIPPED 2026-03-21</summary>

- [x] Phase 8: CMS Plugin Client Foundation (2/2 plans)
- [x] Phase 9: Routing Models — Static Routes & BGP (3/3 plans)
- [x] Phase 10: Interface Models — Units, Families, VRRP (3/3 plans)
- [x] Phase 11: Firewall & Policy Models (3/3 plans)
- [x] Phase 12: ARP & Composite Summary Tools (4/4 plans)
- [x] Phase 13: CMS Drift Verification (2/2 plans)
- [x] Phase 14: CLI Commands & Agent Skill Guides (2/2 plans)

</details>

<details>
<summary>❌ v1.3 Generic Resource Engine — REJECTED 2026-03-24</summary>

Planned phases 15-18 (Resource Registry, Generic CRUD Dispatcher, Server Consolidation, UAT) were rejected before implementation. Superseded by API Bridge architecture (3 tools + agent skills).

See: [API Bridge Design](../docs/plans/2026-03-24-api-bridge-mcp-design.md)

</details>

<details>
<summary>✅ v1.3 API Bridge MCP Server (Phases 15-18) — SHIPPED 2026-03-25</summary>

- [x] Phase 15: Catalog Engine & Core Endpoints (2/2 plans) — completed 2026-03-24
- [x] Phase 16: REST Bridge & Universal CRUD (2/2 plans) — completed 2026-03-24
- [x] Phase 17: Workflow Registry & Server Consolidation (2/2 plans) — completed 2026-03-24
- [x] Phase 18: Agent Skills, Tests & UAT (2/2 plans) — completed 2026-03-25

</details>

<details>
<summary>✅ v1.4 Operational Robustness (Phases 19-22) — SHIPPED 2026-03-26</summary>

- [x] Phase 19: Partial Failure Resilience (2/2 plans) — completed 2026-03-25
- [x] Phase 20: Catalog Accuracy & Endpoint Dereference (2/2 plans) — completed 2026-03-26
- [x] Phase 21: Workflow Contracts & Error Diagnostics (2/2 plans) — completed 2026-03-26
- [x] Phase 22: Response Ergonomics & UAT (1/1 plan) — completed 2026-03-26

</details>

### v1.5 (Planned)

*(coming soon — `/gsd:new-milestone` to start planning)*

---
*Last updated: 2026-03-26 — v1.4 milestone shipped*
