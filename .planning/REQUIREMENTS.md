# Requirements: nautobot-mcp-cli v1.3

**Defined:** 2026-03-24
**Core Value:** AI agents can read and write Nautobot data through standardized MCP tools — with minimal context window overhead and maximum tool selection accuracy.

## v1.3 Requirements

Requirements for v1.3 Generic Resource Engine. Each maps to roadmap phases.

### Registry (REG)

- [ ] **REG-01**: Resource Registry module (`registry.py`) defines all resource types with supported actions, Pydantic models, and handler references
- [ ] **REG-02**: CMS resources auto-mapped from existing `CMS_ENDPOINTS` dictionary — no duplication of endpoint definitions
- [ ] **REG-03**: Core Nautobot resources (device, interface, IP, VLAN, prefix, circuit, tenant, location) mapped explicitly to existing domain functions
- [ ] **REG-04**: Each `ResourceDef` declares filter fields and required create fields for schema introspection
- [ ] **REG-05**: Registry validates at import time that all referenced handlers and models exist (fail-fast)

### Discovery (DISC)

- [ ] **DISC-01**: `nautobot_list_resources` tool returns catalog of all resource types grouped by domain, with their supported actions
- [ ] **DISC-02**: `nautobot_list_resources` supports optional `domain` filter (core, ipam, org, circuits, cms, golden_config)
- [ ] **DISC-03**: `nautobot_resource_schema` tool returns parameter schema for a resource type — separating required/optional fields per action (list, get, create, update, delete)
- [ ] **DISC-04**: `nautobot_resource_schema` excludes read-only fields (id, display, url, computed) from create/update schemas

### CRUD Dispatcher (CRUD)

- [ ] **CRUD-01**: `nautobot_resource` tool performs list/get/create/update/delete on any registered resource type
- [ ] **CRUD-02**: List action supports `filters: dict` passthrough and `limit` parameter with pagination
- [ ] **CRUD-03**: Get action supports lookup by `id` (UUID) or `filters` (e.g., name match)
- [ ] **CRUD-04**: Create action accepts `data: dict` and passes to the appropriate domain create function
- [ ] **CRUD-05**: Update action requires `id` + `data: dict` and passes to appropriate domain update function
- [ ] **CRUD-06**: Delete action requires `id` and passes to appropriate domain delete function
- [ ] **CRUD-07**: Invalid `resource_type` or `action` returns clear error with valid options listed
- [ ] **CRUD-08**: CMS resources dispatch through generic `cms_list/get/create/update/delete` helpers; core resources dispatch through explicit domain functions

### Server Consolidation (SVR)

- [ ] **SVR-01**: `server.py` reduced from 3,883 lines to ~300 lines with 3 generic tools + ~15 composite tools
- [ ] **SVR-02**: All 165 individual `@mcp.tool` CRUD wrappers removed (clean break, no aliases)
- [ ] **SVR-03**: ~15 composite workflow tools preserved unchanged (device_summary, bgp_summary, etc.)
- [ ] **SVR-04**: Error handling via existing `handle_error` function unchanged
- [ ] **SVR-05**: `get_client()` singleton pattern unchanged

### Testing (TEST)

- [ ] **TEST-01**: Registry completeness test — 100% of old CRUD operations covered by registry entries
- [ ] **TEST-02**: `test_server.py` updated to test new tool interface (3 generic + composites)
- [ ] **TEST-03**: New `test_registry.py` with tests for registry validation, action dispatch, schema generation
- [ ] **TEST-04**: All existing domain module tests pass unchanged (293+ tests)
- [ ] **TEST-05**: Tool count assertion updated from ~165 to ~18-20

### UAT Verification (UAT)

- [ ] **UAT-01**: Smoke test script for list/get operations against Nautobot dev server (http://101.96.85.93)
- [ ] **UAT-02**: Verify `nautobot_list_resources()` returns all expected domains and types from live server
- [ ] **UAT-03**: Verify `nautobot_resource("device", "list")` returns real device data from live server
- [ ] **UAT-04**: Verify `nautobot_resource("cms.static_route", "list", filters={"device": "..."})` works with real CMS data
- [ ] **UAT-05**: Verify composite tools (device_summary, bgp_summary) still work end-to-end

## Future Requirements

### Multi-Domain Scaling

- **SCALE-01**: When adding a new domain, only registry entries needed (zero new `@mcp.tool` definitions)
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
| Dynamic tool generation from registry | Harder to debug, IDE unfriendly |
| GraphQL integration | Different query paradigm, not needed |
| Real-time LLM caching | Stale data risk, context bloat |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REG-01 | Phase 15 | Pending |
| REG-02 | Phase 15 | Pending |
| REG-03 | Phase 15 | Pending |
| REG-04 | Phase 15 | Pending |
| REG-05 | Phase 15 | Pending |
| DISC-01 | Phase 16 | Pending |
| DISC-02 | Phase 16 | Pending |
| DISC-03 | Phase 16 | Pending |
| DISC-04 | Phase 16 | Pending |
| CRUD-01 | Phase 16 | Pending |
| CRUD-02 | Phase 16 | Pending |
| CRUD-03 | Phase 16 | Pending |
| CRUD-04 | Phase 16 | Pending |
| CRUD-05 | Phase 16 | Pending |
| CRUD-06 | Phase 16 | Pending |
| CRUD-07 | Phase 16 | Pending |
| CRUD-08 | Phase 16 | Pending |
| SVR-01 | Phase 17 | Pending |
| SVR-02 | Phase 17 | Pending |
| SVR-03 | Phase 17 | Pending |
| SVR-04 | Phase 17 | Pending |
| SVR-05 | Phase 17 | Pending |
| TEST-01 | Phase 17 | Pending |
| TEST-02 | Phase 17 | Pending |
| TEST-03 | Phase 17 | Pending |
| TEST-04 | Phase 17 | Pending |
| TEST-05 | Phase 17 | Pending |
| UAT-01 | Phase 18 | Pending |
| UAT-02 | Phase 18 | Pending |
| UAT-03 | Phase 18 | Pending |
| UAT-04 | Phase 18 | Pending |
| UAT-05 | Phase 18 | Pending |

**Coverage:**
- v1.3 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after initial definition*
