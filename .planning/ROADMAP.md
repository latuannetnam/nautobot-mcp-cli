# Roadmap: nautobot-mcp-cli

**Created:** 2026-03-17
**Granularity:** Coarse (3-5 phases per milestone)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-18) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Agent-Native MCP Tools** — Phases 5-7 (shipped 2026-03-20) — [Archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Juniper CMS Model MCP Tools** — Phases 8-14 (shipped 2026-03-21) — [Archive](milestones/v1.2-ROADMAP.md)
- 🔄 **v1.3 Generic Resource Engine** — Phases 15-18 (in progress)

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

### 🔄 v1.3 Generic Resource Engine

- [ ] Phase 15: Resource Registry Foundation
- [ ] Phase 16: Generic CRUD Dispatcher & Discovery Tools
- [ ] Phase 17: Server Consolidation & Test Suite
- [ ] Phase 18: UAT Verification & Documentation

---

## Phase Details

### Phase 15: Resource Registry Foundation

**Goal:** Create `registry.py` with unified `RESOURCE_REGISTRY` mapping all resource types to their handlers, models, and metadata.

**Requirements:** REG-01, REG-02, REG-03, REG-04, REG-05

**Success criteria:**
1. `ResourceDef` dataclass defined with domain, handler, model, actions, filter_fields, required_create_fields
2. CMS resources auto-mapped from `CMS_ENDPOINTS` (no duplication)
3. Core resources (device, interface, IP, VLAN, prefix, circuit, tenant, location) mapped to domain functions
4. Import-time validation passes — all handlers and models resolve
5. Automated test confirms 100% coverage of old CRUD operations

---

### Phase 16: Generic CRUD Dispatcher & Discovery Tools

**Goal:** Implement the 3 generic MCP tools: `nautobot_list_resources`, `nautobot_resource_schema`, and `nautobot_resource`.

**Requirements:** DISC-01, DISC-02, DISC-03, DISC-04, CRUD-01, CRUD-02, CRUD-03, CRUD-04, CRUD-05, CRUD-06, CRUD-07, CRUD-08

**Success criteria:**
1. `nautobot_list_resources()` returns all resource types grouped by domain
2. `nautobot_resource_schema("cms.static_route")` returns field requirements per action
3. `nautobot_resource("device", "list")` dispatches correctly and returns results
4. CMS and core resources both work through the dispatcher
5. Invalid resource_type/action returns clear error message

---

### Phase 17: Server Consolidation & Test Suite

**Goal:** Replace 165 individual tools in `server.py` with 3 generic + ~15 composite tools. Update all tests.

**Requirements:** SVR-01, SVR-02, SVR-03, SVR-04, SVR-05, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05

**Success criteria:**
1. `server.py` reduced to ~300 lines (from 3,883)
2. `mcp.list_tools()` returns ~18-20 tools (from 165)
3. All composite tools preserved and passing tests
4. `test_server.py` updated for new interface
5. `test_registry.py` added with registry validation tests
6. All 293+ existing domain tests pass unchanged

---

### Phase 18: UAT Verification & Documentation

**Goal:** Validate the refactored MCP server against real Nautobot dev server and update documentation.

**Requirements:** UAT-01, UAT-02, UAT-03, UAT-04, UAT-05

**Success criteria:**
1. Smoke test script passes against `http://101.96.85.93`
2. `nautobot_list_resources()` returns expected domains from live server
3. Device, CMS static route, and BGP queries return real data
4. Composite tools (device_summary, bgp_summary) work end-to-end
5. Token count measurement shows ~89% reduction in tool definition overhead

---
*Last updated: 2026-03-24 — v1.3 roadmap created*
