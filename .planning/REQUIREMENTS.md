# Requirements: nautobot-mcp-cli v1.3

**Defined:** 2026-03-24
**Core Value:** AI agents can read and write Nautobot data through 3 universal MCP tools — with 96% less context window overhead and dramatically improved tool selection accuracy.

## v1.3 Requirements

Requirements for v1.3 API Bridge MCP Server. Each maps to roadmap phases.

### Catalog Engine (CAT)

- [x] **CAT-01**: `nautobot_api_catalog` tool returns all available endpoints and workflows grouped by domain (dcim, ipam, circuits, tenancy, cms, workflows)
- [x] **CAT-02**: Catalog supports optional `domain` filter to return only one domain's entries
- [x] **CAT-03**: Core endpoints (dcim, ipam, circuits, tenancy) defined in static JSON with endpoint path, methods, common filters, and description
- [x] **CAT-04**: CMS plugin endpoints auto-discovered from `CMS_ENDPOINTS` registry at runtime — zero duplication
- [x] **CAT-05**: Workflow entries listed from `WORKFLOW_REGISTRY` with params and description
- [x] **CAT-06**: Catalog response stays under 1500 tokens (concise descriptions, no schema/types)

### REST Bridge (BRG)

- [ ] **BRG-01**: `call_nautobot` tool executes any CRUD operation by specifying endpoint, method, params/data, and optional id
- [ ] **BRG-02**: Endpoint routing: `/api/*` → pynautobot core accessor, `cms:*` → CMS plugin helpers, `plugins:*` → plugin accessor
- [ ] **BRG-03**: Endpoint validated against catalog before dispatch — invalid endpoint returns clear error with "did you mean X?" hint
- [ ] **BRG-04**: Auto-pagination for GET operations — follows `next` links up to `limit` param (default 50)
- [ ] **BRG-05**: Device name → UUID auto-resolution for CMS endpoints requiring device filter
- [ ] **BRG-06**: HTTP error translation: 404/400/401/500 → structured error with actionable hints
- [ ] **BRG-07**: `id` parameter support for single-object operations (GET by UUID, PATCH, DELETE)

### Workflow Registry (WFL)

- [ ] **WFL-01**: `run_workflow` tool dispatches named workflows with params dict
- [ ] **WFL-02**: Workflow registry maps workflow name → function + params schema + description
- [ ] **WFL-03**: All N+1 query patterns preserved as workflows: `bgp_summary`, `routing_table`, `firewall_summary`, `interface_detail`
- [ ] **WFL-04**: All complex business logic preserved as workflows: `onboard_config`, `compare_device`, `verify_data_model`, `verify_compliance`, `compare_bgp`, `compare_routes`
- [ ] **WFL-05**: Parameter normalization handles domain function inconsistencies (e.g., `device` vs `device_name`)
- [ ] **WFL-06**: Invalid workflow name returns clear error listing available workflows

### Server Consolidation (SVR)

- [ ] **SVR-01**: `server.py` reduced from 3,883 lines / 165 tools to ~200 lines / 3 tools
- [ ] **SVR-02**: All 165 individual `@mcp.tool` CRUD wrappers removed (clean break, no aliases)
- [ ] **SVR-03**: Error handling via existing `handle_error` function unchanged
- [ ] **SVR-04**: `get_client()` singleton pattern unchanged

### Agent Skills (SKL)

- [ ] **SKL-01**: All agent skills updated to reference new 3-tool API (`call_nautobot`, `run_workflow`, `nautobot_api_catalog`)
- [ ] **SKL-02**: Skills embed relevant endpoint references inline (not requiring catalog lookup)
- [ ] **SKL-03**: `cms-device-audit` skill updated for cross-MCP orchestration via new API
- [ ] **SKL-04**: `onboard-router-config` skill updated to use `run_workflow("onboard_config", ...)`
- [ ] **SKL-05**: `verify-compliance` skill updated to use `run_workflow("verify_compliance", ...)`

### Testing & UAT (TST)

- [ ] **TST-01**: All existing 293+ domain module tests pass unchanged
- [x] **TST-02**: New `test_catalog.py` with catalog completeness + domain filter tests
- [ ] **TST-03**: New `test_bridge.py` with endpoint routing + validation + error hint tests
- [ ] **TST-04**: New `test_workflows.py` with workflow dispatch + parameter normalization tests
- [ ] **TST-05**: Updated `test_server.py` for new 3-tool interface
- [ ] **TST-06**: UAT smoke test against Nautobot dev server (http://101.96.85.93)
- [ ] **TST-07**: Verify `nautobot_api_catalog()` returns expected domains from live server
- [ ] **TST-08**: Verify `call_nautobot("/api/dcim/devices/", "GET")` returns real device data

## Future Requirements

### Multi-Domain Scaling

- **SCALE-01**: When adding a new domain, only catalog entries needed (zero new `@mcp.tool` definitions)
- **SCALE-02**: Split into multiple MCP sub-servers when tool count exceeds 40

### Extended Tooling

- **EXT-01**: Multi-vendor config parsers (Cisco IOS/IOS-XE, Arista EOS)
- **EXT-02**: Bulk device onboarding (batch config files)
- **EXT-03**: Config remediation suggestions based on drift reports

## Out of Scope

| Feature | Reason |
|---------|--------|
| CLI refactoring | CLI calls domain modules directly — unaffected by MCP layer changes |
| Backwards-compatible tool aliases | Defeats purpose; would double tool count |
| Dynamic tool generation from catalog | Harder to debug, IDE unfriendly |
| GraphQL integration | Different query paradigm, not needed |
| Real-time LLM caching | Stale data risk, context bloat |
| Field-level schema in catalog | Bloats response; agents learn params from skills |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CAT-01 | Phase 15 | Complete |
| CAT-02 | Phase 15 | Complete |
| CAT-03 | Phase 15 | Complete |
| CAT-04 | Phase 15 | Complete |
| CAT-05 | Phase 15 | Complete |
| CAT-06 | Phase 15 | Complete |
| BRG-01 | Phase 16 | Pending |
| BRG-02 | Phase 16 | Pending |
| BRG-03 | Phase 16 | Pending |
| BRG-04 | Phase 16 | Pending |
| BRG-05 | Phase 16 | Pending |
| BRG-06 | Phase 16 | Pending |
| BRG-07 | Phase 16 | Pending |
| WFL-01 | Phase 17 | Pending |
| WFL-02 | Phase 17 | Pending |
| WFL-03 | Phase 17 | Pending |
| WFL-04 | Phase 17 | Pending |
| WFL-05 | Phase 17 | Pending |
| WFL-06 | Phase 17 | Pending |
| SVR-01 | Phase 17 | Pending |
| SVR-02 | Phase 17 | Pending |
| SVR-03 | Phase 17 | Pending |
| SVR-04 | Phase 17 | Pending |
| SKL-01 | Phase 18 | Pending |
| SKL-02 | Phase 18 | Pending |
| SKL-03 | Phase 18 | Pending |
| SKL-04 | Phase 18 | Pending |
| SKL-05 | Phase 18 | Pending |
| TST-01 | Phase 16 | Pending |
| TST-02 | Phase 15 | Complete |
| TST-03 | Phase 16 | Pending |
| TST-04 | Phase 17 | Pending |
| TST-05 | Phase 17 | Pending |
| TST-06 | Phase 18 | Pending |
| TST-07 | Phase 18 | Pending |
| TST-08 | Phase 18 | Pending |

**Coverage:**
- v1.3 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after API Bridge milestone definition*
