# Phase 20: Catalog Accuracy & Endpoint Dereference — Research

## Key Findings

### 1. CMS Filter Architecture (Current State)

**Root cause:** `CMS_DOMAIN_FILTERS` (L22-28 of `cms_discovery.py`) maps domain → `["device"]` for all 5 domains. Line 84 does `CMS_DOMAIN_FILTERS.get(domain, ["device"])` — every endpoint gets `["device"]`.

**Impact:** 21 of 33 CMS endpoints do NOT support `device` as a direct filter. Agents get 400 errors or empty results when using advertised filters.

**Fix point:** Line 84 of `cms_discovery.py` — change from domain-based lookup to endpoint-based lookup using new `CMS_ENDPOINT_FILTERS` dict.

### 2. Bridge UUID Path Handling (Current State)

**Root cause:** `_validate_endpoint()` (L45-66 of `bridge.py`) does exact string match against:
- Core: `entry["endpoint"] == endpoint` (L51)
- CMS: `cms_key in CMS_ENDPOINTS` (L56)

No UUID stripping — `/api/dcim/device-types/abc123-def456/` doesn't match `/api/dcim/device-types/`.

**Fix point:** Add UUID detection + stripping before L48 (core validation). `_parse_core_endpoint()` (L81-99) splits on `/` — needs to filter out UUID segments.

**UUID regex:** `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}` — standard UUID v4 format. Nautobot always uses this format.

### 3. Catalog Engine Integration

`engine.py` calls `discover_cms_endpoints()` once (lazy singleton L20-25). The CMS catalog is cached — changes to `CMS_ENDPOINT_FILTERS` only need to happen in `cms_discovery.py`. The `_cms_cache` needs no changes.

### 4. Test Coverage Gaps

**`test_catalog.py`:**
- `test_cms_entries_have_required_fields` (L105-115) checks presence but NOT correctness of filters
- No test validates that endpoint X has filter Y

**`test_bridge.py`:**
- `_validate_endpoint` tests (L36-74) test valid/invalid but NOT UUID-embedded paths
- `_parse_core_endpoint` tests (L127-149) test standard paths but NOT UUID segments

### 5. Existing Patterns to Follow

- `CMS_ENDPOINTS` is `dict[str, str]` — `CMS_ENDPOINT_FILTERS` should be `dict[str, list[str]]` (same flat pattern)
- `resolve_device_id()` already uses UUID detection: `len(val) == 36 and val.count("-") == 4` (L88 of `client.py`) — we can use `re.compile` for the bridge (more precise)
- Tests use direct function imports and `MagicMock` — no fixtures needed

## Validation Architecture

### Dimension 1: Unit correctness
- Filter map has entry for every key in `CMS_ENDPOINTS`
- UUID stripping preserves base endpoint path

### Dimension 2: Integration correctness
- `discover_cms_endpoints()` returns per-endpoint filters
- `call_nautobot()` with UUID path routes correctly

### Dimension 3: Regression
- All existing tests pass unchanged
- `pytest tests/` exits 0
