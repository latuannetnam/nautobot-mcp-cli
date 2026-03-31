# Roadmap: nautobot-mcp-cli

**Created:** 2026-03-26
**Granularity:** Coarse (3-5 phases per milestone)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-18) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Agent-Native MCP Tools** — Phases 5-7 (shipped 2026-03-20) — [Archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Juniper CMS Model MCP Tools** — Phases 8-14 (shipped 2026-03-21) — [Archive](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 API Bridge MCP Server** — Phases 15-18 (shipped 2026-03-25) — [Archive](milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 Operational Robustness** — Phases 19-22 (shipped 2026-03-26) — [Archive](milestones/v1.4-ROADMAP.md)
- ✅ **v1.5 Agent Performance & Quality** — Phases 23-27 (scope only — not built; requirements deferred) — [Archive](milestones/v1.5-ROADMAP.md)
- ✅ **v1.6 Query Performance Optimization** — Phases 28-29 (shipped 2026-03-28) — [Archive](milestones/v1.6-ROADMAP.md)
- ✅ **v1.7 URI Limit & Server Resilience** — Phases 30-32 (shipped 2026-03-29) — [Archive](milestones/v1.7-ROADMAP.md)
- ✅ **v1.8 CMS Pagination Fix** — Phase 33 (shipped 2026-03-30) — [Archive](milestones/v1.8-ROADMAP.md)
- ✅ **v1.9 CMS Performance Fix** — Phase 34 (shipped 2026-03-30) — [Archive](milestones/v1.9-ROADMAP.md)
- ✅ **v1.10 CMS N+1 Query Elimination** — Phases 35-38 (shipped 2026-03-31) — [Roadmap](milestones/v1.10-ROADMAP.md)

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

<details>
<summary>✅ v1.5 Agent Performance & Quality (Phases 23-27) — NOT BUILT</summary>

- [~] Phase 23: Contract & Envelope Stability (ENV-01..ENV-05) — not started
- [~] Phase 24: Batch Execution Engine (BAT-01..BAT-05) — not started
- [~] Phase 25: Projection & Token Efficiency (PRT-01..PRT-06) — not started
- [~] Phase 26: Security & Resource Guardrails (SEC-01..SEC-06) — not started
- [~] Phase 27: KPI Benchmarks & Verification (KPI-01..KPI-04) — not started

*Scope only — requirements deferred to next milestone*

</details>

<details>
<summary>✅ v1.6 Query Performance Optimization (Phases 28-29) — SHIPPED 2026-03-28</summary>

- [x] Phase 28: Adaptive Count & Fast Pagination (1/1 plan) — completed 2026-03-28
- [x] Phase 29: Direct /count/ Endpoint & Consistency (1/1 plan) — completed 2026-03-28

</details>

<details>
<summary>✅ v1.7 URI Limit & Server Resilience (Phases 30-32) — SHIPPED 2026-03-29</summary>

- [x] Phase 30: Direct HTTP Bulk Fetch for get_device_ips() (1/1 plan) — completed 2026-03-29
- [x] Phase 31: Bridge Param Guard (1/1 plan) — completed 2026-03-29
- [x] Phase 32: VLANs 500 Fix + Regression Tests (1/1 plan) — completed 2026-03-29

</details>

### v1.8 CMS Pagination Fix (SHIPPED 2026-03-30)

- [x] Phase 33: CMS Pagination Fix
  - [x] Plan 01: Smart page-size override in `cms_list()` with `_CMS_BULK_LIMIT = 200` — completed 2026-03-30
  - [x] Plan 02: Regression tests via `uat_cms_smoke.py` HTTP call counting — completed 2026-03-30

### v1.9 CMS Performance Fix (SHIPPED 2026-03-30)

- [x] Phase 34: CMS Performance Fix
  - [x] Plan 01: Gate AF/policy fetches behind `detail=True` in `get_device_bgp_summary()` — bgp_summary: 85s → 2.2s — completed 2026-03-30
  - [x] Plan 02: Lower `devices_inventory` CLI default `--limit` 50 → 10 — completed 2026-03-30

### v1.10 CMS N+1 Query Elimination (PLANNING)

- [x] Phase 35: `interface_detail` N+1 Fix
  - [x] Plan 01: Eliminate per-unit family refetch (bulk families → lookup map) — `598284a`
  - [x] Plan 02: Eliminate per-family VRRP loop (bulk VRRP → lookup map) — `749c508`
  - [x] Plan 03: Unit tests — 8 new tests in `test_cms_interfaces_n1.py` — `a4d1611`
- [x] Phase 36: `firewall_summary` Detail N+1 Fix (completed 2026-03-31)
  - [x] Plan 01: Eliminate per-filter term refetch (bulk terms → lookup map)
  - [x] Plan 02: Eliminate per-term action refetch (bulk actions → lookup map)
  - [x] Plan 03: Unit tests — 8 new tests in `test_cms_firewalls_n1.py` — `683ff5c`
- [x] Phase 37: `routing_table` + `bgp_summary` N+1 Fixes (COMPLETED 2026-03-31)
  - [x] Plan 01: Remove per-route nexthop fallback loop in `routing_table` — `d93a84a`
  - [x] Plan 02: Document `bgp_summary` triple-guard rationale (CQP-04) — `5d0fb16`
  - [x] Plan 03: Unit tests for routing/bgp bulk lookup invariants — `145f2c5`
- [x] Phase 38: Regression Gate (SHIPPED 2026-03-31)
  - [x] Plan 01: `uat_cms_smoke.py` — all 5 workflows pass within thresholds on HQV-PE1-NEW — 5/5 PASS, exit 0
  - [x] Plan 02: Full unit test suite — 546/546 unit tests pass, 0 failed, 0 errored; 10 pre-existing UAT fixture errors (scripts/uat_smoke_test.py, requires live server)

### Next Milestone: v2.0 (TBD)

---
*Last updated: 2026-03-31 — v1.10 COMPLETE (Phases 35-38 shipped); 75/75 plans total*
