# Stack Research

**Domain:** MCP Tool Consolidation / Generic Resource Engine
**Researched:** 2026-03-24
**Confidence:** HIGH

## Recommended Stack

### Core Technologies (Already In Place)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| FastMCP | 3.x | MCP server framework with `@mcp.tool` decorators | ✅ Already using |
| pynautobot | 2.x | Nautobot REST API SDK with pagination/auth | ✅ Already using |
| Pydantic | 2.x | Model validation, schema generation, `.model_dump()` | ✅ Already using |
| Typer | 0.x | CLI framework (unchanged in v1.3) | ✅ Already using |

### Stack Additions Needed for v1.3

| Library | Version | Purpose | Why Needed |
|---------|---------|---------|------------|
| `dataclasses` | stdlib | `ResourceDef` registry entries | Lightweight, no new dependency |
| `inspect` | stdlib | Dynamic schema extraction from Pydantic models | Needed for `nautobot_resource_schema` |
| `enum.Enum` | stdlib | Action types (`list/get/create/update/delete`) | Type-safe action dispatch |

**Key finding: No new external dependencies needed.** The Generic Resource Engine uses only Python stdlib additions on top of the existing stack.

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| FastMCP `mount()` sub-servers | Adds protocol complexity; single server is simpler | Single FastMCP instance with registry dispatch |
| Dynamic `@mcp.tool` generation | Complex, harder to debug, IDE can't inspect | Static 3 tools + internal registry dispatch |
| Pydantic `model_json_schema()` for tool params | Over-engineering; FastMCP handles param schema | Return simplified field descriptions in `nautobot_resource_schema` |
| SQLite/JSON file for registry | Unnecessary persistence layer | In-memory Python dict — registry is code-defined |

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Single `nautobot_resource` dispatcher | Semantic Tool Selection (vector-based) | When tool count exceeds 200 and domains are truly unrelated |
| Python dict registry | Plugin-based auto-discovery | When third parties contribute domain modules |
| Static composite tools | Programmatic Tool Calling (PTC) | When LLM needs to compose multi-step queries dynamically |

## Sources

- MCP Specification 2025-2026 — Toolhost Pattern for consolidation
- FastMCP docs (gofastmcp.com) — Dynamic registration, async support
- LangChain Tool Overload Research 2025 — Accuracy degradation curves

---
*Stack research for: MCP Tool Consolidation*
*Researched: 2026-03-24*
