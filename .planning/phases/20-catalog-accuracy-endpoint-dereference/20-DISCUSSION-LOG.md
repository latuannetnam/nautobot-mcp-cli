# Phase 20: Catalog Accuracy & Endpoint Dereference - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 20-catalog-accuracy-endpoint-dereference
**Areas discussed:** Per-Endpoint Filter Registry, UUID Path Normalization, Filter Discovery Source of Truth, Backward Compatibility

---

## Per-Endpoint Filter Registry

| Option | Description | Selected |
|--------|-------------|----------|
| Flat dict in `cms_discovery.py` | Replace `CMS_DOMAIN_FILTERS` with `CMS_ENDPOINT_FILTERS` keyed by endpoint name | ✓ |
| Extend `CMS_ENDPOINTS` in `client.py` | Change `CMS_ENDPOINTS` from `{name: model_name}` to `{name: {"model": ..., "filters": ...}}` | |
| You decide | Agent picks best structure | |

**User's choice:** Option 1 — flat dict in `cms_discovery.py`
**Notes:** Minimal change, single file, easy to maintain. Avoids changing the widely-used `CMS_ENDPOINTS` registry.

### Filter Scope Sub-question

| Option | Description | Selected |
|--------|-------------|----------|
| Primary FK filters only | Advertise only the filters agents would use (e.g., `device`, `group`, `firewall_filter`) | ✓ |
| Include universal DRF filters | Also list `id`, `created`, `last_updated` on every endpoint | |

**User's choice:** Primary FK filters only (agent-researched recommendation accepted)
**Notes:** Universal filters would bloat the catalog. `id` is already a bridge-level param. Only ~12 of 33 endpoints support `device` directly.

---

## UUID Path Normalization

| Option | Description | Selected |
|--------|-------------|----------|
| Strip UUID in `_validate_endpoint` | Detect UUID segments, strip before validation, pass as `id` internally | ✓ |
| Separate `dereference` action | Add new method for following URLs, agents decompose URLs themselves | |
| You decide | Agent picks best approach | |

**User's choice:** Option 1 — strip UUID transparently
**Notes:** Transparent to agents, minimal change, handles the common case.

### Nested Paths Sub-question

| Option | Description | Selected |
|--------|-------------|----------|
| Raw HTTP fallback | Use `http_session.get()` for nested paths | |
| Decompose + redirect | Parse nested path into flat filter query | |
| Defer nested paths | Only support single-object dereference in v1.4 | ✓ |

**User's choice:** Option C — defer nested paths
**Notes:** The DRF requirements (DRF-01/02/03) are about single-object dereference, not nested traversal. Keeps scope tight.

---

## Filter Discovery Source of Truth

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcode from codebase analysis | Write complete `CMS_ENDPOINT_FILTERS` based on traced `cms_list()` calls | ✓ |
| Runtime introspection via OPTIONS | Query DRF OPTIONS at startup for dynamic filter discovery | |
| Hybrid | Hardcode now, add `--verify-filters` CLI command later | |

**User's choice:** Option 1 — hardcode from codebase analysis
**Notes:** Filter map changes only when CMS plugin adds new models. Runtime introspection adds complexity without proportional value.

---

## Backward Compatibility

| Option | Description | Selected |
|--------|-------------|----------|
| Clean break | v1.4 is new milestone, agents must update, no compatibility shim | ✓ |
| Deprecation period | Keep old `["device"]` field, add `"primary_filters"` field, remove in v1.5 | |
| You decide | Agent picks approach | |

**User's choice:** Option 1 — clean break
**Notes:** Follows v1.3 precedent ("Clean break, no aliases"). The whole point is to stop advertising wrong filters.

---

## Agent's Discretion

- UUID regex implementation details
- Test structure and organization
- Error message wording

## Deferred Ideas

- Nested endpoint traversal (raw HTTP or decompose+redirect) — future phase
- Runtime filter introspection CLI command (`--verify-filters`) — future phase
