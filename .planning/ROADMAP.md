# Roadmap: nautobot-mcp-cli

**Created:** 2026-03-17
**Granularity:** Coarse (3-5 phases per milestone)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-18) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Agent-Native MCP Tools** — Phases 5-7 (shipped 2026-03-20) — [Archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Juniper CMS Model MCP Tools** — Phases 8-14 (shipped 2026-03-21) — [Archive](milestones/v1.2-ROADMAP.md)
- ❌ **v1.3 Generic Resource Engine** — REJECTED (superseded by API Bridge design, 2026-03-24)
- 🔄 **v1.3 API Bridge MCP Server** — Phases 15-18 (in progress)

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

- [x] Phase 15: Catalog Engine & Core Endpoints (completed 2026-03-24)
- [ ] Phase 16: REST Bridge & Universal CRUD
- [ ] Phase 17: Workflow Registry & Server Consolidation
- [ ] Phase 18: Agent Skills, Tests & UAT

---

## Phase Details

### Phase 15: Catalog Engine & Core Endpoints

**Goal:** Build the API catalog engine that lets agents discover available Nautobot endpoints and workflows.

**Requirements:** CAT-01, CAT-02, CAT-03, CAT-04, CAT-05, CAT-06, TST-02

**Success criteria:**
1. `nautobot_api_catalog()` returns all endpoint types grouped by domain (dcim, ipam, circuits, tenancy, cms, workflows)
2. `nautobot_api_catalog(domain="dcim")` returns only DCIM endpoints
3. CMS endpoints auto-discovered from `CMS_ENDPOINTS` — adding a CMS endpoint to the registry automatically appears in catalog
4. Catalog response stays under 1500 tokens
5. `test_catalog.py` validates completeness and domain filtering

---

### Phase 16: REST Bridge & Universal CRUD

**Goal:** Build the universal `call_nautobot` tool that dispatches CRUD operations to the correct backend based on endpoint prefix.

**Requirements:** BRG-01, BRG-02, BRG-03, BRG-04, BRG-05, BRG-06, BRG-07, TST-01, TST-03

**Success criteria:**
1. `call_nautobot("/api/dcim/devices/", "GET", params={"name": "X"})` returns device data via pynautobot
2. `call_nautobot("cms:juniper_static_routes", "GET", params={"device": "X"})` returns CMS data via CMS helpers
3. Invalid endpoint returns error with "did you mean?" hint (not stack trace)
4. GET auto-pagination works with `limit` parameter
5. All 293+ existing domain module tests pass unchanged
6. `test_bridge.py` validates routing, validation, and error hints

---

### Phase 17: Workflow Registry & Server Consolidation

**Goal:** Build the workflow registry wrapping existing composite functions, and rewrite `server.py` to expose only 3 tools.

**Requirements:** WFL-01, WFL-02, WFL-03, WFL-04, WFL-05, WFL-06, SVR-01, SVR-02, SVR-03, SVR-04, TST-04, TST-05

**Success criteria:**
1. `run_workflow("bgp_summary", {"device": "X"})` returns BGP summary data
2. All 10 composite workflows registered and callable with documented params
3. Parameter normalization handles `device` vs `device_name` inconsistencies
4. `server.py` reduced to ~200 lines with exactly 3 `@mcp.tool` definitions
5. `test_workflows.py` validates dispatch and parameter normalization
6. Updated `test_server.py` validates 3-tool interface

---

### Phase 18: Agent Skills, Tests & UAT

**Goal:** Update all agent skills to reference the new 3-tool API and validate everything against the live Nautobot dev server.

**Requirements:** SKL-01, SKL-02, SKL-03, SKL-04, SKL-05, TST-06, TST-07, TST-08

**Success criteria:**
1. `cms-device-audit` skill references `call_nautobot` and `run_workflow` (not old tool names)
2. `onboard-router-config` skill uses `run_workflow("onboard_config", ...)` 
3. `verify-compliance` skill uses `run_workflow("verify_compliance", ...)`
4. UAT smoke test passes against Nautobot dev server (http://101.96.85.93)
5. `nautobot_api_catalog()` returns expected domains from live server
6. `call_nautobot("/api/dcim/devices/", "GET")` returns real device data from live server

---
*Last updated: 2026-03-24 — v1.3 API Bridge roadmap created (4 phases, 36 requirements)*
