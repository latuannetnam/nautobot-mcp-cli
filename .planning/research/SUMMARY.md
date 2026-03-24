# Project Research Summary

**Project:** nautobot-mcp-cli
**Domain:** MCP Server API Bridge for Nautobot
**Researched:** 2026-03-24
**Confidence:** HIGH

## Executive Summary

The API Bridge architecture replaces 165 individual MCP tools with 3 universal tools — `nautobot_api_catalog` (discovery), `call_nautobot` (universal CRUD), and `run_workflow` (server-side composites) — achieving 96% token reduction (50K → 1.8K tokens) in agent context windows. This addresses the critical problem of agent accuracy degradation when tool count exceeds 25.

The recommended approach builds a thin Bridge Layer between the existing MCP server and the unchanged domain modules. Zero new dependencies are needed — the existing stack (FastMCP, pynautobot, Pydantic, DiffSync) is fully reused. The primary risks are agent endpoint confusion (mitigated by catalog validation + error hints) and workflow parameter inconsistency (mitigated by parameter normalization in the workflow registry).

## Key Findings

### Recommended Stack

No new dependencies. The API Bridge is a structural refactoring, not a technology change.

**Reused technologies:**
- FastMCP 3.0: MCP server framework — component versioning, OpenTelemetry
- pynautobot 2.3: Dynamic endpoint discovery, pagination — powers `call_nautobot`
- CMS_ENDPOINTS registry: Dynamic CMS plugin discovery — powers `nautobot_api_catalog`

### Expected Features

**Must have (table stakes):**
- API catalog with domain filtering (dcim, ipam, cms, workflows)
- Universal CRUD dispatcher with endpoint validation
- Auto-pagination and device name → UUID resolution
- Composite workflows (BGP summary, routing table, firewall summary, etc.)
- Structured error messages with hints

**Should have (differentiators):**
- Hybrid catalog (static core + dynamic CMS discovery)
- 96% token reduction in agent context
- Agent skills as distributed files (cross-MCP orchestration)

**Defer (v2+):**
- OpenAPI-based dynamic catalog enrichment
- Multi-server MCP gateway
- Tool usage analytics

### Architecture Approach

4-layer architecture: MCP Server (3 tools) → Bridge Layer (catalog + bridge + workflows) → Domain Layer (unchanged) → Client Layer (unchanged). The Bridge Layer is the only new code; everything below it remains untouched.

**Major components:**
1. Catalog Engine — static JSON + dynamic CMS_ENDPOINTS, ~150 LOC
2. REST Bridge — endpoint routing + validation + pagination, ~200 LOC
3. Workflow Registry — dict mapping name → function, ~100 LOC
4. Server entry — 3 FastMCP tool decorators, ~200 LOC

### Critical Pitfalls

1. **Agent endpoint confusion** — agents must construct endpoint strings from catalog; mitigate with validation + "did you mean?" hints
2. **Domain test breakage** — bridge must never modify domain function signatures; mitigate by running all 293 tests after each change
3. **CMS routing mismatch** — CMS_ENDPOINTS format → catalog entry mapping must be tested independently
4. **Workflow parameter inconsistency** — domain functions use different param names; mitigate with normalization layer
5. **Agent context loss** — catalog fades from context in long conversations; mitigate with inline endpoint references in skills
6. **Catalog bloat** — resist temptation to add schemas/types; keep response < 1500 tokens

## Implications for Roadmap

### Phase 15: Catalog Engine & Core Endpoints
**Rationale:** Discovery must come first — agents need to know what's available before calling it
**Delivers:** `nautobot_api_catalog` tool + static core endpoint JSON + dynamic CMS discovery
**Addresses:** Catalog, discovery, domain filtering
**Avoids:** Pitfall 1 (endpoint confusion), Pitfall 6 (catalog bloat)

### Phase 16: REST Bridge & Universal CRUD
**Rationale:** Once catalog exists, agents need to execute operations; depends on catalog for validation
**Delivers:** `call_nautobot` tool + endpoint routing + validation + pagination + error hints
**Addresses:** CRUD operations, endpoint validation, error handling
**Avoids:** Pitfall 2 (domain test breakage), Pitfall 3 (CMS routing failure)

### Phase 17: Workflow Registry & Server Consolidation
**Rationale:** Composite workflows wrap existing domain functions; depends on bridge being stable
**Delivers:** `run_workflow` tool + workflow registry + rewritten `server.py` (3 tools)
**Addresses:** Composite workflows, server consolidation, parameter normalization
**Avoids:** Pitfall 4 (workflow param mismatch)

### Phase 18: Agent Skills, Tests & UAT
**Rationale:** Skills and documentation update last, once the API is stable; UAT validates everything
**Delivers:** Updated skills, test suite, UAT against Nautobot dev server
**Addresses:** Skills migration, test coverage, live validation
**Avoids:** Pitfall 5 (agent context loss)

### Phase Ordering Rationale

- Catalog → Bridge → Workflows → Skills follows dependency chain
- Each phase builds on the previous, minimizing rework
- Domain modules unchanged throughout = zero regression risk to existing functionality
- Skills update last because they reference the stable 3-tool API

### Research Flags

Phases with standard patterns (skip research-phase):
- **Phase 15:** Static JSON + dict lookup — well-understood pattern
- **Phase 16:** Endpoint routing — straightforward dispatch logic
- **Phase 17:** Registry pattern — simple dict-based dispatch
- **Phase 18:** Skills rewrite + testing — mechanical update

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero changes needed, all proven |
| Features | HIGH | Design doc approved, scope well-defined |
| Architecture | HIGH | 4-layer design clear, domain modules unchanged |
| Pitfalls | HIGH | Based on actual codebase analysis + research |

**Overall confidence:** HIGH

### Gaps to Address

- CMS_ENDPOINTS mapper needs testing before Phase 16 (format compatibility)
- Workflow parameter names need audit across all domain functions during Phase 17

## Sources

### Primary (HIGH confidence)
- API Bridge Design v2 (internal) — approved architecture
- Existing codebase analysis — CMS_ENDPOINTS format, domain function signatures
- pynautobot documentation — dynamic endpoint generation, pagination

### Secondary (MEDIUM confidence)
- FastMCP 3.0 release notes — component versioning, OpenTelemetry
- LLM tool selection research — accuracy thresholds, context window impact

---
*Research completed: 2026-03-24*
*Ready for roadmap: yes*
