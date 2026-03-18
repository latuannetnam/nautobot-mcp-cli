---
phase: 04-onboarding-verification-agent-skills
plan: 03
status: complete
started: 2026-03-17T22:00:00+07:00
completed: 2026-03-18T08:20:00+07:00
---

# Summary: MCP Tools, CLI Commands & Agent Skill Guides

## What was built
Exposed onboarding and verification operations through MCP tools and CLI commands. Created agent skill guides for "Onboard Router Config" and "Verify Compliance" workflows.

## Key files
### key-files.created
- nautobot_mcp/cli/onboard.py
- nautobot_mcp/cli/verify.py
- .agent/skills/onboard-router-config/SKILL.md
- .agent/skills/verify-compliance/SKILL.md

### key-files.modified
- nautobot_mcp/server.py (added 3 new MCP tools)
- nautobot_mcp/cli/app.py (registered onboard and verify subcommand groups)

## Technical approach
- 3 MCP tools added to server.py: `nautobot_onboard_config` (with network_os auto-parse + dry_run), `nautobot_verify_config_compliance`, `nautobot_verify_data_model`
- `nautobot_onboard_config` auto-parses config_json via ParserRegistry before calling onboard engine
- `nautobot_verify_data_model` auto-parses config_json via ParserRegistry before calling verification engine
- CLI `onboard config` command reads from file path, parses via ParserRegistry, shows action table
- CLI `verify compliance` and `verify data-model` commands with JSON output support
- Agent skill `onboard-router-config`: 4-step workflow (jmcp pull → dry-run → commit → verify)
- Agent skill `verify-compliance`: dual workflow (config compliance check + data model drift detection)
- Both skills include progress reporting pattern and CLI alternatives

## Deviations
None — implemented exactly as planned.
