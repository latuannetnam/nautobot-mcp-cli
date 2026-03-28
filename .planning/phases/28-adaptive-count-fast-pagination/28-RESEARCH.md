# Phase 28: Adaptive Count & Fast Pagination — Research

**Phase:** 28-adaptive-count-fast-pagination
**Research date:** 2026-03-28
**Status:** Ready for planning

---

## 1. How pynautobot's `count()` Actually Works

**Finding:** `count()` uses **auto-pagination**, NOT the `/count/` endpoint.

The comment at `devices.py` L247 (`"# .count(device=name) hits /count/?device=... (OK)"`) is **incorrect**. Tracing through pynautobot's source:

- `endpoint_accessor.count(**filters)` internally calls `self.filter(**filters)` then calls `len()` on the generator — triggering **full auto-pagination** across all pages.
- On Nautobot v2, auto-pagination means sequential GET requests to the list endpoint until `next=null` is exhausted.
- For a device with 700+ interfaces, this means 700+ results fetched just to compute a count — a separate, expensive round-trip before the actual data fetch.

**Phase 29** replaces `count()` with direct `/count/` endpoint calls, but Phase 28 works around this by **skipping the call entirely** when not needed.

**Evidence from code:** `get_device_inventory()` calls `client.api.dcim.interfaces.count(device=device_name)` — no `id__in` batching, no `/count/` endpoint. This blocks on full pagination.

---

## 2. `skip_count` in `get_device_inventory()` — Type Signature

**File:** `nautobot_mcp/devices.py` L267–358

Current signature:
```python
def get_device_inventory(
    client: NautobotClient,
    name: Optional[str] = None,
    device: Optional[str] = None,
    detail: Literal["interfaces", "ips", "vlans", "all"] = "interfaces",
    limit: int = 50,
    offset: int = 0,
) -> DeviceInventoryResponse:
```

**Proposed new signature:**
```python
def get_device_inventory(
    client: NautobotClient,
    name: Optional[str] = None,
    device: Optional[str] = None,
    detail: Literal["interfaces", "ips", "vlans", "all"] = "interfaces",
    limit: int = 50,
    offset: int = 0,
    skip_count: bool = False,
) -> DeviceInventoryResponse:
```

Adding `skip_count: bool = False` is backward-compatible:
- All existing callers omit it → defaults to `False` (current behavior).
- Phase 29 will use `skip_count=True` in auto-pagination scenarios.

**Effect on workflow registry** (`nautobot_mcp/workflows.py` L167–176):
```python
"devices_inventory": {
    "function": get_device_inventory,
    "param_map": {
        "device": "name",
        "detail": "detail",
        "limit": "limit",
        "offset": "offset",
    },
    "required": ["device"],
},
```
The registry does NOT list `skip_count` — that's intentional (D-03: agents get CLI-level control, not `skip_count` exposure). The registry is unaffected by this parameter addition since it's optional with a default.

---

## 3. `--no-count` Flag in CLI

**File:** `nautobot_mcp/cli/devices.py` L146–194

Current `devices_inventory` command:
```python
@devices_app.command("inventory")
def devices_inventory(
    ctx: typer.Context,
    name: str = typer.Argument(help="Device name"),
    detail: str = typer.Option("interfaces", "--detail", ...),
    limit: int = typer.Option(50, "--limit", ...),
    offset: int = typer.Option(0, "--offset", ...),
) -> None:
```

**Proposed change:** Add `no_count: bool = typer.Option(False, "--no-count/")`:
```python
@devices_app.command("inventory")
def devices_inventory(
    ctx: typer.Context,
    name: str = typer.Argument(help="Device name"),
    detail: str = typer.Option("interfaces", "--detail", ...),
    limit: int = typer.Option(50, "--limit", ...),
    offset: int = typer.Option(0, "--offset", ...),
    no_count: bool = typer.Option(False, "--no-count/"),
) -> None:
```

Then pass through to the function:
```python
result = devices.get_device_inventory(
    client, name=name, detail=detail, limit=limit, offset=offset,
    skip_count=no_count,
)
```

**D-06:** `--limit 0` also implies `skip_count=True`. Logic: `skip_count = no_count or limit == 0`.

---

## 4. `skip_count` in `call_nautobot()` in the Bridge

**File:** `nautobot_mcp/bridge.py` L322–396

Current signature:
```python
def call_nautobot(
    client,
    endpoint: str,
    method: str = "GET",
    params: Optional[dict] = None,
    body: Optional[dict] = None,
    data: Optional[dict] = None,
    id: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict:
```

This function does **not currently call `count()` anywhere** — it uses `limit`/`offset` directly on list endpoints (L186–189). So `skip_count` has **no functional effect in `_execute_core` or `_execute_cms` today**. Adding it here is for future-proofing and MCP agent parity (D-03), not for immediate behavior change in Phase 28.

**Proposed signature:**
```python
def call_nautobot(
    client,
    endpoint: str,
    method: str = "GET",
    params: Optional[dict] = None,
    body: Optional[dict] = None,
    data: Optional[dict] = None,
    id: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    skip_count: bool = False,  # NEW — for future Phase 29 use
) -> dict:
```

No changes to `_execute_core` or `_execute_cms` are needed in Phase 28 — `skip_count` is simply accepted and discarded. Phase 29 will wire it up.

---

## 5. Parallel Counts with `ThreadPoolExecutor`

**File:** `nautobot_mcp/cms/routing.py` — existing pattern at L659–775 (in `get_device_bgp_summary`)

No ThreadPoolExecutor pattern exists in routing.py — the bulk enrichment uses sequential fetches with fallback-on-error. However, the **CMS client itself** (`nautobot_mcp/cms/client.py`) has no threading either. The D-05 decision (parallel counts for `detail=all`) requires a new pattern.

**Implementation approach:**
```python
from concurrent.futures import ThreadPoolExecutor

if detail == "all" and not skip_count:
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_iface = ex.submit(client.api.dcim.interfaces.count, device=device_name)
        f_ips   = ex.submit(ipam_mod.get_device_ips, client, device_name=device_name, limit=0, offset=0)
        f_vlans = ex.submit(
            client.api.ipam.vlans.count,
            location=device_obj.location.name if device_obj.location else None
        )
        total_interfaces = f_iface.result()
        ips_resp = f_ips.result()
        total_vlans = f_vlans.result() if device_obj.location else 0
        total_ips = ips_resp.total_ips
```

**Key constraints:**
- `client.api` is a pynautobot `api` object. Its HTTP session (`api.http_session`) is thread-safe for concurrent requests using the same `requests.Session` — Python's `requests.Session` is thread-safe.
- The pynautobot `api.dcim.interfaces.count()` call makes a **new HTTP request per call**, so parallelizing them is safe.
- Need to handle exceptions per-thread: wrap each `future.result()` in try/except to prevent one failure from crashing the whole operation.
- For Phase 28, the parallel block is only activated when `detail == "all"` AND `not skip_count` — all other paths remain sequential.

**Sequential fallback when parallel fails:** If any thread raises, fall back to sequential (D-05 says parallel is an optimization, not a contract).

---

## 6. Timing — Per-Section vs Aggregate

**D-04 decision:** Per-section timing: `interfaces_latency_ms`, `ips_latency_ms`, `vlans_latency_ms`, `total_latency_ms`.

The `DeviceInventoryResponse` model (`models/device.py` L83–104) does **not** currently have timing fields. Two options:

### Option A: Add timing fields to `DeviceInventoryResponse` (model change)
```python
# models/device.py
interfaces_latency_ms: Optional[float] = Field(default=None, description="Wall-clock ms for interfaces fetch")
ips_latency_ms:        Optional[float] = Field(default=None, description="Wall-clock ms for IPs fetch")
vlans_latency_ms:      Optional[float] = Field(default=None, description="Wall-clock ms for VLANs fetch")
total_latency_ms:      Optional[float] = Field(default=None, description="Total wall-clock ms")
```

This is the cleanest approach — timing travels with the response. Requires a model change (adds 4 optional fields).

### Option B: Add timing at CLI output layer only
The CLI `--json` output formats `result.model_dump()` — timing could be injected as a post-model dict addition in `devices_inventory()` before formatting. Does **not** change the Pydantic model, but means timing is only visible in `--json` mode.

**Decision:** Option A (model fields). The CONTEXT says "Timing metadata should be added only in `--json` output mode" but that refers to **display**, not storage. Adding fields to the model means:
- `--json` output shows them (success criterion 5).
- Non-JSON text output ignores them (they don't appear in text rendering).
- MCP callers receive them transparently.

**Implementation pattern:**
```python
import time

t0 = time.time()

if detail in ("interfaces", "all"):
    t_iface = time.time()
    total_interfaces = client.api.dcim.interfaces.count(device=device_name) if not skip_count else None
    interfaces_latency_ms = (time.time() - t_iface) * 1000
    # ...
```

For the `total_latency_ms`, measure from `t_start = time.time()` at the very top of `get_device_inventory()`, set it just before returning.

---

## 7. `DeviceInventoryResponse` Field Types — Optional vs Required

**File:** `nautobot_mcp/models/device.py` L83–104

Current fields:
```python
total_interfaces: int = Field(default=0, description="Total interface count")
total_ips:        int = Field(default=0, description="Total IP count")
total_vlans:      int = Field(default=0, description="Total VLAN count")
```

These are `int`, not `Optional[int]`. Per **D-02**: `total_*` should be `null` (Python `None`) when count is skipped.

**Required change:**
```python
total_interfaces: Optional[int] = Field(default=None, description="Total interface count (null if count skipped)")
total_ips:        Optional[int] = Field(default=None, description="Total IP count (null if count skipped)")
total_vlans:      Optional[int] = Field(default=None, description="Total VLAN count (null if count skipped)")
```

This is a type change (from `int` to `Optional[int]`) but **backward compatible** in practice:
- Default is `None` — when count is skipped, totals are `None`.
- When count IS fetched (current behavior), they remain `int`.
- All downstream code should handle `None` gracefully (Pydantic allows `None` in JSON output as `null`).

Also need to update the **CLI text rendering** in `devices_inventory` (L171–174):
```python
# Current:
typer.echo(f"  Interfaces: {data['total_interfaces']} total")
# Must handle None:
typer.echo(f"  Interfaces: {data['total_interfaces'] if data['total_interfaces'] is not None else '?'} total")
```

---

## 8. Workflow Registry Impact

**File:** `nautobot_mcp/workflows.py` L167–176

```python
"devices_inventory": {
    "function": get_device_inventory,
    "param_map": {
        "device": "name",
        "detail": "detail",
        "limit": "limit",
        "offset": "offset",
    },
    "required": ["device"],
},
```

**Impact of Phase 28 changes:**

| Change | Registry impact |
|--------|----------------|
| `skip_count: bool = False` added to function | None — optional param, no default in registry needed |
| `total_interfaces` becomes `Optional[int]` | None — return type changes but model stays compatible |
| `has_more` changes logic when count skipped | None — return type unchanged |
| Timing fields added to model | None — extra fields in serialized output are fine |

**Verification:** The `_validate_registry()` function (L42–91) checks that `required ∪ mapped_params ⊆ signature_params`. Since `skip_count` is optional (has default), it is NOT in `required` or `param_map`, so it doesn't need to be in the registry. The registry is **completely unaffected** by Phase 28.

---

## 9. `get_device_summary()` — Count Calls Also Expensive There

**File:** `nautobot_mcp/devices.py` L228–264

`get_device_summary()` calls:
1. `client.api.dcim.interfaces.count(device=name)` — auto-paginates all interfaces
2. `client.api.ipam.ip_addresses.count(device_id=device_uuid)` — auto-paginates all IPs
3. `client.api.ipam.vlans.count(location=device_location)` — auto-paginates all VLANs

These are used by `devices summary` CLI command. Phase 28 scope is `get_device_inventory()` only, but Phase 29 will apply the same `/count/` endpoint fix to `get_device_summary()`.

**Note for planning:** Do NOT modify `get_device_summary()` in Phase 28 — scope creep risk. Flag it for Phase 29.

---

## 10. Summary: Changes Required Per File

| File | Changes |
|------|---------|
| `nautobot_mcp/models/device.py` | Change `total_interfaces/ips/vlans` from `int` to `Optional[int]`; add `interfaces_latency_ms`, `ips_latency_ms`, `vlans_latency_ms`, `total_latency_ms` fields |
| `nautobot_mcp/devices.py` | Add `skip_count` param to `get_device_inventory()`; conditional count logic; parallel counts via ThreadPoolExecutor for `detail=all`; `None` totals when skipped; `has_more` inference; per-section timing |
| `nautobot_mcp/cli/devices.py` | Add `--no-count` flag; `skip_count = no_count or limit == 0`; handle `None` totals in text output; include timing in JSON output |
| `nautobot_mcp/bridge.py` | Add `skip_count` param to `call_nautobot()` (future Phase 29 wiring, no-op in Phase 28) |
| `nautobot_mcp/workflows.py` | No changes — registry unaffected |

---

## 11. Test Implications

- `tests/test_devices.py` — any existing tests for `get_device_inventory()` that assert on `total_interfaces` being `int` will break (now `Optional[int]`). Need to update assertions to `assert result.total_interfaces is None` for skip-count scenarios.
- `tests/test_workflows.py` — if `devices_inventory` workflow is tested, check timing fields are handled gracefully.
- `tests/test_cli.py` — add `--no-count` flag test coverage.
- **No live credentials needed** for unit tests — can mock pynautobot responses.

---

## 12. Open Questions / Risk Items

1. **Thread safety of pynautobot session:** The `api.http_session` (a `requests.Session`) is thread-safe, but pynautobot's internal `api.dcim.interfaces` accessor may hold state. Risk: low, but worth a note. If parallel counts cause issues, the sequential fallback covers it.

2. **D-06 edge case: `--limit 0 --no-count`:** Both flags set `skip_count=True`. No conflict — both conditions OR together.

3. **`get_device_ips()` for count:** When counting IPs for `total_ips`, the code currently calls `ipam_mod.get_device_ips(..., limit=0, offset=0)` which fetches ALL IPs. With `skip_count=True`, this whole bulk fetch is skipped and `total_ips=None`. This is correct — we don't need the count.

4. **Timing on the device_obj fetch:** `get_device()` is called before any section timing starts. Should it be included in `total_latency_ms`? Per D-04, "wall-clock from first call to final output" — yes, include it. `t_start` should be at the very top of `get_device_inventory()`, before `get_device()`.

5. **Phase 28 vs Phase 29 boundary clarity:** Phase 28 only touches `get_device_inventory()`. Phase 29 replaces all `count()` calls with `/count/` endpoint and applies parallel counting more broadly. The ThreadPoolExecutor for parallel counts (D-05) IS in Phase 28 scope, but only for `detail=all` in `get_device_inventory()`.
