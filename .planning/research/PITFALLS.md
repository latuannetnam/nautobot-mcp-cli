# Pitfalls Research

**Domain:** MCP Server API Bridge for Nautobot
**Researched:** 2026-03-24
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Agent Can't Find the Right Endpoint

**What goes wrong:**
Agent calls `call_nautobot` with an invalid or misspelled endpoint string. Without 165 typed tool names, the agent must construct endpoint strings from catalog knowledge.

**Why it happens:**
Agents are used to typed tool names (e.g., `nautobot_list_devices`). With `call_nautobot(endpoint="/api/dcim/devices/")`, they must remember the exact endpoint path.

**How to avoid:**
1. `nautobot_api_catalog` returns exact endpoint strings agents should copy-paste
2. `call_nautobot` validates endpoint against catalog and returns "did you mean X?" hints
3. Agent skills include the exact `call_nautobot` invocation syntax

**Warning signs:**
Agent repeatedly calls `call_nautobot` with wrong endpoints, or asks user "what endpoint should I use?"

**Phase to address:** Phase 15 (Catalog Engine) — validation + error hints

---

### Pitfall 2: Breaking Existing Domain Module Tests

**What goes wrong:**
Refactoring `server.py` accidentally modifies domain module interfaces. Existing 293 domain tests start failing.

**Why it happens:**
Developer changes domain function signatures to "fit" the new bridge, or accidentally imports that create circular dependencies.

**How to avoid:**
1. Domain modules are 100% unchanged — zero modifications to function signatures
2. Bridge layer wraps domain functions, never modifies them
3. Run full test suite (`pytest`) after each change
4. Bridge uses existing function signatures exactly as they are

**Warning signs:**
Any domain module test failure = bridge is leaking into domain layer.

**Phase to address:** Phase 16 (REST Bridge) — test-first validation

---

### Pitfall 3: CMS Endpoint Discovery Fails Silently

**What goes wrong:**
`nautobot_api_catalog` shows CMS endpoints, but `call_nautobot` fails because CMS_ENDPOINTS registry format doesn't match expected bridge input format.

**Why it happens:**
CMS_ENDPOINTS uses a specific dict structure (`{endpoint_key: {"path": ..., "model": ...}}`). Bridge must map this correctly to the `cms:` prefix routing.

**How to avoid:**
1. Single mapping function `cms_endpoint_to_catalog_entry()` tested independently
2. Test: for every entry in `CMS_ENDPOINTS`, verify `call_nautobot(endpoint="cms:{key}")` routes correctly
3. Integration test: catalog discover → call → assert success

**Warning signs:**
`nautobot_api_catalog` returns CMS entries but `call_nautobot("cms:juniper_static_routes")` returns "unknown endpoint."

**Phase to address:** Phase 15-16 — catalog + bridge must be tested together

---

### Pitfall 4: Workflow Parameter Mismatch

**What goes wrong:**
Workflow registry declares params `{"device": "str"}` but the underlying function expects `device_name` or `client` as first argument. Agent passes correct params from catalog but workflow function rejects them.

**Why it happens:**
Workflow functions have inconsistent parameter names across domain modules (some use `device`, others `device_name`, some require client object).

**How to avoid:**
1. Workflow registry includes parameter mapping/normalization per workflow
2. Each workflow entry tested: `execute_workflow(name, params)` → success
3. Document parameter mapping in WORKFLOW_REGISTRY comments

**Warning signs:**
`run_workflow("bgp_summary", {"device": "router1"})` returns `TypeError: unexpected keyword argument`.

**Phase to address:** Phase 17 (Workflow Registry) — parameter normalization layer

---

### Pitfall 5: Agent Loses Context of Available Operations

**What goes wrong:**
Agent calls `nautobot_api_catalog` once at the start of a conversation, but then the catalog response falls out of context window during a long conversation. Agent starts guessing endpoint names.

**Why it happens:**
LLM context windows are finite. The catalog response (~400 tokens) competes with conversation history.

**How to avoid:**
1. Agent skills include the relevant endpoints inline — agent doesn't need to memorize
2. `call_nautobot` error messages include a hint: "Use nautobot_api_catalog to see available endpoints"
3. Keep catalog responses concise — domain filter helps reduce response size

**Warning signs:**
Late in conversation, agent stops using correct endpoints or starts inventing tool names.

**Phase to address:** Phase 18 (Agent Skills) — skills embed endpoint references

---

### Pitfall 6: Over-Engineering the Catalog

**What goes wrong:**
Catalog becomes a full API documentation system with field types, constraints, example values — bloating the response and slowing down agent discovery.

**Why it happens:**
Temptation to replace `nautobot_resource_schema` from rejected v1.3 with a "smart catalog."

**How to avoid:**
1. Catalog returns: endpoint, methods, common filters (names only), description
2. No field types, no constraints, no examples in catalog
3. Agent learns what params to pass from skills + trial-and-error
4. If schema needed later, add as separate optional tool (not in v1.3)

**Warning signs:**
Catalog response exceeds 2000 tokens or includes Pydantic model schemas.

**Phase to address:** Phase 15 — catalog design scope constraint

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding core endpoint list | Faster to implement than OpenAPI parsing | Must update JSON when Nautobot adds endpoints | v1.3 — update frequency is very low |
| No field-level schema in catalog | Simpler catalog, smaller token footprint | Agent can't validate params client-side | v1.3 — skills guide correct param usage |
| Workflow params as dict (no Pydantic) | Faster to implement, flexible | Less type safety | v1.3 — workflow count is small (~10) |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| pynautobot endpoint names | Using hyphens (`ip-addresses`) | Convert to underscores (`ip_addresses`) |
| CMS device filtering | Passing device name to CMS API | Resolve device name → UUID first via core API |
| Pagination in pynautobot | Not setting `limit` param | Use `limit` param; pynautobot handles auto-pagination |
| Plugin endpoints | Accessing via raw REST | Use `nautobot.plugins.netnam_cms_core` accessor |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Large catalog response | Slow `nautobot_api_catalog` calls | Domain filter param, concise descriptions | >100 endpoints in catalog |
| Unbounded pagination | `call_nautobot` returns thousands of records | Default `limit=50`, agent specifies higher | >1000 results without limit |
| Workflow timeout | `run_workflow("firewall_summary")` times out on large devices | Existing timeout handling in domain modules | Devices with 500+ firewall terms |

## "Looks Done But Isn't" Checklist

- [ ] **Catalog completeness:** Verify ALL existing MCP operations are reachable via catalog + call_nautobot + run_workflow
- [ ] **CMS endpoint coverage:** Every CMS_ENDPOINTS entry appears in catalog AND routes correctly
- [ ] **Workflow parity:** Every composite tool from old server.py has a workflow registry entry
- [ ] **Skill updates:** All agent skills reference new 3-tool API, not old tool names
- [ ] **Error messages:** Invalid endpoint returns helpful "did you mean" hints, not stack traces
- [ ] **Test coverage:** New bridge/catalog/workflow code has dedicated tests

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Agent endpoint confusion | LOW | Add better hints to error messages, update skill docs |
| Domain test breakage | MEDIUM | Revert bridge changes, re-test against domain modules |
| CMS routing failure | LOW | Fix mapping function, add integration test |
| Workflow param mismatch | LOW | Add param normalization in workflow entry |
| Catalog bloat | LOW | Remove excess fields, enforce max token budget |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Agent can't find endpoint | Phase 15 (Catalog) | Test: invalid endpoint → helpful error |
| Domain test breakage | Phase 16 (Bridge) | All 293 domain tests pass unchanged |
| CMS discovery failure | Phase 15-16 | Integration test: catalog → call → success |
| Workflow param mismatch | Phase 17 (Workflows) | Each workflow callable with catalog-documented params |
| Agent context loss | Phase 18 (Skills) | Skills embed endpoint references inline |
| Catalog bloat | Phase 15 | Catalog response < 1500 tokens |

## Sources

- LLM agent tool selection research — accuracy drops with >25 tools; context window competition
- Existing codebase analysis — CMS_ENDPOINTS format, domain function signatures
- API Bridge design doc — tool classification, workflow analysis
- pynautobot documentation — endpoint naming gotchas, pagination

---
*Pitfalls research for: MCP Server API Bridge for Nautobot*
*Researched: 2026-03-24*
