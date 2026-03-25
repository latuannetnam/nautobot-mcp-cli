---
plan: 20-02
title: UUID Path Normalization & Dereference
status: complete
completed: 2026-03-25
---

## Summary

Added UUID path segment detection and stripping to `bridge.py`. Agents can now pass linked object URLs like `/api/dcim/devices/<uuid>/` directly to `call_nautobot()` without manually decomposing them. The bridge transparently strips the UUID, validates the base endpoint, and passes the UUID as `id` to the backend. Added 9 new tests (6 unit + 3 integration).

## Key Files

### Modified
- `nautobot_mcp/bridge.py` — added `import re`, `_UUID_RE` compiled regex, `_strip_uuid_from_endpoint()` function, updated `call_nautobot()` to strip UUID before validation and routing
- `tests/test_bridge.py` — added `_strip_uuid_from_endpoint` import, `TestUUIDPathNormalization` (6 tests), `TestCallNautobotWithUUID` (3 tests)

## Self-Check: PASSED

- `bridge.py` contains `import re` and `_UUID_RE = re.compile(` ✓
- `bridge.py` contains `def _strip_uuid_from_endpoint(` ✓
- Path without UUID returns unchanged ✓
- UUID stripped from `/api/dcim/device-types/<uuid>/` → base + uuid ✓
- Multi-UUID path raises `NautobotValidationError` with "Nested UUID paths" ✓
- Response preserves original endpoint (with UUID) ✓
- `pytest tests/test_bridge.py` → **64 passed** ✓
- `pytest tests/` → **430 passed, 0 failures** (full regression check) ✓
