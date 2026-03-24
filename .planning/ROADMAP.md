# Roadmap: nautobot-mcp-cli

**Created:** 2026-03-17
**Granularity:** Coarse (3-5 phases per milestone)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-18) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Agent-Native MCP Tools** — Phases 5-7 (shipped 2026-03-20) — [Archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Juniper CMS Model MCP Tools** — Phases 8-14 (shipped 2026-03-21) — [Archive](milestones/v1.2-ROADMAP.md)
- ❌ **v1.3 Generic Resource Engine** — REJECTED (superseded by API Bridge design, 2026-03-24)
- 🔄 **v1.3 API Bridge MCP Server** — Phases 15+ (in progress)

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

### 🔄 v1.3 API Bridge MCP Server

_Phases pending — to be defined by gsd-new-milestone workflow._

---
*Last updated: 2026-03-24 — v1.3 Generic Resource Engine rejected, API Bridge adopted*
