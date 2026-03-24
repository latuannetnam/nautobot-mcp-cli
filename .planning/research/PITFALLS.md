# Pitfalls Research

**Domain:** MCP Tool Consolidation / Generic Resource Engine
**Researched:** 2026-03-24
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Incomplete Registry Coverage

**What goes wrong:**
Some resource types are missing from the registry, causing agents to get "unknown resource_type" errors for operations that previously worked.

**Why it happens:**
The current 165 tools were built incrementally over 3 milestones. It's easy to miss some during the mapping, especially edge cases like read-only endpoints or M2M traversals.

**How to avoid:**
- Build an automated test that extracts ALL current tool names from `server.py` (before refactor)
- Map each to its registry entry
- Assert 100% coverage (every operation available pre-refactor must be available post-refactor)

**Warning signs:**
Agent errors like "Resource type 'X' not found" for operations that worked before.

**Phase to address:** Phase 15 (Registry Foundation)

---

### Pitfall 2: Filter Parameter Mismatch

**What goes wrong:**
The generic `filters: dict` parameter accepts arbitrary keys, but domain functions expect specific parameter names. For example, `list_devices` expects `name`, `location`, `role` — but the agent passes `{"device_name": "..."}` because that's what another endpoint uses.

**Why it happens:**
Different domain modules use different parameter naming conventions. CMS uses `device_name`, core uses `name` or `device`.

**How to avoid:**
- Document filter fields per resource type in `nautobot_resource_schema`
- Normalize common filter names (e.g., map `device_name` → `device` for core endpoints)
- Add validation in the dispatcher that checks filter keys against allowed fields

**Warning signs:**
Agents getting empty results when they should get data, because filters silently don't match.

**Phase to address:** Phase 15 (Registry) + Phase 16 (Server Refactor)

---

### Pitfall 3: Breaking Composite Tool Dependencies

**What goes wrong:**
Composite tools like `nautobot_device_summary` internally call domain functions (e.g., `devices.get_device()`, `devices.list_interfaces()`). If the refactor changes how the client is passed or initialized, composites break silently.

**Why it happens:**
Composite tools import domain functions directly and use the shared `get_client()` singleton. Changes to client initialization flow affect all tools.

**How to avoid:**
- Keep `get_client()` function signature unchanged
- Run all existing composite tool tests before and after refactor
- Don't change domain function signatures — the dispatcher adapts to them, not vice versa

**Warning signs:**
Composite tools returning errors or empty results when the underlying data hasn't changed.

**Phase to address:** Phase 16 (Server Refactor)

---

### Pitfall 4: CMS CRUD vs Core CRUD Asymmetry

**What goes wrong:**
CMS resources use `cms_list/cms_get/cms_create/cms_update/cms_delete` (generic functions from `cms/client.py`), while core resources use individually written functions (`devices.list_devices`, `interfaces.list_interfaces`). The dispatcher must handle both.

**Why it happens:**
CMS was designed later with a generic pattern; core was built earlier with explicit functions.

**How to avoid:**
- ResourceDef has a `handler_style` field: `"cms_generic"` vs `"explicit"`
- CMS dispatches through `cms_list(endpoint_name, client, model_cls, ...)`
- Core dispatches through `domain_module.function(client, ...)`
- Both return the same shape: `dict` with `count` and `results` for list, or flat dict for get

**Warning signs:**
CMS resources work but core resources don't (or vice versa).

**Phase to address:** Phase 15 (Registry Design)

---

### Pitfall 5: Schema Explosion for Create/Update

**What goes wrong:**
`nautobot_resource_schema("cms.static_route")` returns a massive list of fields because Pydantic models include all optional fields. Agent gets overwhelmed or hallucinates field names.

**Why it happens:**
Pydantic models were designed for response serialization (read), not for input (create/update). Many fields are read-only (id, display, url) or computed (nexthops, neighbor_count).

**How to avoid:**
- Separate read fields from write fields in schema response
- Mark required vs optional clearly
- Exclude read-only fields (id, display, url, computed)
- Show only the fields that the create/update API actually accepts

**Warning signs:**
Agents passing `id`, `display`, or computed fields in create requests and getting errors.

**Phase to address:** Phase 15 (Registry) — schema design

---

### Pitfall 6: UAT Against Live Server Flaky Tests

**What goes wrong:**
UAT tests against Nautobot dev server are flaky because data changes between runs, server is down, or API rate limits are hit.

**Why it happens:**
External dependency in test suite. Dev server data is not under test control.

**How to avoid:**
- Use read-only operations for UAT (list, get) — don't modify dev data
- Create a specific test device/resource on dev and target it
- Tag UAT tests separately so they don't fail CI
- Write a "smoke test" script that's run manually, not in pytest

**Warning signs:**
Tests pass locally but fail in CI; tests pass one day, fail the next.

**Phase to address:** Phase 18 (UAT Verification)

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hard-coded resource_type strings | Fast development | Typos cause runtime errors | Never — use constants or enum |
| Skip schema for some resources | Faster delivery | Agent confusion on those types | Only for read-only resources |
| Copy-paste filter handling | Works for first 5 types | Inconsistent behavior | Never — extract to helper |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| CMS `cms_create` | Sending full Pydantic model dict | Send only API-accepted fields |
| Core `list_devices` | Passing `device_name` instead of `name` | Normalize to API field names |
| `get_client()` | Calling in registry definition | Call lazily in dispatcher |

## "Looks Done But Isn't" Checklist

- [ ] **Registry completeness:** Count resources in registry, compare to old tool count — 100% CRUD ops covered?
- [ ] **Schema accuracy:** `nautobot_resource_schema` returns correct required/optional fields for each resource?
- [ ] **Filter fields documented:** Every resource type lists its valid filter fields?
- [ ] **Error messages useful:** "Resource type 'X' not found" message includes suggestion of similar types?
- [ ] **Composite tools unchanged:** All ~15 composite tools still pass their original tests?
- [ ] **Token count verified:** Measure actual token consumption of new tool definitions vs old?

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-----------------|--------------|
| Incomplete registry coverage | Phase 15 | Automated test: old tools → new registry 100% |
| Filter parameter mismatch | Phase 15 + 16 | Schema shows valid filters per type |
| Composite tool breakage | Phase 16 | Run existing test suite unchanged |
| CMS/Core asymmetry | Phase 15 | Both CMS and core types pass same dispatcher |
| Schema explosion | Phase 15 | Schema excludes read-only fields |
| UAT flakiness | Phase 18 | Separate UAT from unit tests |

---
*Pitfalls research for: MCP Tool Consolidation*
*Researched: 2026-03-24*
