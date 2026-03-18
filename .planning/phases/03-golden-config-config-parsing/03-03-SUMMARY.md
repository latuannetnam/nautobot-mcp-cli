---
phase: 03-golden-config-config-parsing
plan: 03
status: complete
started: 2026-03-17T19:00:00+07:00
completed: 2026-03-18T08:15:00+07:00
---

# Summary: MCP Tools & CLI Commands for Golden Config and Parser

## What was built
Extended the FastMCP server and Typer CLI with Golden Config tools/commands and parser tools/commands, completing Phase 3 by making all new capabilities accessible to both AI agents and human users.

## Key files
### key-files.created
- nautobot_mcp/cli/golden_config.py
- nautobot_mcp/cli/parse.py

### key-files.modified
- nautobot_mcp/server.py (added 13 new MCP tools)
- nautobot_mcp/cli/app.py (registered golden-config and parse subcommand groups)

## Technical approach
- 11 Golden Config MCP tools added to server.py: `nautobot_get_intended_config`, `nautobot_get_backup_config`, `nautobot_list_compliance_features`, `nautobot_create_compliance_feature`, `nautobot_delete_compliance_feature`, `nautobot_list_compliance_rules`, `nautobot_create_compliance_rule`, `nautobot_update_compliance_rule`, `nautobot_delete_compliance_rule`, `nautobot_get_compliance_results`, `nautobot_quick_diff_config`
- 2 Parser MCP tools: `nautobot_parse_config`, `nautobot_list_parsers`
- CLI `golden-config` subcommand group with 11 commands matching MCP tools
- CLI `parse` subcommand group with `junos` (reads from file or stdin) and `list-parsers` commands
- All CLI commands follow existing pattern from `devices.py`, `circuits.py`

## Deviations
CLI module paths use flat structure (`nautobot_mcp/cli/golden_config.py`) rather than `commands/` subdirectory as originally planned — matches the established convention from Phases 1 and 2.
