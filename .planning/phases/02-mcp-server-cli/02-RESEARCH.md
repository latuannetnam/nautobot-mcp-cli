# Phase 2: MCP Server & CLI - Research

**Researched:** 2026-03-17

## FastMCP 3.0 Server

### Tool Registration Pattern
FastMCP uses `@mcp.tool` decorator that auto-generates JSON schema from Python type hints:

```python
from fastmcp import FastMCP
mcp = FastMCP("Nautobot MCP Server")

@mcp.tool(
    name="nautobot_list_devices",
    description="List Nautobot devices with optional filtering by location, tenant, role, platform."
)
def nautobot_list_devices(
    location: str | None = None,
    tenant: str | None = None,
    role: str | None = None,
    limit: int = 50,
) -> dict:
    """List devices with filtering."""
    client = get_client()
    result = list_devices(client, location=location, tenant=tenant, role=role, limit=limit)
    return result.model_dump()
```

### Key Findings
- **Custom tool name**: `@mcp.tool(name="nautobot_list_devices")` — can use any name, not bound to function name
- **Description**: `description=` param overrides docstring for LLM-facing description
- **Tags/meta**: `tags={"devices", "crud"}` for organization, `meta={"version": "1.0"}` for metadata
- **Type annotations**: FastMCP generates input schema from type hints — `str | None`, `int`, `bool` all supported
- **Return values**: Return dicts/lists directly — FastMCP serializes to JSON. Pydantic models can be returned and are auto-serialized
- **Error handling**: Raise `ToolError` from `fastmcp.exceptions` for explicit error messages to client. Other exceptions are caught and masked by default with `mask_error_details=True`
- **Timeouts**: `@mcp.tool(timeout=30.0)` for per-tool timeout
- **Server run**: `mcp.run()` defaults to stdio transport. Also supports `mcp.run(transport="http")` for HTTP/SSE

### Error Handling Strategy
```python
from fastmcp.exceptions import ToolError
from nautobot_mcp.exceptions import NautobotNotFoundError, NautobotConnectionError

@mcp.tool(name="nautobot_get_device")
def nautobot_get_device(name: str = None, id: str = None) -> dict:
    try:
        client = get_client()
        result = get_device(client, name=name, id=id)
        return result.model_dump()
    except NautobotNotFoundError as e:
        raise ToolError(f"{e.message}. Hint: {e.hint}")
    except NautobotConnectionError as e:
        raise ToolError(f"Connection failed: {e.message}. Hint: {e.hint}")
```

### Client Lifecycle
- Create `NautobotClient` once at server startup or lazily on first tool call
- Client has built-in retry (3 attempts) — no need for MCP-level retry
- Config from env vars (`NAUTOBOT_URL`, `NAUTOBOT_TOKEN`) — aligns with MCP server deployment

## Typer CLI Framework

### Nested Subcommand Pattern
```python
import typer

app = typer.Typer(name="nautobot-mcp")
devices_app = typer.Typer(help="Device operations")
ipam_app = typer.Typer(help="IPAM operations")
prefixes_app = typer.Typer(help="Prefix operations")

app.add_typer(devices_app, name="devices")
app.add_typer(ipam_app, name="ipam")
ipam_app.add_typer(prefixes_app, name="prefixes")

@devices_app.command("list")
def devices_list(location: str = None, json_output: bool = typer.Option(False, "--json")):
    ...
```

### Key Findings
- **Nested apps**: `app.add_typer(sub_app, name="devices")` creates `nautobot-mcp devices ...`
- **Global options**: Use `@app.callback()` for options available on every command
- **Shell completion**: Built-in via `typer.main.get_command(app)` — works with bash, zsh, fish
- **Entry point**: `[project.scripts] nautobot-mcp = "nautobot_mcp.cli:app"` in pyproject.toml
- **Exit codes**: `raise typer.Exit(code=2)` for custom exit codes

### Global Options Pattern
```python
@app.callback()
def main(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    profile: str = typer.Option(None, "--profile", help="Config profile name"),
    url: str = typer.Option(None, "--url", help="Nautobot URL override"),
    token: str = typer.Option(None, "--token", help="API token override"),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip SSL verification"),
):
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    ctx.obj["profile"] = profile
    # Store for downstream commands
```

## Output Formatting

### Tabulate for Table Output
```python
from tabulate import tabulate

def format_table(data: list[dict], headers: list[str]) -> str:
    rows = [[item.get(h, "") for h in headers] for item in data]
    return tabulate(rows, headers=headers, tablefmt="simple")
```

- `tablefmt="simple"` — clean, no borders, agent-friendly
- Columns per resource type: Name, Status, Location/Tenant (varies by model)
- `tabulate` is lightweight (pure Python, no dependencies)

## Wiring Core Library to MCP/CLI

### Pattern: Shared Client Factory
```python
# nautobot_mcp/client_factory.py
_client: NautobotClient | None = None

def get_client(profile=None, url=None, token=None, verify_ssl=True) -> NautobotClient:
    global _client
    if _client is None:
        settings = NautobotSettings(profile=profile)
        if url: settings.url = url
        if token: settings.token = token
        _client = NautobotClient(settings)
    return _client
```

Both MCP server and CLI use `get_client()` — MCP gets config from env, CLI gets from flags → env → config file.

## Dependencies to Add

```toml
[project.dependencies]
# ... existing ...
fastmcp = ">=3.0.0"
typer = ">=0.15.0"
tabulate = ">=0.9.0"

[project.scripts]
nautobot-mcp = "nautobot_mcp.cli.app:app"
```

## Module Structure for Phase 2

```
nautobot_mcp/
├── server.py              # FastMCP server + all @mcp.tool definitions
├── cli/
│   ├── __init__.py
│   ├── app.py             # Typer app root + global options
│   ├── devices.py         # devices subcommands
│   ├── interfaces.py      # interfaces subcommands
│   ├── ipam.py            # ipam subcommands (prefixes, addresses, vlans)
│   ├── organization.py    # org subcommands (tenants, locations)
│   ├── circuits.py        # circuits subcommands
│   └── formatters.py      # Table/JSON output formatting
└── ...existing modules...
```

## Pitfalls Specific to Phase 2

1. **MCP tool too-granular (Pitfall #3)**: Accepted risk — user chose one-tool-per-function. Mitigate with rich descriptions so agents know which tool to call.
2. **MCP transport misconfiguration (Pitfall #7)**: Use `mcp.run()` which defaults to stdio. Test with Claude Desktop early.
3. **Error handling for agents (Pitfall #9)**: Convert all `NautobotMCPError` subclasses to `ToolError` with structured messages.

## Validation Architecture

### Key Risk Areas
1. **MCP tool schema generation** — Type hints must produce valid JSON schemas
2. **Client lifecycle** — Singleton client must handle reconnection after errors
3. **CLI global options propagation** — Typer context must pass options to all subcommands
4. **Output format consistency** — JSON output must match `ListResponse` shape exactly

### Validation Approach
- Unit tests: Mock `NautobotClient`, verify tool output shapes
- Integration test: Start MCP server, call tools via MCP client
- CLI test: Invoke Typer commands programmatically with `CliRunner`
- Output test: Verify JSON shape matches `{"count": N, "results": [...]}`

---

*Phase: 02-mcp-server-cli*
*Research completed: 2026-03-17*
