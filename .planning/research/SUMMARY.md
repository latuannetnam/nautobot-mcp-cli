# Research Summary: nautobot-mcp-cli

## Stack

**FastMCP 3.0 + pynautobot 2.6.x + Typer** — FastMCP is the de facto standard for Python MCP servers (auto-schema from type hints). pynautobot is the official Nautobot SDK (handles auth, pagination, versioning). Typer provides CLI with minimal code. All three share pydantic/type-hint patterns for consistency.

**Python 3.11+** required by MCP SDK. **pytest + respx** for testing.

## Table Stakes

- Nautobot CRUD for all core models (devices, interfaces, IPAM, org, circuits)
- API token authentication with connection validation
- Golden Config plugin integration (read/write compliance rules, intended configs)
- MCP server with tool discovery and structured responses
- CLI with human-readable and scriptable output

## Differentiators

- **Config onboarding workflow** — Parse JunOS config → create/update Nautobot objects automatically
- **Compliance verification** — Compare live config (via jmcp) against Golden Config and Nautobot data models
- **Agent skills** — Pre-built multi-step workflows that chain nautobot-mcp and jmcp tools

## Watch Out For

1. **API pagination** — pynautobot handles it, but raw requests will miss data
2. **MCP tool granularity** — Balance between atomic and composite tools
3. **Config parsing fragility** — JunOS varies by platform/version; need extensive test fixtures
4. **Object reference resolution** — Creating Nautobot objects requires resolving foreign keys (device type, location, manufacturer)
5. **Golden Config plugin API** — Differs from core Nautobot API; test against real server early
6. **Idempotency** — Onboarding must be safe to run repeatedly without creating duplicates

## Architecture

Shared core library with three thin interface layers:
- **Core** (`nautobot_mcp/`) — API client, parsers, comparators, data models
- **MCP Server** (`mcp_server/`) — FastMCP tools wrapping core functions
- **CLI** (`cli/`) — Typer commands wrapping core functions
- **Skills** (`skills/`) — Multi-step workflow definitions

## Build Order

1. Core client (auth, connection)
2. Data model operations (devices, interfaces, IPAM)
3. MCP server layer
4. CLI layer
5. Config parser (JunOS)
6. Golden Config integration
7. Comparators + verification workflows
8. Agent skills

## Existing Implementations

Several Nautobot MCP servers exist (gt732/nautobot-app-mcp, kvncampos/nautobot_mcp). Our approach differs: standalone tool with CLI and skills, not a Nautobot plugin. We complement jmcp for cross-device-and-SoT workflows.
