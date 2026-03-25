# Roadmap: nautobot-mcp-cli

**Created:** 2026-03-17
**Granularity:** Coarse (3-5 phases per milestone)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-18) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Agent-Native MCP Tools** — Phases 5-7 (shipped 2026-03-20) — [Archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Juniper CMS Model MCP Tools** — Phases 8-14 (shipped 2026-03-21) — [Archive](milestones/v1.2-ROADMAP.md)
- ❌ **v1.3 Generic Resource Engine** — REJECTED (superseded by API Bridge design, 2026-03-24)
- ✅ **v1.3 API Bridge MCP Server** — Phases 15-18 (shipped 2026-03-25) — [Archive](milestones/v1.3-ROADMAP.md)
- 🔵 **v1.4 Operational Robustness** — Phases 19-22 (in progress)

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

### v1.4 Operational Robustness (Phases 19-22)

- [x] **Phase 19: Partial Failure Resilience** — Composite workflows gracefully degrade — completed 2026-03-25
- [ ] **Phase 20: Catalog Accuracy & Endpoint Dereference** — Fix filter contracts + URL follow
- [ ] **Phase 21: Workflow Contracts & Error Diagnostics** — Fix param contracts + enrich errors
- [ ] **Phase 22: Response Ergonomics & UAT** — Summary modes, size metadata, live validation

#### Phase 19: Partial Failure Resilience

**Goal:** Composite workflows return partial data with warnings instead of all-or-nothing failure.

**Requirements:** PFR-01, PFR-02, PFR-03, PFR-04

**Files:** `nautobot_mcp/cms/routing.py`, `nautobot_mcp/cms/firewalls.py`, `nautobot_mcp/cms/interfaces.py`, `nautobot_mcp/workflows.py`

**Success criteria:**
1. `bgp_summary` returns groups+neighbors when policy association query fails, with `status: "partial"` and `warnings` list
2. `routing_table`, `firewall_summary`, `interface_detail` all implement graceful degradation
3. Response envelope includes `warnings` array with per-child failure details
4. Existing tests pass; new tests validate partial failure paths

#### Phase 20: Catalog Accuracy & Endpoint Dereference

**Goal:** Fix false filter advertisement and enable linked object URL follow.

**Requirements:** CAT-07, CAT-08, CAT-09, DRF-01, DRF-02, DRF-03

**Files:** `nautobot_mcp/catalog/cms_discovery.py`, `nautobot_mcp/bridge.py`, `tests/test_catalog.py`, `tests/test_bridge.py`

**Success criteria:**
1. Per-endpoint filter registry replaces domain-level `CMS_DOMAIN_FILTERS`
2. `juniper_bgp_neighbors` catalog entry shows `group` filter (not `device`)
3. `/api/dcim/device-types/<uuid>/` resolves correctly through bridge
4. Tests validate per-endpoint filter accuracy and UUID path normalization

#### Phase 21: Workflow Contracts & Error Diagnostics

**Goal:** Fix param contract bugs and enrich error messages with actionable context.

**Requirements:** WFC-01, WFC-02, WFC-03, ERR-01, ERR-02, ERR-03, ERR-04

**Files:** `nautobot_mcp/workflows.py`, `nautobot_mcp/client.py`, `nautobot_mcp/exceptions.py`, `tests/test_workflows.py`

**Success criteria:**
1. `verify_data_model` requires `parsed_config` and applies `ParsedConfig.model_validate` transform
2. Workflow registry performs startup self-check for required-param mismatches
3. 400 errors surface field-level validation details (not generic "check server logs")
4. Composite workflow errors show which child operation failed via `origin` field

#### Phase 22: Response Ergonomics & UAT

**Goal:** Add summary modes for large-payload workflows and validate all fixes end-to-end.

**Requirements:** RSP-01, RSP-02, RSP-03

**Files:** `nautobot_mcp/cms/interfaces.py`, `nautobot_mcp/workflows.py`, `tests/`

**Success criteria:**
1. `interface_detail` supports `detail=False` summary mode (counts only, no nested objects)
2. Response envelopes include `response_size_bytes` metadata
3. Composite workflows accept optional `limit` parameter
4. All v1.4 UAT tests pass against Nautobot dev server

---
*Last updated: 2026-03-25 — v1.4 Operational Robustness milestone roadmap created*
