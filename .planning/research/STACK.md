# Stack Research: Nautobot MCP CLI

## Recommended Stack

### Core Framework
- **Python 3.11+** — Required by MCP SDK, aligns with pynautobot compatibility
- **FastMCP 3.0** — High-level Python MCP framework, built on official MCP SDK. Uses decorators (`@mcp.tool()`) and type hints for auto-schema generation. Incorporated into official MCP Python SDK.
- **Confidence:** ★★★★★ (FastMCP is the de facto standard for Python MCP servers)

### Nautobot Client
- **pynautobot v2.6.x** — Official Python SDK for Nautobot REST API. Supports multithreaded queries, global/per-request API versioning. Compatible with Nautobot 2.4+.
- **Confidence:** ★★★★★ (Official SDK, actively maintained by Network to Code)

### CLI Framework
- **Click** or **Typer** — Typer is built on Click with type hints (aligns with FastMCP patterns). Both are well-established.
- **Recommendation:** Typer — consistent type-hint-driven approach across MCP and CLI layers
- **Confidence:** ★★★★☆

### Config & Auth
- **python-dotenv** — Environment variable management for API tokens
- **pydantic** or **pydantic-settings** — Config validation (FastMCP already depends on pydantic)
- **Confidence:** ★★★★★

### Network Config Parsing
- **ttp (Template Text Parser)** — Parse semi-structured device configs (JunOS, IOS)
- **jinja2** — Template rendering for golden config comparison
- **Confidence:** ★★★★☆

### Testing
- **pytest** — Standard Python testing
- **pytest-asyncio** — For async MCP tool tests
- **responses** or **respx** — Mock HTTP/Nautobot API calls
- **Confidence:** ★★★★★

## What NOT to Use

| Library | Why Not |
|---------|---------|
| Raw `requests` for Nautobot | pynautobot handles auth, pagination, versioning |
| Flask/Django for MCP | FastMCP handles MCP protocol natively |
| NAPALM | Overlaps with jmcp; this tool doesn't talk to devices directly |
| netmiko | Same — device interaction is jmcp's job |
| Ansible modules | Overkill for API client; adds heavyweight dependency |

## Existing Implementations to Reference

- **gt732/nautobot-app-mcp** — Nautobot plugin that integrates MCP server directly into Nautobot
- **kvncampos/nautobot_mcp** — Standalone MCP server with semantic search across Nautobot APIs
- **Network to Code's official Nautobot MCP** — Dynamic API request tool, OpenAPI schema discovery

Our approach differs: standalone MCP server + CLI + skills, not a Nautobot plugin.

## Version Matrix

| Component | Version | Compatibility |
|-----------|---------|---------------|
| Python | 3.11+ | MCP SDK requirement |
| FastMCP | 3.0.x | Latest, Jan 2026 |
| pynautobot | 2.6.x | Nautobot 2.4+ |
| Nautobot server | 2.4.x | User's current version |
| MCP protocol | 2025-11-05 | Latest stable spec |
