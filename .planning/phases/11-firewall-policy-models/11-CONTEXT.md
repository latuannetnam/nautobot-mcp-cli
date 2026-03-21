# Phase 11: Firewall & Policy Models - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Add full CRUD MCP tools, Pydantic models, and CLI commands for Juniper firewall filters (terms, match conditions, actions, policers) and policy statements (JPS terms, match conditions, actions, prefix lists, communities, AS paths). Requirements FW-01 through FW-07 and POL-01 through POL-08 (15 requirements total).

</domain>

<decisions>
## Implementation Decisions

### CRUD Scope — Top-Level Full CRUD, Sub-Models Read-Only

Only 6 **top-level models** (with direct `device` FK) get full CRUD (list/get/create/update/delete):

| Model | Endpoint | CRUD |
|-------|----------|------|
| JuniperFirewallFilter | `juniper_firewall_filters` | Full CRUD ✅ |
| JuniperFirewallPolicer | `juniper_firewall_policers` | Full CRUD ✅ |
| JuniperPolicyStatement | `juniper_policy_statements` | Full CRUD ✅ |
| JuniperPolicyPrefixList | `juniper_policy_prefix_lists` | Full CRUD ✅ |
| JuniperPolicyCommunity | `juniper_policy_communities` | Full CRUD ✅ |
| JuniperPolicyAsPath | `juniper_policy_as_paths` | Full CRUD ✅ |

All 13 **sub-models** (child FK to parent) get read-only (list/get only):

| Model | Endpoint | CRUD |
|-------|----------|------|
| JuniperFirewallTerm | `juniper_firewall_terms` | Read-only 📖 |
| JuniperFirewallFilterMatchCondition | `juniper_firewall_match_conditions` | Read-only 📖 |
| JuniperFirewallFilterAction | `juniper_firewall_actions` | Read-only 📖 |
| JuniperFirewallPolicerAction | `juniper_firewall_policer_actions` | Read-only 📖 |
| JuniperFirewallMatchConditionToPrefixList | `juniper_firewall_match_condition_prefix_lists` | Read-only 📖 |
| JPSTerm | `jps_terms` | Read-only 📖 |
| JPSMatchCondition | `jps_match_conditions` | Read-only 📖 |
| JPSMatchConditionRouteFilter | `jps_match_condition_route_filters` | Read-only 📖 |
| JPSMatchConditionPrefixList | `jps_match_condition_prefix_lists` | Read-only 📖 |
| JPSMatchConditionCommunity | `jps_match_condition_communities` | Read-only 📖 |
| JPSMatchConditionAsPath | `jps_match_condition_as_paths` | Read-only 📖 |
| JPSAction | `jps_actions` | Read-only 📖 |
| JPSActionCommunity | `jps_action_communities` | Read-only 📖 |
| JPSActionAsPath | `jps_action_as_paths` | Read-only 📖 |
| JPSActionLoadBalance | `jps_action_load_balances` | Read-only 📖 |
| JPSActionInstallNexthop | `jps_action_install_nexthops` | Read-only 📖 |
| JuniperPolicyPrefix | `juniper_policy_prefixes` | Read-only 📖 |

**Estimated tool count:** ~56 tools (6×5 full CRUD + 13×2 read-only)

### Phase Structure — Single Phase with 4-5 Plans

Keep as one Phase 11. Do NOT split into separate firewall + policy phases. Expected plan structure:
1. Pydantic models for all firewall + policy models
2. Firewall MCP tools + CRUD functions
3. Policy MCP tools + CRUD functions
4. CLI commands + unit tests

### Inlining Strategy — Shallow List, Rich Get (Hybrid)

Same pattern as Phase 10:
- **`list_*` tools** return shallow data with **count fields** (term_count, match_count, action_count) — fast for scanning
- **`get_*` tools** return rich data with **inlined child summaries** — full picture in one call

Specific behavior:
- `list_firewall_filters(device=X)` → name, family, description, term_count
- `get_firewall_filter(id)` → inlines term names + order + match_condition_count + action_count
- `list_firewall_terms(filter=X)` → name, order, enabled, match_count, action_count
- `get_firewall_term(id)` → inlines match conditions (type, value, negate) + actions (type, value, policer name)
- `list_policy_statements(device=X)` → name, description, term_count, bgp_association_count
- `get_policy_statement(id)` → inlines term names + match_count + action_count
- `list_jps_terms(statement=X)` → name, order, enabled, match_count, action_count
- `get_jps_term(id)` → inlines match conditions + actions with sub-associations

### Policer Handling — Standalone Tools + Name Inlining

- `list_firewall_policers(device=X)` is a standalone device-scoped tool (full CRUD)
- When `get_firewall_term` shows an action with `action_type=policer`, it inlines only the policer **name** as a string reference
- Agent calls `get_firewall_policer(id)` separately for full bandwidth/burst detail

### CLI Command Structure

- **Nested domain namespace:** `nautobot-mcp cms firewalls <command>` and `nautobot-mcp cms policies <command>`
- **CLI ships with this phase** — not deferred to Phase 14
- **Tabular output + `--detail` flag** — default shows concise table, `--detail` shows inlined child data

### Claude's Discretion
- Exact Pydantic field selection per model (which fields to include vs omit)
- Table column selection for CLI output per model
- Internal helper functions for inlining children into get responses
- Error messages and hints for firewall/policy-specific operations
- Plan decomposition (whether 4 or 5 plans needed)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Established patterns (from Phase 8 + 9 + 10)
- `nautobot_mcp/cms/client.py` — Generic CRUD helpers (`cms_list`, `cms_get`, `cms_create`, `cms_update`, `cms_delete`), device UUID resolution, endpoint registry
- `nautobot_mcp/models/cms/base.py` — `CMSBaseSummary` base model with `from_nautobot()`, `_extract_device()`, `_get_field()`
- `nautobot_mcp/cms/routing.py` — Phase 9 CRUD pattern to follow (inlining, device-scoping, list+get patterns)
- `nautobot_mcp/models/cms/routing.py` — Phase 9 Pydantic model pattern to follow
- `nautobot_mcp/cms/interfaces.py` — Phase 10 CRUD pattern (shallow list, rich get hybrid)
- `nautobot_mcp/models/cms/interfaces.py` — Phase 10 Pydantic model pattern
- `nautobot_mcp/cli/cms_routing.py` — Phase 9 CLI pattern to follow (Typer + rich tables)
- `nautobot_mcp/cli/cms_interfaces.py` — Phase 10 CLI pattern to follow
- `nautobot_mcp/client.py` — `NautobotClient.cms` property for plugin access

### CMS API model definitions
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\models\firewalls.py` — All 7 firewall models (Filter, Term, MatchCondition, MatchConditionToPrefixList, FilterAction, Policer, PolicerAction)
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\models\policies.py` — All policy models (PrefixList, PolicyPrefix, Statement, JPSTerm, JPSMatchCondition, RouteFilter, PrefixListRef, Community, AsPath, JPSAction, ActionCommunity, ActionAsPath, ActionLoadBalance, ActionInstallNexthop)
- `D:\latuan\Programming\nautobot-project\netnam-cms-core\netnam_cms_core\api\urls.py` — All 19 DRF endpoint registrations for firewall + policy domains

</canonical_refs>

<code_context>
## Existing Code Insights

### CMS Endpoint Names (pynautobot underscore format)

**Firewall (7 endpoints):**
- `juniper_firewall_filters` → Firewall filters (device FK, filter by family)
- `juniper_firewall_terms` → Filter terms (filter FK)
- `juniper_firewall_match_conditions` → Match conditions (term FK)
- `juniper_firewall_actions` → Filter actions (term FK, optional policer FK)
- `juniper_firewall_policers` → Policers (device FK)
- `juniper_firewall_policer_actions` → Policer actions (policer FK)
- `juniper_firewall_match_condition_prefix_lists` → Match condition to prefix list junction

**Policy (12 endpoints):**
- `juniper_policy_statements` → Policy statements (device FK)
- `jps_terms` → JPS terms (statement FK)
- `jps_match_conditions` → Match conditions (term FK)
- `jps_match_condition_route_filters` → Route filters (match_condition FK)
- `jps_match_condition_prefix_lists` → Prefix list refs (match_condition FK)
- `jps_match_condition_communities` → Community refs (match_condition FK)
- `jps_match_condition_as_paths` → AS path refs (match_condition FK)
- `jps_actions` → JPS actions (term FK)
- `jps_action_communities` → Action communities (action FK)
- `jps_action_as_paths` → Action AS paths (action FK)
- `jps_action_load_balances` → Action load balances (action FK)
- `jps_action_install_nexthops` → Action install nexthops (action FK)
- `juniper_policy_as_paths` → AS paths (device FK)
- `juniper_policy_communities` → Communities (device FK)
- `juniper_policy_prefix_lists` → Prefix lists (device FK)
- `juniper_policy_prefixes` → Prefix associations (prefix_list FK)

### Key Model Relationships

**Firewall hierarchy:**
- FirewallFilter.device → FK to Device (direct)
- FirewallFilter.family → CharField (inet, inet6, vpls, etc.)
- FirewallTerm.filter → FK to FirewallFilter (related_name: `terms`)
- MatchCondition.term → FK to FirewallTerm (related_name: `match_conditions`)
- MatchCondition.condition_type → CharField (source-address, destination-port, protocol, etc.)
- FilterAction.term → FK to FirewallTerm (related_name: `actions`)
- FilterAction.policer → FK to FirewallPolicer (nullable, related_name: `filter_actions`)
- MatchConditionToPrefixList → junction: match_condition FK + prefix_list FK
- FirewallPolicer.device → FK to Device (direct)
- PolicerAction.policer → FK to FirewallPolicer (related_name: `actions`)

**Policy hierarchy:**
- PolicyStatement.device → FK to Device (direct)
- JPSTerm.statement → FK to PolicyStatement (related_name: `terms`)
- JPSMatchCondition.term → FK to JPSTerm (related_name: `match_conditions`)
- JPSAction.term → FK to JPSTerm (related_name: `actions`)
- RouteFilter.match_condition → FK to JPSMatchCondition (related_name: `route_filters`)
- PrefixListRef.match_condition → FK + prefix_list FK
- CommunityRef.match_condition → FK
- AsPathRef.match_condition → FK
- ActionCommunity.action → FK to JPSAction
- ActionAsPath.action → FK to JPSAction
- ActionLoadBalance.action → FK to JPSAction
- ActionInstallNexthop.action → FK to JPSAction
- PolicyPrefixList.device → FK to Device (direct)
- PolicyPrefix.prefix_list → FK to PrefixList
- PolicyCommunity.device → FK to Device (direct)
- PolicyAsPath.device → FK to Device (direct)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following established Phase 8/9/10 patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-firewall-policy-models*
*Context gathered: 2026-03-21*
