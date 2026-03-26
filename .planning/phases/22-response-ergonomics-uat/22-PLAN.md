---
wave: 22
depends_on: []
phase_id: 22-response-ergonomics-uat
phase_goal: Add summary modes, response size metadata, and limit parameters to composite workflows. Validate all v1.4 fixes end-to-end against the Nautobot dev server.
files_modified:
  - nautobot_mcp/cms/interfaces.py
  - nautobot_mcp/cms/routing.py
  - nautobot_mcp/cms/firewalls.py
  - nautobot_mcp/workflows.py
  - nautobot_mcp/catalog/workflow_stubs.py
  - scripts/uat_smoke_test.py
  - tests/test_cms_composites.py
  - tests/test_workflows.py
autonomous: true
---

# Phase 22: Response Ergonomics & UAT — Plan

## Overview

Implement RSP-01 (`detail=False` summary mode), RSP-02 (`response_size_bytes` in envelopes), and RSP-03 (`limit` parameter for all 4 composites). End with UAT smoke test + pytest validation against the Nautobot dev server.

---

## Wave 1 — Function Signature Updates (Parallel)

All four composite functions need new parameters before the registry can reference them (WFC-03 import-time guard depends on this order).

---

### Task 1.1 — `get_device_bgp_summary`: add `limit: int = 0`

**read_first:**
- `nautobot_mcp/cms/routing.py` lines 599–677 (`get_device_bgp_summary`)

**acceptance_criteria:**
- `grep -n "def get_device_bgp_summary" nautobot_mcp/cms/routing.py` shows `limit: int = 0` in signature
- `grep -n "def get_device_bgp_summary" nautobot_mcp/cms/routing.py` shows `detail: bool = False` already present (no change needed)
- `grep -n "group_dicts = group_dicts\[:limit\] if limit > 0 else group_dicts" nautobot_mcp/cms/routing.py` finds the limit cap on groups
- `grep -n "enriched_neighbors = enriched_neighbors\[:limit\] if limit > 0 else enriched_neighbors" nautobot_mcp/cms/routing.py` finds the limit cap on neighbors per group
- Existing tests in `tests/test_cms_composites.py` still pass after change

**action:**

Change the function signature from:

```python
def get_device_bgp_summary(
    client: "NautobotClient",
    device: str,
    detail: bool = False,
) -> tuple[BGPSummaryResponse, list]:
```

to:

```python
def get_device_bgp_summary(
    client: "NautobotClient",
    device: str,
    detail: bool = False,
    limit: int = 0,
) -> tuple[BGPSummaryResponse, list]:
```

Add limit caps after building `group_dicts` and `enriched_neighbors`:

1. After `group_dicts.append(grp_dict)` (around L666), add:
   ```python
   # Cap groups[] at limit (per-array independent cap)
   group_dicts = group_dicts[:limit] if limit > 0 else group_dicts
   ```

2. In the `if detail and neighbors_for_group:` block, after `enriched_neighbors.append(nbr_dict)` (around L660), add:
   ```python
   # Cap neighbors[] per group at limit (per-array independent cap)
   enriched_neighbors = enriched_neighbors[:limit] if limit > 0 else enriched_neighbors
   ```

3. In the `else:` block (L663), add the same cap after the list comprehension:
   ```python
   grp_dict["neighbors"] = [nbr.model_dump() for nbr in neighbors_for_group[:limit] if limit > 0 else neighbors_for_group]
   ```
   Or as two lines:
   ```python
   neighbors_capped = neighbors_for_group[:limit] if limit > 0 else neighbors_for_group
   grp_dict["neighbors"] = [nbr.model_dump() for nbr in neighbors_capped]
   ```

---

### Task 1.2 — `get_device_routing_table`: add `limit: int = 0`

**read_first:**
- `nautobot_mcp/cms/routing.py` lines 680–729 (`get_device_routing_table`)

**acceptance_criteria:**
- `grep -n "def get_device_routing_table" nautobot_mcp/cms/routing.py` shows `limit: int = 0` in signature
- `grep -n "def get_device_routing_table" nautobot_mcp/cms/routing.py` shows `detail: bool = False` already present
- `grep -n "routes = routes\[:limit\] if limit > 0 else routes" nautobot_mcp/cms/routing.py` finds the routes cap
- Existing tests in `tests/test_cms_composites.py` still pass after change

**action:**

Change the function signature from:

```python
def get_device_routing_table(
    client: "NautobotClient",
    device: str,
    detail: bool = False,
) -> tuple[RoutingTableResponse, list]:
```

to:

```python
def get_device_routing_table(
    client: "NautobotClient",
    device: str,
    detail: bool = False,
    limit: int = 0,
) -> tuple[RoutingTableResponse, list]:
```

After `routes = routes_resp.results` (around L707), add:
```python
# Cap routes[] at limit
routes = routes[:limit] if limit > 0 else routes
```

---

### Task 1.3 — `get_device_firewall_summary`: add `limit: int = 0`

**read_first:**
- `nautobot_mcp/cms/firewalls.py` lines 648–743+ (`get_device_firewall_summary`)

**acceptance_criteria:**
- `grep -n "def get_device_firewall_summary" nautobot_mcp/cms/firewalls.py` shows `limit: int = 0` in signature
- `grep -n "filter_dicts = filter_dicts\[:limit\] if limit > 0 else filter_dicts" nautobot_mcp/cms/firewalls.py` finds the filters cap
- `grep -n "policer_dicts = policer_dicts\[:limit\] if limit > 0 else policer_dicts" nautobot_mcp/cms/firewalls.py` finds the policers cap
- `grep -n "fd\[\"terms\"\] = \[t\.model_dump\(\) for t in terms_resp\.results\[:limit\] if limit > 0 else terms_resp\.results\]" nautobot_mcp/cms/firewalls.py` finds the terms cap in detail mode (one-liner approach)
- Existing tests in `tests/test_cms_composites.py` still pass after change

**action:**

Change the function signature from:

```python
def get_device_firewall_summary(
    client: "NautobotClient",
    device: str,
    detail: bool = False,
) -> tuple[FirewallSummaryResponse, list]:
```

to:

```python
def get_device_firewall_summary(
    client: "NautobotClient",
    device: str,
    detail: bool = False,
    limit: int = 0,
) -> tuple[FirewallSummaryResponse, list]:
```

Apply per-array independent limits:

1. After the `detail` block builds `filter_dicts` and `policer_dicts` lists (around L709 and L722), add cap before building the response:
   - After `filter_dicts.append(fd)` loop → before building FirewallSummaryResponse:
     ```python
     filter_dicts = filter_dicts[:limit] if limit > 0 else filter_dicts
     ```
   - After `policer_dicts.append(pd)` loop → before building FirewallSummaryResponse:
     ```python
     policer_dicts = policer_dicts[:limit] if limit > 0 else policer_dicts
     ```

2. In the `else:` block (shallow mode), add the same caps after building `filter_dicts` and `policer_dicts`:
   ```python
   filter_dicts = [fw_filter.model_dump() for fw_filter in filters_data[:limit] if limit > 0 else filters_data]
   policer_dicts = [fw_policer.model_dump() for fw_policer in policers_data[:limit] if limit > 0 else policers_data]
   ```
   Or as separate statements using the same `[:limit] if limit > 0 else identity` pattern as the detail branch.

3. In the `detail` block, cap `terms[]` per filter and `actions[]` per policer by changing:
   ```python
   fd["terms"] = [t.model_dump() for t in terms_resp.results]
   ```
   to:
   ```python
   fd["terms"] = [t.model_dump() for t in terms_resp.results[:limit] if limit > 0 else terms_resp.results]
   ```
   And similarly for `actions[]`:
   ```python
   pd["actions"] = [a.model_dump() for a in actions_resp.results[:limit] if limit > 0 else actions_resp.results]
   ```

---

### Task 1.4 — `get_interface_detail`: add `detail: bool = True, limit: int = 0`, implement RSP-01

**read_first:**
- `nautobot_mcp/cms/interfaces.py` lines 653–724 (`get_interface_detail`)
- `nautobot_mcp/models/cms/composites.py` (InterfaceDetailResponse model)

**acceptance_criteria:**
- `grep -n "def get_interface_detail" nautobot_mcp/cms/interfaces.py` shows `detail: bool = True, limit: int = 0` in signature
- `grep -n "detail:" nautobot_mcp/cms/interfaces.py` finds `if detail:` branching block
- `grep -n "families = \[\]" nautobot_mcp/cms/interfaces.py` finds the summary mode families=[] strip
- `grep -n "vrrp_group_count" nautobot_mcp/cms/interfaces.py` finds vrrp_group_count set in summary mode (not hardcoded to 0)
- `grep -n "unit_dict\[\\"families\\"\] = family_dicts\[:limit\] if limit > 0 else family_dicts" nautobot_mcp/cms/interfaces.py` finds families cap
- `grep -n "enriched_units = enriched_units\[:limit\] if limit > 0 else enriched_units" nautobot_mcp/cms/interfaces.py` finds units cap
- `grep -n "arp_entries = arp_entries\[:limit\] if limit > 0 else arp_entries" nautobot_mcp/cms/interfaces.py` finds arp_entries cap
- Existing `test_interface_detail_default()` in `tests/test_cms_composites.py` still passes (backward compat — detail=True is the default)
- `workflows.py` imports `get_interface_detail` without error after signature change

**action:**

**Step A — Signature:** Change from:
```python
def get_interface_detail(
    client: "NautobotClient",
    device: str,
    include_arp: bool = False,
) -> tuple[InterfaceDetailResponse, list]:
```
to:
```python
def get_interface_detail(
    client: "NautobotClient",
    device: str,
    include_arp: bool = False,
    detail: bool = True,
    limit: int = 0,
) -> tuple[InterfaceDetailResponse, list]:
```

**Step B — Branch on `detail`:** Replace the entire unit enrichment loop (L682–703) with:

```python
# For each unit, fetch its families and VRRP groups
enriched_units = []
for unit in units:
    unit_dict = unit.model_dump()

    # Fetch families for the unit (critical — failure propagates)
    families = list_interface_families(client, unit_id=unit.id, limit=0)
    family_count = families.count

    if detail:
        # Full enrichment: nested families + VRRP groups
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
            # Cap families[] nested array at limit
            if limit > 0 and len(family_dicts) >= limit:
                break
            family_dicts.append(fam_dict)
        unit_dict["families"] = family_dicts
        unit_dict["family_count"] = family_count
    else:
        # Summary mode: strip families[] and vrrp_groups[], keep counts only.
        # Compute vrrp_group_count by iterating each family.
        total_vrrp = 0
        for fam in families.results:
            try:
                vrrp = list_vrrp_groups(client, family_id=fam.id, limit=0)
                total_vrrp += vrrp.count
            except Exception:
                # Non-fatal in summary mode; skip
                pass
        unit_dict["families"] = []      # stripped for agents
        unit_dict["family_count"] = family_count
        unit_dict["vrrp_group_count"] = total_vrrp

    # Cap units[] at limit
    if limit > 0 and len(enriched_units) >= limit:
        break
    enriched_units.append(unit_dict)
```

**Step C — Cap `arp_entries` at limit:** After `arp_entries = [e.model_dump() for e in arp_resp.results]` (L711), add:
```python
arp_entries = arp_entries[:limit] if limit > 0 else arp_entries
```

---

## Wave 2 — `workflows.py` Registry + Engine (Depends on Wave 1)

---

### Task 2.1 — Add `json` import, `response_size_bytes` to `_build_envelope()`, update registry param_maps, wire `run_workflow()`

**read_first:**
- `nautobot_mcp/workflows.py` (full file — imports L14, registry L92–165, `_build_envelope` L205–255, `run_workflow` L263–360)

**acceptance_criteria:**
- `grep -n "^import json" nautobot_mcp/workflows.py` finds the json import
- `grep -n "response_size_bytes" nautobot_mcp/workflows.py` finds it in `_build_envelope` signature, body, and `run_workflow` calls
- `grep -n '"limit": "limit"' nautobot_mcp/workflows.py` finds limit entries for all 4 composites: `bgp_summary`, `routing_table`, `firewall_summary`, `interface_detail`
- `grep -n '"detail": "detail"' nautobot_mcp/workflows.py` finds detail entry for `interface_detail` (alongside existing entries for bgp_summary and routing_table which are already there)
- `grep -n "response_size_bytes=response_size_bytes" nautobot_mcp/workflows.py` finds the pass-through in both ok and partial envelope calls
- `_validate_registry()` passes without error (module imports cleanly: `python -c "import nautobot_mcp.workflows"` succeeds)
- `python -c "from nautobot_mcp.workflows import WORKFLOW_REGISTRY; print(WORKFLOW_REGISTRY['interface_detail']['param_map'])"` shows `{'device': 'device', 'include_arp': 'include_arp', 'detail': 'detail', 'limit': 'limit'}`
- `python -c "from nautobot_mcp.workflows import WORKFLOW_REGISTRY; print(WORKFLOW_REGISTRY['bgp_summary']['param_map'])"` shows `{'device': 'device', 'detail': 'detail', 'limit': 'limit'}`

**action:**

**Change 1 — Add `json` import:** Add at top of file, after existing imports:
```python
import json
```

**Change 2 — `_build_envelope()` signature and body:** Change the signature from:
```python
def _build_envelope(
    workflow_id: str,
    params: dict,
    data: Any = None,
    error: Exception | str | None = None,
    warnings: list[dict[str, str]] | None = None,
) -> dict:
```
to:
```python
def _build_envelope(
    workflow_id: str,
    params: dict,
    data: Any = None,
    error: Exception | str | None = None,
    warnings: list[dict[str, str]] | None = None,
    response_size_bytes: int | None = None,
) -> dict:
```

In the return dict (around L247–255), add `"response_size_bytes": response_size_bytes`:
```python
return {
    "workflow": workflow_id,
    "device": device,
    "status": status,
    "data": data,
    "error": error_str,
    "warnings": warnings if warnings is not None else [],
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "response_size_bytes": response_size_bytes,
}
```

**Change 3 — Update registry `param_map` entries:**

For `bgp_summary`:
```python
"bgp_summary": {
    "function": get_device_bgp_summary,
    "param_map": {"device": "device", "detail": "detail", "limit": "limit"},
    "required": ["device"],
},
```

For `routing_table`:
```python
"routing_table": {
    "function": get_device_routing_table,
    "param_map": {"device": "device", "detail": "detail", "limit": "limit"},
    "required": ["device"],
},
```

For `firewall_summary`:
```python
"firewall_summary": {
    "function": get_device_firewall_summary,
    "param_map": {"device": "device", "detail": "detail", "limit": "limit"},
    "required": ["device"],
},
```

For `interface_detail`:
```python
"interface_detail": {
    "function": get_interface_detail,
    "param_map": {"device": "device", "include_arp": "include_arp", "detail": "detail", "limit": "limit"},
    "required": ["device"],
},
```

**Change 4 — `run_workflow()` wiring:** In the `try` block after `serialized = _serialize_result(result)` (L330), **add `response_size_bytes = len(json.dumps(serialized))`**, then pass `response_size_bytes=response_size_bytes` to both envelope calls.

In the `try` block after `serialized = _serialize_result(result)` (L330), measure size and pass to `_build_envelope()`:

In the `if warnings_list:` branch (L336–341), add `response_size_bytes`:
```python
return _build_envelope(
    workflow_id, params,
    data=serialized,
    error=error_summary,
    warnings=warnings_list,
    response_size_bytes=response_size_bytes,
)
```

In the `return _build_envelope(workflow_id, params, data=serialized)` ok branch (L342), add:
```python
return _build_envelope(
    workflow_id, params,
    data=serialized,
    response_size_bytes=response_size_bytes,
)
```

In the `except` block (L355–360), add `response_size_bytes=0`:
```python
return _build_envelope(
    workflow_id,
    params,
    error=e,
    warnings=[exception_warning],
    response_size_bytes=0,
)
```

**CRITICAL ordering note:** Task 2.1 must be done AFTER all 4 composite function signatures are updated (Wave 1). Otherwise `_validate_registry()` will raise `NautobotValidationError` because the registry will reference `limit` and `detail` params that don't exist in the function signatures yet.

---

### Task 2.2 — Update `workflow_stubs.py` catalog with `detail` and `limit` params

**read_first:**
- `nautobot_mcp/catalog/workflow_stubs.py` (full file — `WORKFLOW_STUBS` dict L8–96)

**acceptance_criteria:**
- `grep -n '"detail": "bool (optional, default true)"' nautobot_mcp/catalog/workflow_stubs.py` finds the `detail` param in `interface_detail`
- `grep -n '"limit": "int (optional, default 0)"' nautobot_mcp/catalog/workflow_stubs.py` finds the `limit` param in all 4 composites: `bgp_summary`, `routing_table`, `firewall_summary`, `interface_detail`
- `grep -n "WORKFLOW_STUBS\['interface_detail'\]\['params'\]" -A 6` shows all 4 params: `device`, `include_arp`, `detail`, `limit`
- `python -c "from nautobot_mcp.catalog.workflow_stubs import WORKFLOW_STUBS; print(WORKFLOW_STUBS['bgp_summary']['params'])"` shows `{"device": "str (required)", "detail": "bool (optional)", "limit": "int (optional, default 0)"}`

**action:**

`workflow_stubs.py` is a **manual catalog file** (not auto-generated). It must be kept in sync with `WORKFLOW_REGISTRY` param maps so agents and documentation see the correct agent-facing parameter list.

Apply the following changes to the `WORKFLOW_STUBS` dict:

**Change 1 — `bgp_summary`:**
```python
"params": {"device": "str (required)", "detail": "bool (optional)", "limit": "int (optional, default 0)"},
```

**Change 2 — `routing_table`:**
```python
"params": {"device": "str (required)", "detail": "bool (optional, default false)", "limit": "int (optional, default 0)"},
```

**Change 3 — `firewall_summary`:**
```python
"params": {"device": "str (required)", "detail": "bool (optional, default false)", "limit": "int (optional, default 0)"},
```

**Change 4 — `interface_detail`:** Add `"detail"` and `"limit"` alongside the existing `device` and `include_arp`:
```python
"params": {
    "device": "str (required)",
    "include_arp": "bool (optional, default false)",
    "detail": "bool (optional, default true)",
    "limit": "int (optional, default 0)",
},
```

---

## Wave 3 — Smoke Script + Pytest Tests (Depends on Wave 2)

---

### Task 3.1 — Update smoke script with RSP-01/02/03 tests

**read_first:**
- `scripts/uat_smoke_test.py` (full file, 226 lines — existing test functions L77–166, `run_tests()` L173–221)

**acceptance_criteria:**
- `grep -n "def test_rsp01" scripts/uat_smoke_test.py` finds the RSP-01 test function
- `grep -n "def test_rsp02" scripts/uat_smoke_test.py` finds the RSP-02 test function
- `grep -n "def test_rsp03" scripts/uat_smoke_test.py` finds the RSP-03 test function
- `grep -n "response_size_bytes" scripts/uat_smoke_test.py` finds at least 2 occurrences (RSP-02 + RSP-03 checks)
- `grep -n "RSP" scripts/uat_smoke_test.py` finds the RSP section header in `run_tests()`
- Smoke script runs without syntax error: `python -m py_compile scripts/uat_smoke_test.py` exits 0

**action:**

**Step A — Add test functions after the existing test functions (before `run_tests()`):**

Add after `test_workflow_onboard_dry_run()` (after L166, before L168):

```python
# -------------------------------------------------------------------------
# RSP-01: detail=False summary mode
# -------------------------------------------------------------------------


def test_rsp01_interface_detail_summary_mode(client: NautobotClient):
    """RSP-01: interface_detail(detail=False) returns counts but no nested arrays."""
    result = run_workflow(
        client,
        workflow_id="interface_detail",
        params={"device": UAT_DEVICE, "detail": False},
    )
    assert result["status"] in ("ok", "partial"), f"Workflow failed: {result.get('error')}"
    data = result["data"]
    assert data is not None, "data must be present in summary mode"
    for unit in data.get("units", []):
        assert "families" in unit, "families key must be present in unit"
        assert unit["families"] == [], (
            f"families[] must be empty in detail=False, got {unit.get('families')}"
        )
        assert "family_count" in unit, "family_count must be present in summary mode"
        assert isinstance(unit["family_count"], int), "family_count must be an integer"


# -------------------------------------------------------------------------
# RSP-02: response_size_bytes in envelope
# -------------------------------------------------------------------------


def test_rsp02_response_size_bytes_in_envelope(client: NautobotClient):
    """RSP-02: All composite envelopes include response_size_bytes (positive int)."""
    composite_workflows = (
        "bgp_summary",
        "routing_table",
        "firewall_summary",
        "interface_detail",
    )
    for wf_id in composite_workflows:
        result = run_workflow(client, workflow_id=wf_id, params={"device": UAT_DEVICE})
        assert "response_size_bytes" in result, (
            f"{wf_id}: envelope missing response_size_bytes field"
        )
        assert isinstance(result["response_size_bytes"], int), (
            f"{wf_id}: response_size_bytes must be int, got {type(result['response_size_bytes'])}"
        )
        assert result["response_size_bytes"] > 0, (
            f"{wf_id}: response_size_bytes must be > 0, got {result['response_size_bytes']}"
        )


# -------------------------------------------------------------------------
# RSP-03: limit parameter caps result arrays
# -------------------------------------------------------------------------


def test_rsp03_limit_parameter_caps_results(client: NautobotClient):
    """RSP-03: limit=N independently caps each result array in composite workflows."""
    composite_workflows = (
        ("bgp_summary", "groups"),
        ("routing_table", "routes"),
        ("firewall_summary", "filters"),
        ("interface_detail", "units"),
    )
    for wf_id, top_key in composite_workflows:
        result = run_workflow(
            client,
            workflow_id=wf_id,
            params={"device": UAT_DEVICE, "limit": 2},
        )
        assert result["status"] in ("ok", "partial"), (
            f"{wf_id} with limit=2 failed: {result.get('error')}"
        )
        data = result["data"]
        assert data is not None, f"{wf_id}: data must not be None"
        items = data.get(top_key, [])
        assert len(items) <= 2, (
            f"{wf_id}: {top_key} must be capped at 2, got {len(items)} items"
        )
```

**Step B — Update `run_tests()` to include the RSP section:** After the existing workflow results block (after line 211, before `all_results = catalog_results + bridge_results + workflow_results`):

Add new RSP section:
```python
print("\n[ RSP-01/02/03 Response Ergonomics Tests ]")
rsp_results = [
    _run("RSP-01: interface_detail summary mode", lambda: test_rsp01_interface_detail_summary_mode(client)),
    _run("RSP-02: response_size_bytes in envelope", lambda: test_rsp02_response_size_bytes_in_envelope(client)),
    _run("RSP-03: limit parameter caps arrays", lambda: test_rsp03_limit_parameter_caps_results(client)),
]
```

Update `all_results` to include `rsp_results`:
```python
all_results = catalog_results + bridge_results + workflow_results + rsp_results
```

---

### Task 3.2 — Add RSP tests to `tests/test_workflows.py` (RSP-02 envelope tests)

**read_first:**
- `tests/test_workflows.py` (full file, 758 lines — existing `TestResponseSizeBytes`-style classes at end, `workflow_func_mock` helper at L70–84)

**acceptance_criteria:**
- `grep -n "class TestResponseSizeBytes" tests/test_workflows.py` finds the RSP-02 test class
- `grep -n "test_response_size_bytes_present" tests/test_workflows.py` finds the presence test
- `grep -n "test_response_size_bytes_equals_actual" tests/test_workflows.py` finds the value-accuracy test
- `grep -n "test_response_size_bytes_in_partial" tests/test_workflows.py` finds the partial envelope test
- `pytest tests/test_workflows.py -k "ResponseSize" --collect-only` shows at least 3 collected tests
- `pytest tests/test_workflows.py -k "ResponseSize" -v` exits 0

**action:**

Add at end of `tests/test_workflows.py` (after the last test, before the final blank line):

```python
# ---------------------------------------------------------------------------
# RSP-02: response_size_bytes in envelope (run_workflow integration)
# ---------------------------------------------------------------------------


class TestResponseSizeBytes:
    """RSP-02: All composite workflow envelopes include response_size_bytes."""

    @pytest.mark.parametrize("workflow_id", [
        "bgp_summary",
        "routing_table",
        "firewall_summary",
        "interface_detail",
    ])
    def test_response_size_bytes_present_in_ok_envelope(self, workflow_id):
        """response_size_bytes must be in envelope for all composite workflows."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"key": "value"}

        with workflow_func_mock(workflow_id, return_value=mock_result):
            client = MagicMock()
            result = run_workflow(
                client, workflow_id=workflow_id, params={"device": "rtr-01"}
            )

        assert "response_size_bytes" in result, (
            f"{workflow_id}: missing response_size_bytes field"
        )
        assert isinstance(result["response_size_bytes"], int), (
            f"{workflow_id}: response_size_bytes must be int"
        )
        assert result["response_size_bytes"] > 0, (
            f"{workflow_id}: response_size_bytes should be > 0, got {result['response_size_bytes']}"
        )

    def test_response_size_bytes_in_partial_envelope(self):
        """response_size_bytes present and positive in partial status envelope."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"x": 1}
        w = [{"operation": "list_af", "error": "timeout"}]
        with workflow_func_mock("bgp_summary", return_value=(mock_result, w)):
            client = MagicMock()
            result = run_workflow(
                client, workflow_id="bgp_summary", params={"device": "rtr-01"}
            )

        assert result["status"] == "partial"
        assert "response_size_bytes" in result
        assert result["response_size_bytes"] > 0

    def test_response_size_bytes_equals_actual_json_bytes(self):
        """response_size_bytes equals len(json.dumps(data)) after serialization."""
        mock_result = MagicMock()
        payload = {"groups": [{"id": "1", "name": "test"}], "total_groups": 1}
        mock_result.model_dump.return_value = payload

        with workflow_func_mock("bgp_summary", return_value=mock_result):
            client = MagicMock()
            result = run_workflow(
                client, workflow_id="bgp_summary", params={"device": "rtr-01"}
            )

        import json
        expected = len(json.dumps(payload))
        assert result["response_size_bytes"] == expected, (
            f"Expected {expected}, got {result['response_size_bytes']}"
        )

    def test_response_size_bytes_zero_on_hard_error(self):
        """response_size_bytes is 0 when the workflow raises an exception."""
        with workflow_func_mock("bgp_summary") as mock_func:
            mock_func.side_effect = RuntimeError("connection refused")

            client = MagicMock()
            result = run_workflow(
                client, workflow_id="bgp_summary", params={"device": "rtr-01"}
            )

        assert result["status"] == "error"
        assert result["data"] is None
        assert result["response_size_bytes"] == 0
```

---

### Task 3.3 — Add RSP tests to `tests/test_cms_composites.py` (RSP-01 + RSP-03 domain tests)

**read_first:**
- `tests/test_cms_composites.py` (full file — mock helpers at L29–120, existing interface tests L244–306, existing bgp tests L130–200, existing firewall tests L314–380)

**acceptance_criteria:**
- `grep -n "def test_interface_detail_summary_mode" tests/test_cms_composites.py` finds the RSP-01 summary mode test
- `grep -n "def test_interface_detail_summary_mode_strips_nested_arrays" tests/test_cms_composites.py` finds the nested-array strip test
- `grep -n "def test_interface_detail_summary_mode_does_not_affect_arp" tests/test_cms_composites.py` finds the ARP independence test
- `grep -n "def test_bgp_summary_limit" tests/test_cms_composites.py` finds the RSP-03 limit test
- `grep -n "def test_interface_detail_limit" tests/test_cms_composites.py` finds the interface limit test
- `pytest tests/test_cms_composites.py -k "summary_mode or limit" --collect-only` shows at least 4 collected tests
- `pytest tests/test_cms_composites.py -v` exits 0 (all tests pass including existing ones)

**action:**

Add at end of `tests/test_cms_composites.py` (after the existing firewall test section):

```python
# ---------------------------------------------------------------------------
# RSP-01: detail=False summary mode for interface_detail
# ---------------------------------------------------------------------------


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

    vrrp = MagicMock()
    vrrp.model_dump.return_value = {"id": "vrrp-001", "group_number": 1}

    with patch(
        "nautobot_mcp.cms.interfaces.list_interface_units",
        return_value=_mock_list_response(unit),
    ) as mock_units, patch(
        "nautobot_mcp.cms.interfaces.list_interface_families",
        return_value=_mock_list_response(fam),
    ) as mock_fams, patch(
        "nautobot_mcp.cms.interfaces.list_vrrp_groups",
        return_value=_mock_list_response(vrrp),
    ) as mock_vrrp:
        result, warnings = get_interface_detail(client, device="edge-01", detail=False)

    assert isinstance(result, InterfaceDetailResponse)
    assert result.device_name == "edge-01"
    assert result.total_units == 1
    assert len(result.units) == 1
    assert result.units[0]["families"] == [], (
        "families[] must be stripped (empty list) in detail=False mode"
    )
    assert "family_count" in result.units[0], "family_count must be present in summary mode"
    assert result.units[0]["family_count"] == 1
    assert "vrrp_group_count" in result.units[0], "vrrp_group_count must be present in summary mode"
    assert result.units[0]["vrrp_group_count"] == 1, "vrrp_group_count should reflect actual VRRP count"
    # VRRP query SHOULD be called (even in summary mode, we query per family for count)
    mock_vrrp.assert_called()
    assert warnings == []


def test_interface_detail_summary_mode_does_not_affect_arp():
    """RSP-01: detail=False does not affect include_arp behavior (ARP controlled by include_arp)."""
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()
    unit = MagicMock()
    unit.id = "unit-002"
    unit.model_dump.return_value = {"id": "unit-002", "interface_name": "ge-0/0/1"}

    fam = MagicMock()
    fam.id = "fam-002"
    fam.model_dump.return_value = {"id": "fam-002", "family_type": "inet"}

    arp_entry = MagicMock()
    arp_entry.model_dump.return_value = {
        "id": "arp-001",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "ip_address": "10.0.0.1/24",
    }

    with patch(
        "nautobot_mcp.cms.interfaces.list_interface_units",
        return_value=_mock_list_response(unit),
    ), patch(
        "nautobot_mcp.cms.interfaces.list_interface_families",
        return_value=_mock_list_response(fam),
    ), patch(
        "nautobot_mcp.cms.interfaces.list_vrrp_groups",
        return_value=_mock_list_response(),
    ), patch(
        "nautobot_mcp.cms.arp.list_arp_entries",
        return_value=_mock_list_response(arp_entry),
    ):
        result, warnings = get_interface_detail(
            client, device="edge-02", include_arp=True, detail=False
        )

    assert result.units[0]["families"] == [], "families[] still stripped when include_arp=True"
    assert len(result.arp_entries) == 1, "ARP entries should be present when include_arp=True"
    assert result.arp_entries[0]["mac_address"] == "aa:bb:cc:dd:ee:ff"


def test_interface_detail_detail_true_unchanged():
    """RSP-01: get_interface_detail(detail=True) behavior is unchanged from default."""
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()
    unit = MagicMock()
    unit.id = "unit-003"
    unit.model_dump.return_value = {"id": "unit-003", "interface_name": "ge-0/0/2"}

    fam = MagicMock()
    fam.id = "fam-003"
    fam.model_dump.return_value = {"id": "fam-003", "family_type": "inet6"}

    vrrp = MagicMock()
    vrrp.model_dump.return_value = {"id": "vrrp-003", "group_number": 10}

    with patch(
        "nautobot_mcp.cms.interfaces.list_interface_units",
        return_value=_mock_list_response(unit),
    ) as mock_units, patch(
        "nautobot_mcp.cms.interfaces.list_interface_families",
        return_value=_mock_list_response(fam),
    ) as mock_fams, patch(
        "nautobot_mcp.cms.interfaces.list_vrrp_groups",
        return_value=_mock_list_response(vrrp),
    ) as mock_vrrp:
        result, warnings = get_interface_detail(client, device="edge-03", detail=True)

    assert isinstance(result, InterfaceDetailResponse)
    assert len(result.units) == 1
    # In detail=True mode, families should NOT be stripped
    assert len(result.units[0]["families"]) == 1, "families[] must be populated in detail=True"
    assert result.units[0]["families"][0]["vrrp_group_count"] == 1
    assert "vrrp_groups" in result.units[0]["families"][0]
    mock_vrrp.assert_called()


# ---------------------------------------------------------------------------
# RSP-03: limit parameter for all 4 composites
# ---------------------------------------------------------------------------


def test_bgp_summary_limit_caps_groups_and_neighbors():
    """RSP-03: bgp_summary(limit=N) caps groups[] and neighbors[] independently."""
    from nautobot_mcp.cms.routing import get_device_bgp_summary

    client = _mock_client()
    grps = [_mock_bgp_group(id_=f"grp-{i}") for i in range(5)]
    nbrs = [_mock_bgp_neighbor(id_=f"nbr-{i}", group_id="grp-0") for i in range(5)]

    with patch(
        "nautobot_mcp.cms.routing.list_bgp_groups",
        return_value=_mock_list_response(*grps),
    ), patch(
        "nautobot_mcp.cms.routing.list_bgp_neighbors",
        return_value=_mock_list_response(*nbrs),
    ):
        result, warnings = get_device_bgp_summary(client, device="rtr-01", limit=3)

    assert len(result.groups) <= 3, f"groups[] must be capped at 3, got {len(result.groups)}"
    for grp in result.groups:
        assert len(grp.get("neighbors", [])) <= 3, (
            f"neighbors[] per group must be capped at 3, got {len(grp.get('neighbors', []))}"
        )


def test_routing_table_limit_caps_routes():
    """RSP-03: routing_table(limit=N) caps routes[]."""
    from nautobot_mcp.cms.routing import get_device_routing_table

    client = _mock_client()
    routes = [_mock_static_route(id_=f"rt-{i}", destination=f"10.{i}.0.0/16") for i in range(5)]

    with patch(
        "nautobot_mcp.cms.routing.list_static_routes",
        return_value=_mock_list_response(*routes),
    ):
        result, warnings = get_device_routing_table(client, device="rtr-01", limit=2)

    assert len(result.routes) <= 2, f"routes[] must be capped at 2, got {len(result.routes)}"


def test_firewall_summary_limit_caps_filters_and_policers():
    """RSP-03: firewall_summary(limit=N) caps filters[] and policers[] independently."""
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary

    client = _mock_client()
    fw_filters = [_mock_fw_filter(id_=f"fw-{i}") for i in range(5)]
    fw_policers = [_mock_fw_policer(id_=f"pol-{i}") for i in range(5)]

    with patch(
        "nautobot_mcp.cms.firewalls.list_firewall_filters",
        return_value=_mock_list_response(*fw_filters),
    ), patch(
        "nautobot_mcp.cms.firewalls.list_firewall_policers",
        return_value=_mock_list_response(*fw_policers),
    ):
        result, warnings = get_device_firewall_summary(client, device="fw-01", limit=2)

    assert len(result.filters) <= 2, f"filters[] must be capped at 2, got {len(result.filters)}"
    assert len(result.policers) <= 2, f"policers[] must be capped at 2, got {len(result.policers)}"


def test_interface_detail_limit_caps_units_and_families():
    """RSP-03: interface_detail(limit=N) caps units[] and caps families[] per unit."""
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()
    units = [MagicMock(id=f"unit-{i}", model_dump=lambda i=i: {"id": f"unit-{i}", "interface_name": f"ge-0/0/{i}"}) for i in range(5)]
    # Give each unit 3 families
    for u in units:
        families_per_unit = [
            MagicMock(id=f"fam-{u.id}-{j}", model_dump=lambda j=j: {"id": f"fam-{j}", "family_type": "inet"})
            for j in range(3)
        ]
        with patch(
            "nautobot_mcp.cms.interfaces.list_interface_units",
            return_value=_mock_list_response(*units),
        ), patch(
            "nautobot_mcp.cms.interfaces.list_interface_families",
            return_value=_mock_list_response(*families_per_unit),
        ), patch(
            "nautobot_mcp.cms.interfaces.list_vrrp_groups",
            return_value=_mock_list_response(),
        ):
            result, warnings = get_interface_detail(client, device="edge-01", limit=2)

    assert len(result.units) <= 2, f"units[] must be capped at 2, got {len(result.units)}"
    for unit in result.units:
        assert len(unit.get("families", [])) <= 2, (
            f"families[] per unit must be capped at 2, got {len(unit.get('families', []))}"
        )
```

---

## Wave 4 — UAT Validation

---

### Task 4.1 — Run smoke script against Nautobot dev server

**acceptance_criteria:**
- `python scripts/uat_smoke_test.py` exits 0
- Output shows `[PASS]` for all 3 RSP smoke tests
- Output shows no `[FAIL]` entries

**action:**

```bash
python scripts/uat_smoke_test.py
```

If the dev server is unavailable, the smoke script will print a connection error and exit non-zero. Report the error but note that the smoke test itself is correctly written (connection failures are server-side, not implementation errors).

---

### Task 4.2 — Run pytest suite

**acceptance_criteria:**
- `pytest tests/test_workflows.py -v --tb=short` exits 0 — all tests pass including new `TestResponseSizeBytes` class
- `pytest tests/test_cms_composites.py -v --tb=short` exits 0 — all tests pass including new RSP-01 and RSP-03 tests
- `pytest tests/ -v --tb=short -k "not live"` exits 0 — no regressions in other test files
- Test count: at least 3 new tests in `test_workflows.py`, at least 6 new tests in `test_cms_composites.py`

**action:**

```bash
pytest tests/test_workflows.py tests/test_cms_composites.py -v --tb=short
pytest tests/ -v --tb=short -k "not live"  # full suite, exclude live tests
```

---

## Verification Summary

| Requirement | Acceptance Criterion | Verification |
|-------------|---------------------|--------------|
| RSP-01 | `interface_detail(detail=False)` strips `families[]` and `vrrp_groups[]`, keeps counts | `grep "families = \[\]" interfaces.py` + pytest `test_interface_detail_summary_mode_strips_nested_arrays` |
| RSP-01 | `detail=True` is backward-compatible default | Existing `test_interface_detail_default` still passes |
| RSP-01 | `arp_entries` unaffected by `detail` param | `test_interface_detail_summary_mode_does_not_affect_arp` passes |
| RSP-02 | `response_size_bytes` in all composite envelopes | `grep "response_size_bytes" workflows.py` + `TestResponseSizeBytes` tests pass |
| RSP-02 | `response_size_bytes` = `len(json.dumps(data))` | `test_response_size_bytes_equals_actual_json_bytes` passes |
| RSP-03 | `limit=N` caps each composite's arrays independently | All 4 `test_*_limit_*` domain tests pass + smoke test passes |
| RSP-03 | `limit=0` (default) means no cap | Smoke test with default params returns full data |
| WFC-03 | `_validate_registry()` passes after all changes | Module imports without `NautobotValidationError` |
| Smoke | All 3 RSP smoke tests `[PASS]` | `python scripts/uat_smoke_test.py` exits 0 |
| Pytest | All new + existing tests pass | `pytest tests/ -k "not live" -v --tb=short` exits 0 |
