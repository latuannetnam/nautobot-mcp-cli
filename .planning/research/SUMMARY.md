# Research Summary

**Domain:** MCP Tool Consolidation / Generic Resource Engine
**Synthesized:** 2026-03-24
**Dimensions:** Stack, Features, Architecture, Pitfalls

## Key Findings

### Stack Additions
- **No new external dependencies** — only Python stdlib (`dataclasses`, `inspect`, `enum`)
- Core stack unchanged: FastMCP 3.x, pynautobot 2.x, Pydantic 2.x, Typer

### Feature Table Stakes
- Resource catalog discovery (`nautobot_list_resources`)
- Schema introspection (`nautobot_resource_schema`)
- Universal CRUD dispatcher (`nautobot_resource`)
- ~15 preserved composite workflow tools (multi-entity joins)
- Action validation, filter passthrough, structured errors

### Architecture Pattern
- **Toolhost Pattern** — industry-recognized MCP pattern for consolidating 20+ closely related tools
- Single `registry.py` module with `RESOURCE_REGISTRY` dict
- Dual handler strategy: CMS uses `cms_list/get/create/update/delete`, core uses explicit domain functions
- Only 2 files change: `registry.py` (new) and `server.py` (modified)

### Watch Out For
1. **Incomplete registry coverage** — automated test must verify 100% old tool coverage
2. **Filter parameter mismatch** — CMS uses `device_name`, core uses `name`/`device`
3. **CMS/Core handler asymmetry** — dual dispatch needed
4. **Schema explosion** — exclude read-only fields from create/update schemas
5. **Composite tool breakage** — keep `get_client()` and domain function signatures unchanged
6. **UAT flakiness** — separate UAT from unit tests, use read-only operations

## Architectural Decision Summary

| Decision | Rationale |
|----------|-----------|
| Static 3 tools + internal dispatch | Debuggable, IDE-friendly, less FastMCP magic |
| `filters: dict` and `data: dict` params | Avoids parameter explosion on generic tool |
| Dual-registry (CMS auto-mapped, Core explicit) | Maximizes code reuse from existing `CMS_ENDPOINTS` |
| Clean break (no aliases) | Tool count stays at ~18 permanently |
| CLI unchanged | CLI calls domain modules directly, not MCP tools |

## Phase Structure Recommendation

Based on research, recommend 4 phases:

1. **Resource Registry Foundation** — `registry.py` with `ResourceDef`, automated coverage test
2. **Server Refactor** — Replace 165 tools with 3 generic + ~15 composites in `server.py`
3. **Test Suite & Coverage** — Update `test_server.py`, new `test_registry.py`, ensure 293+ tests pass
4. **UAT Verification** — Smoke tests against Nautobot dev server (`http://101.96.85.93`)

---
*Research synthesized: 2026-03-24*
