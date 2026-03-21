---
plan: 11-02
phase: 11
title: "Firewall Domain CRUD Functions & MCP Tools"
status: complete
completed_at: 2026-03-21
commits:
  - 6d169aa
  - f170065
key-files:
  created:
    - nautobot_mcp/cms/firewalls.py
  modified:
    - nautobot_mcp/server.py
---

## Summary

Created `nautobot_mcp/cms/firewalls.py` with **20 CRUD functions** and registered **20 MCP tools** in `server.py`.

### Functions Created

**Full CRUD (10 functions):**
- `list_firewall_filters` / `get_firewall_filter` / `create_firewall_filter` / `update_firewall_filter` / `delete_firewall_filter`
- `list_firewall_policers` / `get_firewall_policer` / `create_firewall_policer` / `update_firewall_policer` / `delete_firewall_policer`

**Read-only sub-models (10 functions — list/get × 5):**
- `list_firewall_terms` / `get_firewall_term`
- `list_firewall_match_conditions` / `get_firewall_match_condition`
- `list_firewall_filter_actions` / `get_firewall_filter_action`
- `list_firewall_policer_actions` / `get_firewall_policer_action`
- `list_firewall_match_condition_prefix_lists` / `get_firewall_match_condition_prefix_list`

### MCP Tools Registered

20 tools in `# CMS FIREWALL TOOLS` section in `server.py` (`nautobot_cms_list_firewall_filters`, `nautobot_cms_get_firewall_filter`, etc.)

### Verification

```
python -c "from nautobot_mcp.cms.firewalls import list_firewall_filters, ..." → PASS
python -c "from nautobot_mcp.server import mcp; print('Server loads successfully')" → PASS
```

## Self-Check: PASSED
