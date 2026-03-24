# Stack Research

**Domain:** MCP Server API Bridge for Nautobot
**Researched:** 2026-03-24
**Confidence:** HIGH

## Recommended Stack

### Core Technologies (UNCHANGED from v1.2)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| FastMCP | 3.0+ | MCP server framework | Official SDK, type-hint driven tool definitions, OpenTelemetry support, component versioning |
| pynautobot | 2.3+ | Nautobot REST API client | Dynamic endpoint discovery, auto-pagination, threading support, official SDK |
| Python | 3.12+ | Runtime | Current stable, used throughout existing codebase |
| Pydantic | 2.x | Data validation | Already used for 40+ CMS models, type safety for API bridge |
| Typer | 0.9+ | CLI framework | Already in use, unchanged by API bridge changes |
| DiffSync | 2.x | Drift comparison | Used by existing workflow functions, unchanged |

### New/Changed Libraries for v1.3

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none needed) | — | — | The API Bridge reuses existing stack entirely |

**Key insight:** The API Bridge architecture requires **zero new dependencies**. All changes are structural (how tools are organized) not technological (what libraries to use). This is intentional — the existing stack is proven and the refactoring is about tool layer consolidation only.

### Existing Stack Reuse Map

| Existing Component | API Bridge Role |
|--------------------|-----------------|
| `pynautobot` `Api` class | Powers `call_nautobot` — core/IPAM/circuits endpoint routing |
| `cms/client.py` `CMS_ENDPOINTS` | Powers `nautobot_api_catalog` — dynamic CMS plugin discovery |
| `cms/client.py` `cms_list/get/create/update/delete` | Powers `call_nautobot` — CMS endpoint routing |
| Domain modules (`devices.py`, `interfaces.py`, etc.) | Powers `run_workflow` — composite workflow functions |
| Pydantic models (`models/`) | Used by workflow functions for validation |
| DiffSync adapters | Used by drift comparison workflows |

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Static JSON catalog | OpenAPI spec parsing | If Nautobot changes endpoints frequently; adds complexity |
| pynautobot for routing | Direct HTTP requests | Never — pynautobot handles auth, pagination, error handling |
| FastMCP decorators | Dynamic tool generation | Never — harder to debug, IDE-unfriendly (per Key Decisions) |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| OpenAPI auto-generation of tools | Creates too many tools again, defeats the purpose | Static catalog + universal dispatcher |
| GraphQL | Different paradigm, pynautobot doesn't support it | REST API via pynautobot |
| New ORM/Data layer | Over-engineering; pynautobot already handles this | Existing pynautobot + domain modules |
| Backwards-compatible tool aliases | Doubles tool count, defeats consolidation | Clean break migration |

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| FastMCP 3.0 | Python 3.12+ | Component versioning requires 3.0+ |
| pynautobot 2.3 | Nautobot 2.x REST API | Dynamic endpoint generation handles API changes |
| Pydantic 2.x | FastMCP 3.0 | Both use Pydantic v2 natively |

## Sources

- FastMCP 3.0 release notes (January 2026) — component versioning, OpenTelemetry
- pynautobot documentation — dynamic endpoint generation, pagination, threading
- Existing codebase analysis — no new dependencies needed
- API Bridge design doc — confirms no stack changes required

---
*Stack research for: MCP Server API Bridge for Nautobot*
*Researched: 2026-03-24*
