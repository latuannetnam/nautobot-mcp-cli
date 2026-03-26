# Phase 22: Response Ergonomics & UAT — Research

**Researched:** 2026-03-26
**Phase:** 22-response-ergonomics-uat

---

## 1. RSP-01: `detail=False` Summary Mode in `get_interface_detail()`

### What to Strip

Phase 21 already placed `detail` in the registry `param_map` for `bgp_summary` and `interface_detail`, but `get_interface_detail()` never implemented it. The current function signature at `interfaces.py` L653:

```python
def get_interface_detail(
    client: "NautobotClient",
    device: str,
    include_arp: bool = False,
) -> tuple[InterfaceDetailResponse, list]:
```

Per D-01 through D-05 in 22-CONTEXT.md:
- `detail=False` → strip `families[]` and `vrrp_groups[]` arrays from each unit dict
- `detail=False` → keep `family_count` and `vrrp_group_count` at unit level (these are already set to integer counts)
- `detail=False` → do NOT affect `arp_entries` block (controlled by `include_arp`)
- `detail=True` (default) → full enriched data, unchanged
- `get_interface_detail()` gains `detail: bool = True` parameter

### How to Implement Stripping

The current code at L686–702 builds `enriched_units` by:
1. Fetching families per unit (L686)
2. For each family: fetching VRRP groups, building `vrrp_groups` list (L691–698)
3. Building `unit_dict["families"] = family_dicts` with nested vrrp_groups

**Implementation approach:**

In the per-unit enrichment loop, when `detail=False`, skip the VRRP fetch entirely (avoiding the API call) and also skip building the full `families` list. Instead, set `family_count` directly from the family query count without iterating nested families:

```python
# Around L682-703 in interfaces.py
if detail:
    for unit in units:
        unit_dict = unit.model_dump()
        families = list_interface_families(client, unit_id=unit.id, limit=0)
        family_dicts = []
        for fam in families.results:
            fam_dict = fam.model_dump()
            try:
                vrrp = list_vrrp_groups(client, family_id=fam.id, limit=0)
                fam_dict["vrrp_groups"] = [v.model_dump() for v in vrrp.results]
                fam_dict["vrrp_group_count"] = vrrp.count
            except Exception as e:
                collector.add(f"list_vrrp_groups(family={fam.id})", str(e))
                fam_dict["vrrp_groups"] = []
                fam_dict["vrrp_group_count"] = 0
            family_dicts.append(fam_dict)
        unit_dict["families"] = family_dicts
        unit_dict["family_count"] = len(families.results)
        enriched_units.append(unit_dict)
else:
    # Summary mode: fetch only family counts, no nested families/vrrp
    for unit in units:
        unit_dict = unit.model_dump()
        families = list_interface_families(client, unit_id=unit.id, limit=0)
        unit_dict["family_count"] = families.count
        unit_dict["families"] = []   # stripped
        # vrrp_group_count requires a family_id; compute via batch query
        try:
            vrrp_batch = list_vrrp_groups(client, family_id=None, limit=0)  # or per-family
            # For summary mode, accumulate vrrp_group_count per unit from family_ids
        except Exception:
            pass
        # Simplified: just leave families=[] and set vrrp_group_count=0 in summary
        unit_dict["vrrp_group_count"] = 0  # conservative: we don't know without per-family query
        enriched_units.append(unit_dict)
```

**Key decisions (Claude's discretion per D-53):**
- `vrrp_group_count` in `detail=False` mode: query each family's VRRP count (not nested) or default to `0`. Since families are not nested, compute `vrrp_group_count` via a single batched count per unit by iterating families and counting VRRP per family.
- `family_count` in `detail=False` mode: use `families.count` from the query — already correct.
- Empty `families=[]` in `detail=False` mode — signal to agents that nesting is stripped.

### Integration: Signature + Registry

`get_interface_detail()` gains `detail: bool = True`. The registry entry at `workflows.py` L108–112:

```python
"interface_detail": {
    "function": get_interface_detail,
    "param_map": {"device": "device", "include_arp": "include_arp", "detail": "detail"},  # add detail
    "required": ["device"],
},
```

`_validate_registry()` at import time will confirm `detail` is now in the function signature — no false positives.

---

## 2. RSP-03: `limit` Parameter Across All 4 Composites

### Design: Per-Array Independent Cap

Per D-06 through D-10:
- `limit=0` → no cap (Nautobot convention, Python-falsy sentinel)
- Positive integer `N` → each result array independently capped at `N` items
- Applies to: `units[]`, `groups[]`, `neighbors[]`, `routes[]`, `filters[]`, `policers[]`, `terms[]`, `actions[]`, `families[]`, `vrrp_groups[]`

### Where to Apply Limit Per Composite

**`get_device_bgp_summary` (routing.py L599):**
- Top-level array: `groups[]` — cap at L666 before building `result`
- Nested array: `neighbors[]` per group — cap at L663 (or L661 inside `detail` branch)
- Both use `[:limit] if limit > 0 else identity` pattern (same as existing `routing.py` L426)

**`get_device_routing_table` (routing.py L680):**
- Top-level array: `routes[]` — cap at L724 (after building `route_dicts`)
- Already uses `detail` branching; limit applies in both branches

**`get_device_firewall_summary` (firewalls.py L648):**
- Top-level arrays: `filters[]` (L709) and `policers[]` (L722) — cap in both `detail` and shallow branches
- Nested arrays in `detail` mode: `terms[]` per filter (L704), `actions[]` per policer (L716) — cap those too

**`get_interface_detail` (interfaces.py L653):**
- Top-level array: `units[]` — cap at L703
- Nested arrays: `families[]` per unit (L699 in detail mode), `vrrp_groups[]` per family (L693)
- `arp_entries[]` top-level: cap at L711

### Implementation Pattern

```python
def _cap(items: list, limit: int) -> list:
    """Return items capped at limit (0 = no cap)."""
    return items[:limit] if limit > 0 else items
```

Apply via `unit_dict["families"] = _cap(family_dicts, limit)` etc.

### Registry Updates

Add `"limit": "limit"` to all 4 composite param_maps in `workflows.py` L93–112:

```python
"bgp_summary": {
    "function": get_device_bgp_summary,
    "param_map": {"device": "device", "detail": "detail", "limit": "limit"},  # add limit
    "required": ["device"],
},
"routing_table": {
    "function": get_device_routing_table,
    "param_map": {"device": "device", "detail": "detail", "limit": "limit"},  # add limit
    "required": ["device"],
},
"firewall_summary": {
    "function": get_device_firewall_summary,
    "param_map": {"device": "device", "detail": "detail", "limit": "limit"},  # add limit
    "required": ["device"],
},
"interface_detail": {
    "function": get_interface_detail,
    "param_map": {"device": "device", "include_arp": "include_arp",
                  "detail": "detail", "limit": "limit"},  # add both
    "required": ["device"],
},
```

### Function Signature Updates Required

| Function | File | Current signature | Needed change |
|----------|------|-------------------|---------------|
| `get_device_bgp_summary` | routing.py L599 | `(client, device, detail=False)` | add `limit=0` |
| `get_device_routing_table` | routing.py L680 | `(client, device, detail=False)` | add `limit=0` |
| `get_device_firewall_summary` | firewalls.py L648 | `(client, device, detail=False)` | add `limit=0` |
| `get_interface_detail` | interfaces.py L653 | `(client, device, include_arp=False)` | add `detail=True, limit=0` |

All existing tests patch the composite functions directly (they don't test the domain functions), so the `_validate_registry()` import-time check is the main guard.

---

## 3. RSP-02: `response_size_bytes` in `_build_envelope()`

### Where to Measure

Per D-11 through D-14: `response_size_bytes = len(json.dumps(response_body))`, measured after full response assembly, always present.

**Correct measurement location:** in `run_workflow()` AFTER `_serialize_result()` is called, BEFORE `_build_envelope()`:

```python
# workflows.py around L330-332 (after existing code)
serialized = _serialize_result(result)
response_size_bytes = len(json.dumps(serialized))  # D-11
```

This is the right place because:
1. `_serialize_result()` produces the JSON-safe dict that goes into the envelope's `data` field
2. At this point the full response is assembled — both the data payload AND all metadata fields are known
3. `json.dumps()` on the serialized dict gives the on-wire payload size

**DO NOT measure inside `_build_envelope()`** — the envelope is a dict, and measuring `len(json.dumps(envelope))` would include the envelope wrapper itself (workflow, status, timestamp) which is not the "response body" the agent receives.

### Wiring to `_build_envelope()`

`_build_envelope()` needs a new optional parameter:

```python
def _build_envelope(
    workflow_id: str,
    params: dict,
    data: Any = None,
    error: Exception | str | None = None,
    warnings: list[dict[str, str]] | None = None,
    response_size_bytes: int | None = None,  # NEW
) -> dict:
    ...
    return {
        ...
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response_size_bytes": response_size_bytes,  # always present, None when error
    }
```

Then in `run_workflow()` (both the partial and ok branches at L336 and L342), pass `response_size_bytes=response_size_bytes`.

**Edge case:** when `data is None` (error case), `response_size_bytes` should still be present (it's measuring the empty data case). In the `except` handler at L355, pass `response_size_bytes=0` or `None` since no data was assembled. Per D-12 ("always present"), `None` when error is acceptable — agents can check for presence.

### Import Needed

`json` is not currently imported in `workflows.py`. Add:

```python
import json  # at top of workflows.py
```

---

## 4. Smoke Script Updates

**File:** `scripts/uat_smoke_test.py` (existing, 226 lines)

The existing smoke script already covers `bgp_summary`, `routing_table`, `firewall_summary` via `run_workflow()`. Add these RSP checks:

```python
def test_rsp01_interface_detail_summary_mode(client):
    """RSP-01: interface_detail(detail=False) returns counts, no nested arrays."""
    result = run_workflow(client, workflow_id="interface_detail",
                          params={"device": UAT_DEVICE, "detail": False})
    assert result["status"] in ("ok", "partial"), f"Workflow failed: {result.get('error')}"
    data = result["data"]
    assert data is not None, "data should be present in summary mode"
    for unit in data.get("units", []):
        assert "families" in unit
        assert unit["families"] == [], f"families should be empty in detail=False, got {unit['families']}"
        assert "family_count" in unit, "family_count must be present in summary mode"
        assert "vrrp_group_count" in unit, "vrrp_group_count must be present in summary mode"


def test_rsp02_response_size_bytes_in_envelope(client):
    """RSP-02: All composite envelopes include response_size_bytes."""
    for workflow_id in ("bgp_summary", "routing_table", "firewall_summary", "interface_detail"):
        result = run_workflow(client, workflow_id=workflow_id,
                              params={"device": UAT_DEVICE})
        assert "response_size_bytes" in result, f"{workflow_id}: missing response_size_bytes"
        assert isinstance(result["response_size_bytes"], int)
        assert result["response_size_bytes"] > 0, f"{workflow_id}: response_size_bytes should be > 0"


def test_rsp03_limit_parameter_caps_results(client):
    """RSP-03: limit=N caps result arrays in composite workflows."""
    for workflow_id in ("bgp_summary", "routing_table", "firewall_summary", "interface_detail"):
        result = run_workflow(client, workflow_id=workflow_id,
                              params={"device": UAT_DEVICE, "limit": 2})
        assert result["status"] in ("ok", "partial")
        data = result["data"]
        assert data is not None
        # Check top-level array capped at 2
        top_level_key = {"bgp_summary": "groups", "routing_table": "routes",
                         "firewall_summary": "filters", "interface_detail": "units"}[workflow_id]
        items = data.get(top_level_key, [])
        assert len(items) <= 2, f"{workflow_id}: {top_level_key} should be capped at 2, got {len(items)}"
```

Add to `run_tests()` section:

```python
print("\n[ RSP-01/02/03 Response Ergonomics Tests ]")
rsp_results = [
    _run("RSP-01: interface_detail summary mode", lambda: test_rsp01_interface_detail_summary_mode(client)),
    _run("RSP-02: response_size_bytes in envelope", lambda: test_rsp02_response_size_bytes_in_envelope(client)),
    _run("RSP-03: limit parameter caps arrays", lambda: test_rsp03_limit_parameter_caps_results(client)),
]
```

---

## 5. Pytest Test Suite Additions

### File Organization Decision (Claude's Discretion)

Per 22-CONTEXT.md D-56: "new file vs additions to existing test_workflows.py".

**Decision:** Add RSP tests to existing `tests/test_cms_composites.py` (for domain-level RSP-01/RSP-03 composite function tests) and `tests/test_workflows.py` (for envelope-level RSP-02 tests via `run_workflow()`).

### `tests/test_cms_composites.py` — RSP-01 + RSP-03 Domain Tests

**RSP-01: `detail=False` summary mode for `interface_detail`:**

```python
def test_interface_detail_summary_mode_strips_nested_arrays():
    """RSP-01: get_interface_detail(detail=False) returns family_count but no families/vrrp_groups."""
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()
    unit = MagicMock()
    unit.id = "unit-001"
    unit.model_dump.return_value = {"id": "unit-001", "interface_name": "ge-0/0/0"}

    fam = MagicMock()
    fam.id = "fam-001"
    fam.model_dump.return_value = {"id": "fam-001", "family_type": "inet"}

    with patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(unit)), \
         patch("nautobot_mcp.cms.interfaces.list_interface_families", return_value=_mock_list_response(fam)) as mock_fams, \
         patch("nautobot_mcp.cms.interfaces.list_vrrp_groups", return_value=_mock_list_response()) as mock_vrrp:
        result, warnings = get_interface_detail(client, device="edge-01", detail=False)

    assert result.total_units == 1
    assert len(result.units) == 1
    assert result.units[0]["families"] == [], "families[] must be stripped in summary mode"
    assert result.units[0]["family_count"] == 1, "family_count must be present"
    assert "vrrp_group_count" in result.units[0], "vrrp_group_count must be present"
    # VRRP query should NOT have been called (avoided in summary mode)
    mock_vrrp.assert_not_called()


def test_interface_detail_summary_mode_does_not_affect_arp():
    """RSP-01: detail=False does not affect include_arp behavior."""
    # When detail=False AND include_arp=True: families stripped, ARP still fetched
    ...

def test_interface_detail_detail_true_unchanged():
    """RSP-01: get_interface_detail(detail=True) behavior unchanged."""
    ...
```

**RSP-03: `limit` parameter for all 4 composites:**

```python
def test_bgp_summary_limit_caps_groups_and_neighbors():
    """RSP-03: bgp_summary(limit=N) caps groups[] and neighbors[] independently."""
    from nautobot_mcp.cms.routing import get_device_bgp_summary

    client = _mock_client()
    grps = [_mock_bgp_group(id_=f"grp-{i}") for i in range(5)]
    nbrs = [_mock_bgp_neighbor(id_=f"nbr-{i}", group_id="grp-0") for i in range(5)]

    with patch("nautobot_mcp.cms.routing.list_bgp_groups", return_value=_mock_list_response(*grps)), \
         patch("nautobot_mcp.cms.routing.list_bgp_neighbors", return_value=_mock_list_response(*nbrs)):
        result, warnings = get_device_bgp_summary(client, device="rtr-01", limit=3)

    assert len(result.groups) <= 3, f"groups[] should be capped at 3, got {len(result.groups)}"
    # each group capped at limit neighbors
    for grp in result.groups:
        assert len(grp.get("neighbors", [])) <= 3


def test_routing_table_limit_caps_routes():
    """RSP-03: routing_table(limit=N) caps routes[]."""
    ...


def test_firewall_summary_limit_caps_filters_and_policers():
    """RSP-03: firewall_summary(limit=N) caps filters[] and policers[]."""
    ...


def test_interface_detail_limit_caps_units_and_families():
    """RSP-03: interface_detail(limit=N) caps units[] and families[]."""
    ...
```

### `tests/test_workflows.py` — RSP-02 Envelope Tests

**RSP-02: `response_size_bytes` in envelope via `run_workflow()`:**

```python
class TestResponseSizeBytes:
    """RSP-02: All composite workflow envelopes include response_size_bytes."""

    @pytest.mark.parametrize("workflow_id", [
        "bgp_summary", "routing_table", "firewall_summary", "interface_detail"
    ])
    def test_response_size_bytes_present_in_ok_envelope(self, workflow_id):
        """response_size_bytes must be in envelope for all composite workflows."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"key": "value"}

        with workflow_func_mock(workflow_id, return_value=mock_result):
            client = MagicMock()
            result = run_workflow(client, workflow_id=workflow_id, params={"device": "rtr-01"})

        assert "response_size_bytes" in result, f"{workflow_id}: missing response_size_bytes"
        assert isinstance(result["response_size_bytes"], int)
        assert result["response_size_bytes"] > 0, f"{workflow_id}: response_size_bytes should be > 0"

    def test_response_size_bytes_in_partial_envelope(self):
        """response_size_bytes present in partial status envelope."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"x": 1}
        w = [{"operation": "op1", "error": "timeout"}]
        with workflow_func_mock("bgp_summary", return_value=(mock_result, w)):
            client = MagicMock()
            result = run_workflow(client, workflow_id="bgp_summary", params={"device": "rtr-01"})

        assert "response_size_bytes" in result
        assert result["response_size_bytes"] > 0

    def test_response_size_bytes_equals_actual_json_bytes(self):
        """response_size_bytes equals len(json.dumps(data))."""
        mock_result = MagicMock()
        payload = {"groups": [{"id": "1", "name": "test"}], "total_groups": 1}
        mock_result.model_dump.return_value = payload

        with workflow_func_mock("bgp_summary", return_value=mock_result):
            client = MagicMock()
            result = run_workflow(client, workflow_id="bgp_summary", params={"device": "rtr-01"})

        import json
        expected = len(json.dumps(payload))
        assert result["response_size_bytes"] == expected
```

### Existing Tests That Need Updates

**`test_interface_detail_default()` in `test_cms_composites.py` L244–277:**
- Current mock doesn't pass `detail` or `limit` — existing test is `get_interface_detail(client, device="edge-01")` which is `detail=True, limit=0` defaults. No changes needed.

**`test_interface_detail_with_arp()` L280–306:**
- Same: existing call uses `include_arp=True` only, `detail=True` is default. No changes needed.

**`test_workflows.py` L128–141 (`test_bgp_summary_dispatches_correctly`):**
- Currently uses `params={"device": "core-rtr-01"}` — still valid since all new params have defaults. No assertion changes needed.

---

## 6. Existing Patterns for Response Size Measurement and Limit

### Response Size Measurement

No existing pattern in the codebase. `json.dumps()` + `len()` is the standard approach confirmed in 22-CONTEXT.md insights.

`_serialize_result()` already produces JSON-safe dicts — adding `len(json.dumps(...))` on its output is the cleanest integration point.

### Limit Pattern

**Already used in routing.py and firewalls.py:**
- `routing.py` L426: `limited = all_neighbors[:limit] if limit > 0 else all_neighbors`
- `routing.py` L91–92: `all_results = routes.results; limited = all_results[:limit] if limit > 0 else all_results`
- `firewalls.py` L84: `limited = all_results[:limit] if limit > 0 else all_results`

This is a consistent pattern: `items[:limit] if limit > 0 else items`.

For nested arrays, the same pattern applies per-array: `unit_dict["families"] = family_dicts[:limit] if limit > 0 else family_dicts`.

### `_validate_registry()` Guard

The import-time validation in `workflows.py` L40–89 will catch any registry/signature mismatches for the new params:
- `interface_detail` adding `detail` to param_map → function signature must include it → `_validate_registry()` passes
- `bgp_summary` adding `limit` to param_map → function signature must include it → `_validate_registry()` passes

This prevents any "forgot to update function signature" mistakes from reaching runtime.

---

## 7. Implementation Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| `get_interface_detail()` detail=False doesn't query VRRP — reduces API load | Low | VRRP query is skipped in summary mode; safe |
| `response_size_bytes` measured before envelope fields added (timestamp varies) | Low | Timestamp added after measurement; acceptable |
| `limit` on nested arrays could cause inconsistent counts | Medium | Each array independently capped; documented per D-07 |
| `detail=False` + `include_arp=True` interaction | Low | `arp_entries` controlled independently per D-03 |
| Smoke test devices may not have enough data to demonstrate limit cap | Medium | Smoke test uses `assert len(items) <= 2` not `== 2` |
| `_validate_registry()` fails if function signatures not updated first | High | Update all 4 function signatures BEFORE registry param_maps |
| Backward compat: `interface_detail` now accepts `detail` param | Low | Default is `True`, so existing callers unaffected |

---

## 8. File Changes Summary

| File | Change | Lines Affected |
|------|--------|----------------|
| `nautobot_mcp/workflows.py` | Add `json` import; add `response_size_bytes` param to `_build_envelope()`; pass to both `_build_envelope()` calls in `run_workflow()`; add `"limit": "limit"` to all 4 composite param_maps; add `"detail": "detail"` to `interface_detail` param_map | L14, L93–112, L205, L330–342 |
| `nautobot_mcp/cms/interfaces.py` | Add `detail: bool = True, limit: int = 0` params to `get_interface_detail()`; implement `detail=False` stripping logic; apply `limit` to `units[]` and nested `families[]` | L653–724 |
| `nautobot_mcp/cms/routing.py` | Add `limit: int = 0` to `get_device_bgp_summary()` and `get_device_routing_table()`; apply `limit` to groups[], neighbors[], routes[] | L599, L680 |
| `nautobot_mcp/cms/firewalls.py` | Add `limit: int = 0` to `get_device_firewall_summary()`; apply `limit` to filters[], policers[], terms[], actions[] | L648 |
| `nautobot_mcp/catalog/workflow_stubs.py` | Add `detail` param to `interface_detail` stub; add `limit` to all composite stubs | L38–48 |
| `tests/test_cms_composites.py` | Add `test_interface_detail_summary_mode_*` tests (RSP-01); add `test_*_limit_*` tests (RSP-03) | ~80 new lines |
| `tests/test_workflows.py` | Add `TestResponseSizeBytes` class (RSP-02) | ~40 new lines |
| `scripts/uat_smoke_test.py` | Add 3 RSP smoke test functions; update `run_tests()` to include them | ~50 new lines |

---

## 9. Test Count Projection

- **Current tests:** 415+ (per D-17)
- **New tests:** ~15–20 (5 RSP-01, 4 RSP-03, 4 RSP-02 envelope, 3 smoke)
- **Expected total after phase:** ~430–435 tests
- **All existing tests must continue passing** — the mock-based test strategy means no existing assertions are broken by adding optional parameters with defaults
