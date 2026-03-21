---
plan: 11-03
phase: 11
title: "Policy Domain CRUD Functions & MCP Tools"
status: complete
completed_at: 2026-03-21
commits:
  - 231410b
  - f170065
key-files:
  created:
    - nautobot_mcp/cms/policies.py
  modified:
    - nautobot_mcp/server.py
---

## Summary

Created `nautobot_mcp/cms/policies.py` with **44 CRUD functions** and registered **44 MCP tools** in `server.py`.

### Functions Created

**Full CRUD (20 functions — 4 models × 5 each):**
- `PolicyStatement`: list / get / create / update / delete
- `PolicyPrefixList`: list / get / create / update / delete
- `PolicyCommunity`: list / get / create / update / delete
- `PolicyAsPath`: list / get / create / update / delete

**Read-only sub-models (24 functions — 12 × list/get):**
- `PolicyPrefix` (prefix_list child)
- `JPSTerm` (statement child, with match_count/action_count inlining)
- `JPSMatchCondition`, `JPSMatchConditionRouteFilter`
- `JPSMatchConditionPrefixList`, `JPSMatchConditionCommunity`, `JPSMatchConditionAsPath`
- `JPSAction`, `JPSActionCommunity`, `JPSActionAsPath`
- `JPSActionLoadBalance`, `JPSActionInstallNexthop`

### MCP Tools Registered

44 tools in `# CMS POLICY TOOLS` section in `server.py` (`nautobot_cms_list_policy_statements`, ..., `nautobot_cms_get_jps_action_install_nexthop`).

### Verification

```
python -c "from nautobot_mcp.cms.policies import list_policy_statements, create_policy_statement, list_jps_terms, ..." → PASS
python -c "from nautobot_mcp.server import mcp; print('Server loads successfully')" → PASS
```

## Self-Check: PASSED
