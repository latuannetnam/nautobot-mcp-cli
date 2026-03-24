# Feature Research

**Domain:** MCP Tool Consolidation / Generic Resource Engine
**Researched:** 2026-03-24
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Must Have for v1.3)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Resource catalog discovery | Agent needs to know what resources exist before acting | LOW | `nautobot_list_resources` — returns all resource types |
| Schema introspection | Agent needs field requirements before create/update | MEDIUM | `nautobot_resource_schema` — dynamic from Pydantic models |
| Universal CRUD dispatcher | Core value prop — one tool for all entities | HIGH | `nautobot_resource` — dispatch to domain functions |
| Preserved composite tools | Multi-entity joins can't be expressed as simple CRUD | LOW | Keep ~15 existing tools unchanged |
| Action validation | Reject invalid actions before hitting API | LOW | Enum-based action checking in dispatcher |
| Filter passthrough | Agents need to filter resources (e.g., device_name) | MEDIUM | Forward filters dict to domain functions |
| Structured error handling | Agents need clear errors to recover | LOW | Already have `handle_error` — reuse |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Domain-grouped catalog | Agent sees resources organized by domain, not a flat list | LOW | `nautobot_list_resources(domain="cms")` |
| Inline child nesting | Routes include nexthops, interfaces include families | LOW | Already implemented in v1.2 models |
| Zero-new-dependency growth | Adding domains adds registry entries, not tools | LOW | Architecture guarantee |
| Auto-generated schema | `nautobot_resource_schema` builds field info from Pydantic model | MEDIUM | Uses `model_fields` introspection |

### Anti-Features (Don't Build)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Dynamic `@mcp.tool` generation | "Auto-register tools from registry" | Harder to debug, IDE can't inspect | Static 3 tools, internal dispatch |
| GraphQL dispatcher | "Use Nautobot's GraphQL" | Different query model, parallel complexity | REST API is reliable and consistent |
| Backwards-compatible aliases | "Keep old tool names" | Doubles tool count, defeats purpose | Clean break + comprehensive testing |
| LLM-side caching | "Cache responses in context" | Stale data risk, context bloat | Let agent re-query as needed |

## Feature Dependencies

```
[nautobot_list_resources] ← requires ← [Resource Registry]
[nautobot_resource_schema] ← requires ← [Resource Registry]
[nautobot_resource] ← requires ← [Resource Registry]
                    ← requires ← [Domain Modules (unchanged)]

[Resource Registry] ← requires ← [CMS_ENDPOINTS (already exists)]
                    ← requires ← [Core domain function mapping (new)]
```

### Dependency Notes

- **All 3 tools require Resource Registry:** Registry must be built first
- **Registry requires CMS_ENDPOINTS:** Already exists in `cms/client.py`
- **Composite tools are independent:** No changes needed

## Feature Prioritization Matrix

| Feature | User Value | Cost | Priority |
|---------|------------|------|----------|
| Resource Registry module | HIGH | MEDIUM | **P1** |
| `nautobot_resource` dispatcher | HIGH | HIGH | **P1** |
| `nautobot_list_resources` | HIGH | LOW | **P1** |
| `nautobot_resource_schema` | MEDIUM | MEDIUM | **P1** |
| Preserved composite tools | HIGH | LOW | **P1** |
| Domain-grouped catalog | MEDIUM | LOW | **P2** |
| UAT against Nautobot dev | HIGH | MEDIUM | **P1** |

---
*Feature research for: MCP Tool Consolidation*
*Researched: 2026-03-24*
