---
phase: 02-mcp-server-cli
plan: 02
status: complete
started: 2026-03-17T16:45:00+07:00
completed: 2026-03-17T16:55:00+07:00
---

# Summary: Typer CLI with Nested Subcommands

## What was built
Complete Typer CLI layer with `nautobot-mcp` entry point, nested domain subcommands, global options, table/JSON output formatting, and structured exit codes.

## Key files
### key-files.created
- nautobot_mcp/cli/__init__.py
- nautobot_mcp/cli/app.py
- nautobot_mcp/cli/formatters.py
- nautobot_mcp/cli/devices.py
- nautobot_mcp/cli/interfaces.py
- nautobot_mcp/cli/ipam.py
- nautobot_mcp/cli/organization.py
- nautobot_mcp/cli/circuits.py

## Technical approach
- Root app with `@app.callback()` for global flags: --json, --profile, --url, --token, --no-verify
- `get_client_from_ctx()` creates NautobotClient from CLI context, supports direct URL/token override
- `handle_cli_error()` maps NautobotMCPError hierarchy to exit codes: 0=success, 1=general, 2=connection, 3=not found, 4=validation
- `formatters.py`: `format_table()` using tabulate "simple" format, `format_json()` for --json mode, column defs per resource type
- 5 domain modules with Typer sub-apps: devices, interfaces, ipam (nested: prefixes/addresses/vlans), org (nested: tenants/locations), circuits
- All commands follow consistent pattern: get_client → call core function → output result

## Deviations
None — implemented exactly as planned.
