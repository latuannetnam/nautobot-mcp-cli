# Feature Research

**Domain:** MCP Server API Bridge for Nautobot
**Researched:** 2026-03-24
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features agents expect from a Nautobot MCP server. Missing these = agents can't do their job.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| API discovery / catalog | Agent needs to know what endpoints exist before calling them | MEDIUM | Hybrid: static core + dynamic CMS plugin discovery |
| Universal CRUD (list/get/create/update/delete) | Core operations on any Nautobot resource | MEDIUM | Route `/api/*` → pynautobot, `cms:*` → CMS helpers |
| Endpoint validation | Agent needs clear errors when using wrong endpoint/method | LOW | Check against catalog before dispatching |
| Auto-pagination | Agent shouldn't manually page through results | LOW | Already handled by pynautobot; expose via `limit` param |
| Device name → UUID resolution | CMS endpoints require device UUID, agents know names | LOW | Already implemented in existing domain modules |
| Structured error messages | Agent needs to recover from errors without guessing | LOW | HTTP status → actionable hint mapping |
| Composite workflows (BGP summary, routing table, etc.) | N+1 query patterns must be server-side for performance | LOW | Already implemented — just wrap in workflow registry |

### Differentiators (Competitive Advantage)

Features that make this MCP server better than raw API access.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Domain-grouped catalog | Agent can discover by domain (dcim, ipam, cms, workflows) | LOW | Better than flat endpoint list |
| Workflow registry with descriptions | Agent chooses workflows by intent, not function name | LOW | Each workflow has params + description |
| Hybrid catalog (static + dynamic CMS) | Zero-maintenance when CMS plugin adds endpoints | MEDIUM | Reads `CMS_ENDPOINTS` at runtime |
| Agent skills as distributed files | Cross-MCP orchestration (nautobot + jmcp) stays agent-side | LOW | Existing skills adapted to 3-tool API |
| 96% token reduction | 50K → 1.8K tokens per request for tool descriptions | HIGH (impact) | The core value proposition |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Dynamic tool generation from catalog | "Auto-create one tool per endpoint" | Recreates the 165-tool problem, harder to debug | Universal `call_nautobot` dispatcher |
| Real-time schema introspection from Nautobot | "Fetch field names/types live" | Adds latency, stale risk, complexity | Static catalog with curated field lists |
| Backwards-compatible aliases | "Keep old tool names as aliases" | Doubles tool count, defeats purpose | Clean break + updated skills |
| Caching API responses | "Cache device lists for speed" | Stale data risk in network context | Fresh queries; agent can re-query cheaply |
| GraphQL support | "More efficient than REST for nested data" | pynautobot doesn't support it, different paradigm | REST + composite workflows for N+1 patterns |

## Feature Dependencies

```
nautobot_api_catalog (discovery)
    └──required by──> call_nautobot (needs valid endpoints)
    └──required by──> run_workflow (catalog lists available workflows)

call_nautobot (CRUD)
    └──used by──> run_workflow (workflows call domain functions internally)

Domain modules (devices.py, cms/routing.py, etc.)
    └──unchanged, used by──> run_workflow (wrapper functions)
    └──unchanged, used by──> call_nautobot (core endpoint routing)

Agent skills (distributed files)
    └──references──> all 3 MCP tools
    └──references──> jmcp tools (cross-MCP orchestration)
```

### Dependency Notes

- **`nautobot_api_catalog` required first:** Agent must discover endpoints before calling them
- **`call_nautobot` depends on catalog:** Validates endpoints against catalog registry
- **`run_workflow` wraps domain functions:** No changes to domain modules needed
- **Skills depend on all 3 tools:** Skills must be updated last, after API is stable

## MVP Definition

### Launch With (v1.3)

- [x] `nautobot_api_catalog` — endpoint + workflow discovery with domain filter
- [x] `call_nautobot` — universal CRUD for core + CMS + plugin endpoints
- [x] `run_workflow` — server-side composite workflows (10 workflows)
- [x] Updated agent skills referencing 3-tool API
- [x] Tests validating tool dispatch
- [x] UAT against Nautobot dev server

### Add After Validation (v1.x)

- [ ] OpenAPI-based dynamic catalog enrichment — fetch field types from Nautobot spec
- [ ] Tool usage analytics — track which endpoints agents call most
- [ ] Streaming responses for large result sets

### Future Consideration (v2+)

- [ ] Multi-server MCP gateway (nautobot + jmcp + future servers as one)
- [ ] Agent-adaptive catalog (hide endpoints agent hasn't needed)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| API catalog with domain filter | HIGH | LOW | P1 |
| Universal CRUD dispatcher | HIGH | MEDIUM | P1 |
| Workflow registry | HIGH | LOW | P1 |
| Endpoint validation + error hints | HIGH | LOW | P1 |
| Auto-pagination | HIGH | LOW (exists) | P1 |
| Device name → UUID resolution | MEDIUM | LOW (exists) | P1 |
| Updated agent skills | MEDIUM | LOW | P1 |
| Domain-grouped catalog | MEDIUM | LOW | P2 |
| Dynamic CMS discovery | MEDIUM | MEDIUM | P1 |

## Sources

- API Bridge Design v2 (internal) — tool classification, workflow analysis
- LLM tool selection research — accuracy drops >25 tools, context window impact
- FastMCP 3.0 best practices — tool design for outcomes, not atomic operations
- pynautobot documentation — dynamic endpoint generation, pagination

---
*Feature research for: MCP Server API Bridge for Nautobot*
*Researched: 2026-03-24*
