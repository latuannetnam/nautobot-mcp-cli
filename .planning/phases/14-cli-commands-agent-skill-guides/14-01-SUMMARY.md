---
phase: 14
plan: 1
status: complete
completed: 2026-03-21
---

# Summary: Plan 14-01 — Extract Drift CLI & Add ARP CLI

## What Was Built
Extracted the drift comparison CLI commands from `cms_routing.py` into a dedicated `nautobot_mcp/cli/cms_drift.py` module, registered the new module under `nautobot-mcp cms drift`, and created unit tests to cover both commands.

## Key Files Created/Modified

### Created
- `nautobot_mcp/cli/cms_drift.py` — New dedicated drift CLI module
  - `drift_app = typer.Typer(help="CMS drift verification commands")`
  - `@drift_app.command("bgp")` — Compare live BGP neighbors against CMS
  - `@drift_app.command("routes")` — Compare live static routes against CMS
  - Supports `--from-file` (path) or stdin fallback
  - JSON and table output modes via `ctx.obj.get("json", False)`
- `tests/test_cli_cms_drift.py` — 8 unit tests for drift CLI commands
  - `TestDriftBgpFromFile` — 4 tests for `cms drift bgp`
  - `TestDriftRoutesFromFile` — 4 tests for `cms drift routes`

### Modified
- `nautobot_mcp/cli/cms_routing.py` — Removed DRIFT COMPARISON COMMANDS section (drift-bgp, drift-routes)
- `nautobot_mcp/cli/app.py` — Added `from nautobot_mcp.cli.cms_drift import drift_app` and `cms_app.add_typer(drift_app, name="drift")`

## Decisions Made
- `ARP CLI`: ARP commands already in `cms_interfaces.py` (`list-arp-entries`, `get-arp-entry`) — no separate module needed
- `mix_stderr`: CliRunner constructed without `mix_stderr=False` (not supported in installed typer version)

## Verification
```
pytest tests/test_cli_cms_drift.py -v  → 8 passed
pytest tests/ -k "routing" -v          → 26 passed, no regressions
python -c "from nautobot_mcp.cli.app import app; print('ok')"  → ok
```
