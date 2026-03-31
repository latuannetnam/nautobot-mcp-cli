# Architecture Research

**Domain:** CMS N+1 Query Elimination
**Researched:** 2026-03-31
**Confidence:** HIGH

---

## How the CMS Client Architecture Supports Parallel HTTP Calls

### What prevents N+1 today

`cms/client.py` is a **stateless helper module**. Functions `cms_list`, `cms_get`, `cms_create`, `cms_update`, `cms_delete` carry no connection state — each call immediately delegates to pynautobot:

```python
def cms_list(client, endpoint_name, model_cls, limit=0, offset=0, **filters):
    endpoint = get_cms_endpoint(client, endpoint_name)
    records = list(endpoint.filter(**filters, **pagination_kwargs))
    return ListResponse(count=len(all_results), results=all_results)
```

The `client` is a `NautobotClient` instance. Its `api` property exposes a **shared `requests.Session`** (`client.api.http_session`) with auth headers already attached:

```python
# client.py — auth is baked into the shared session at init
self._api.http_session.headers["Authorization"] = f"Token {self._profile.token}"
self._api.http_session.headers["Accept"] = "application/json"
```

`requests.Session` is **thread-safe** for concurrent use — connections are reused via the adapter pool. This means any function that accepts `client` as a parameter can safely be called from a `ThreadPoolExecutor` worker, and all workers share the authenticated session without re-authenticating.

### What already uses this pattern

`devices.py` `get_device_inventory()` (v1.6 Phase 27) uses `ThreadPoolExecutor(max_workers=3)` to run `count`, `get_device_ips`, and `_count_vlans_by_loc` in parallel:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as ex:
    f_iface = ex.submit(client.count, "dcim", "interfaces", device=device_name)
    f_ips   = ex.submit(ipam_mod.get_device_ips, client, device_name=device_name, limit=0, offset=0)
    f_vlans = ex.submit(_count_vlans_by_loc, client, loc_id)
    total_interfaces = f_iface.result()
    ips_resp = f_ips.result()
    vlans_result = f_vlans.result()
```

This is the **proven pattern to replicate** in CMS workflows.

### The `_CMS_BULK_LIMIT = 200` foundation

v1.8 Phase 33 already eliminated per-record sequential pagination (PAGE_SIZE=1 → PAGE_SIZE=200) by setting `limit=200` when `limit=0` in `cms_list()`. This means each `cms_list()` call now generates **ceil(N/200) HTTP calls** instead of **N calls**. But it does not eliminate the **sequential chain** of dependent `cms_list()` calls in the composite functions — that is the remaining N+1.

---

## Relationship Between Layers

```
CLI  (nautobot_mcp/cli/cms_*.py)
  │
  ▼
Workflow Dispatcher  (nautobot_mcp/workflows.py → WORKFLOW_REGISTRY)
  │
  ▼
Composite Domain Functions  (nautobot_mcp/cms/{routing,routing,firewalls,interfaces}.py)
  │  ← get_device_bgp_summary, get_device_routing_table,
  │     get_device_firewall_summary, get_interface_detail
  ▼
CMS CRUD Domain Functions  (same files, lower section)
  │  ← list_firewall_filters, list_interface_units, etc.
  ▼
cms/client.py helpers  (cms_list, cms_get, cms_create, cms_update, cms_delete)
  │
  ▼
pynautobot  (client.api.dcim.*, client.api.cms.*)
  │
  ▼
client.api.http_session  ← shared requests.Session with auth
  │
  ▼
Nautobot REST API  (https://nautobot.netnam.vn/api/*)
```

The CLI layer and the workflow layer both call the **same CMS domain functions** — they share the entire call stack. Any parallelization added to CMS domain functions benefits both CLI and MCP callers simultaneously with no extra work.

---

## Identified N+1 Hotspots

### 🔴 Hotspot 1 — `get_interface_detail` (interfaces.py, lines 690–692)

**Pattern:** Sequential loop over units, each iteration makes one `cms_list()` call.

```python
# CURRENT — sequential N calls, one per unit
unit_families: dict[str, list] = {}
for unit in units:                          # ← N iterations (HQV-PE1-NEW: 709 units)
    families = list_interface_families(client, unit_id=unit.id, limit=0)
    unit_families[unit.id] = families.results
```

For a device with 709 interface units, this makes **709 sequential HTTP calls**. The fix: pre-fetch all families for all units in **1 bulk call** upfront, then distribute in-memory:

```python
# FIXED — 1 bulk call, O(1) distribution
all_families = list_interface_families(client, device=device_id, limit=0)
family_by_unit: dict[str, list] = {}
for fam in all_families.results:
    family_by_unit.setdefault(fam.unit_id, []).append(fam)
```

### 🔴 Hotspot 2 — `get_device_firewall_summary` detail loop (firewalls.py, lines 707–717)

**Pattern:** Sequential loop over filters, each iteration makes one `cms_list()` call.

```python
# CURRENT — sequential N calls, one per filter
filter_dicts = []
for fw_filter in filters_data:              # ← N iterations
    terms_resp = list_firewall_terms(client, filter_id=fw_filter.id, limit=0)
    fd["terms"] = [t.model_dump() for t in terms_resp.results]
```

Fix: pre-fetch all terms for all filters in **1 bulk call** (already done in the `list_firewall_filters` co-primary), then distribute in-memory.

### 🟡 Hotspot 3 — `_get_vrrp_for_family` lazy cache (interfaces.py, lines 696–705)

**Pattern:** Sequential loop over families, each makes one `cms_list()` call on first encounter.

```python
# CURRENT — up to M sequential calls, one per unique family
for unit in units:
    for fam in families_results:
        fam_vrrp = _get_vrrp_for_family(fam.id)   # ← cached after first call per family
```

M is bounded by the number of unique family IDs (typically far fewer than units). But the sequential chain per family is still N+1 if called in a tight loop. Fix: pre-fetch all VRRP groups for all families in **1 bulk call** before the unit loop.

### 🟡 Hotspot 4 — `get_firewall_term` enrichment (firewalls.py, lines 438–465)

**Pattern:** Two sequential `cms_list()` calls inside a `get_firewall_term` function called per term.

```python
# Called from list_firewall_terms → for each term → sequential MC + actions fetch
mc = cms_list(client, "juniper_firewall_match_conditions", ..., term=id, limit=0)
actions = cms_list(client, "juniper_firewall_actions", ..., term=id, limit=0)
```

This is read-only; `list_firewall_terms` already does the bulk-prefetch-with-count fallback pattern. No action needed unless called standalone from CLI/MCP.

### 🟢 Hotspot 5 — `list_bgp_neighbors` fallback (routing.py, lines 460–470)

**Pattern:** Sequential loop over BGP groups to fetch neighbors when direct device filter fails.

```python
# Fallback only — v1.9 Phase 34 fixed the primary path
groups = cms_list(client, "juniper_bgp_groups", ..., device=device_id, limit=0)
for grp in groups.results:                  # ← only hit when device filter fails
    nbrs = cms_list(client, "juniper_bgp_neighbors", ..., group=grp.id)
```

Only triggers when the `juniper_bgp_neighbors` endpoint doesn't support the `device` filter directly. The primary path is already bulk. **No action needed** — the fallback is for edge-case environments.

---

## Integration Points

### Existing — what must not break

| Caller | Call site | Pattern |
|--------|-----------|---------|
| `workflows.py` | `get_device_bgp_summary` → `list_bgp_groups`, `list_bgp_neighbors` | Composite function returning `(result, warnings)` |
| `workflows.py` | `get_device_routing_table` → `list_static_routes` | Composite function returning `(result, warnings)` |
| `workflows.py` | `get_device_firewall_summary` → `list_firewall_filters`, `list_firewall_policers` | Composite function returning `(result, warnings)` |
| `workflows.py` | `get_interface_detail` → `list_interface_units`, `list_interface_families` | Composite function returning `(result, warnings)` |
| `cli/cms_*.py` | All CMS CRUD functions (thin wrappers) | Return raw model objects |
| `cms/arp.py` | ARP enrichment (imported dynamically) | Optional enrichment |

### New — what to add

| Component | Location | Purpose |
|-----------|----------|---------|
| `_cms_bulk_families_by_unit()` | `cms/client.py` or `cms/interfaces.py` | Pre-fetch all families for all units on a device in 1 call |
| `_cms_bulk_vrrp_by_family()` | `cms/client.py` or `cms/interfaces.py` | Pre-fetch all VRRP groups for all families on a device in 1 call |
| `_cms_bulk_terms_by_filter()` | `cms/client.py` or `cms/firewalls.py` | Pre-fetch all terms for all filters on a device in 1 call |
| `_cms_bulk_actions_by_policer()` | `cms/client.py` or `cms/firewalls.py` | Pre-fetch all actions for all policers on a device in 1 call |

### Thread-safety guarantee

The `NautobotClient` instance is **shareable across ThreadPoolExecutor workers** because:
- `requests.Session` is thread-safe (connection reuse via urllib3 pool)
- Auth token is attached to the session once at `api` property access time
- pynautobot's `Endpoint` objects are stateless wrappers around the session
- The `WarningCollector` is **not** thread-safe — each worker must capture its own errors; collect in the main thread after `as_completed()`

---

## Data Flow Changes

### `get_interface_detail` — current vs fixed

```
CURRENT (N+1):
  1. Fetch all units (1 call)
  2. for unit in units:            ← N iterations (709 on HQV-PE1-NEW)
       fetch families for unit     ← N sequential calls
  3. for unit in units:
       for family in families:
         fetch VRRP for family     ← M sequential calls, M << N

FIXED (2+1):
  1. Fetch all units (1 call)
  2. Fetch all families for device (1 bulk call) → dict by unit_id
  3. Fetch all VRRP groups for device (1 bulk call) → dict by family_id
  4. for unit in units: enrich in-memory from dicts  ← O(N), no HTTP
```

### `get_device_firewall_summary` — current vs fixed (detail mode)

```
CURRENT (N+1):
  1. Fetch filters (1 call)
  2. Fetch policers (1 call) [co-primary, parallel already]
  3. for filter in filters:       ← N iterations
       fetch terms for filter     ← N sequential calls
  4. for policer in policers:     ← M iterations
       fetch actions for policer ← M sequential calls

FIXED (4 total):
  1. Fetch filters (1 call)
  2. Fetch policers (1 call)
  3. Fetch all terms for device (1 bulk call) → dict by filter_id
  4. Fetch all actions for device (1 bulk call) → dict by policer_id
  5. Enrich in-memory from dicts  ← O(N+M), no HTTP
```

---

## Recommended Project Structure

```
nautobot_mcp/
├── cms/
│   ├── client.py          # MODIFY: add _cms_bulk_* helpers
│   ├── interfaces.py      # MODIFY: get_interface_detail — use bulk helpers
│   ├── firewalls.py       # MODIFY: get_device_firewall_summary detail loop — use bulk helpers
│   ├── routing.py         # MODIFY: list_static_routes fallback loop — consider parallel
│   ├── arp.py             # READ-ONLY: already clean
│   └── cms_drift.py       # READ-ONLY: compare workflows
└── workflows.py          # READ-ONLY: thin dispatcher, no changes needed
```

### Structure Rationale

- **`cms/client.py` additions:** Bulk helper functions here (not in domain modules) so they're reusable from both `get_interface_detail` and standalone CLI `get-interface-unit` calls.
- **`cms/interfaces.py` changes:** Only the composite `get_interface_detail` function changes. Domain CRUD functions (`list_interface_units`, `list_interface_families`) remain unchanged — they still do single-unit operations for standalone use.
- **`cms/firewalls.py` changes:** Only the composite `get_device_firewall_summary` detail loop changes. Domain CRUD functions remain unchanged.
- **`cms/routing.py` changes:** The `list_static_routes` fallback loop (lines 96–120) is the only candidate; the primary path is already bulk.

---

## Architectural Patterns

### Pattern 1: Bulk Pre-fetch + In-Memory Distribution

**What:** Replace a sequential N×1 HTTP call pattern with a single bulk fetch, then distribute results in-memory using dict lookups.

**When to use:** When a composite function fetches a list of parent records, then loops to fetch children for each parent. The children can all be fetched in one bulk call using a common filter (e.g., `device=device_id`).

**Trade-offs:**
- ✅ Eliminates N+1 entirely — reduces HTTP calls from O(N) to O(1)
- ✅ Works for any parent-child cardinality (1:1, 1:N, N:M)
- ⚠️ Memory: bulk fetch returns all children at once; add a safety cap or warn if count > 5000
- ⚠️ Breaks if parent_id FK is absent from the child endpoint (must verify in `CMS_ENDPOINTS`)

**Example:**
```python
# BEFORE: N HTTP calls
for unit in units:
    families = list_interface_families(client, unit_id=unit.id, limit=0)

# AFTER: 1 HTTP call + O(N) dict lookup
all_families = list_interface_families(client, device=device_id, limit=0)
by_unit: dict[str, list] = {}
for fam in all_families.results:
    by_unit.setdefault(fam.unit_id, []).append(fam)
for unit in units:
    unit.families = by_unit.get(unit.id, [])
```

### Pattern 2: Parallel Bulk Fetches with `as_completed`

**What:** Fire multiple independent bulk fetches concurrently using `ThreadPoolExecutor.submit()`, then collect results as they complete using `as_completed()`.

**When to use:** When two or more bulk fetches are independent (no ordering dependency) and both are required for the final result. Already proven in `devices.py` with 3 workers.

**Trade-offs:**
- ✅ Latency = max(fetches) instead of sum(fetches)
- ✅ Each worker captures its own exceptions — failures are isolated
- ⚠️ WarningCollector is not thread-safe — collect per-worker, merge in main thread
- ⚠️ `max_workers` should match the number of independent fetches; don't oversubscribe

**Example:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_enriched_data(client, device_id):
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_families = ex.submit(list_interface_families, client, device=device_id, limit=0)
        f_vrrp     = ex.submit(list_vrrp_groups, client, device=device_id, limit=0)
        families_results = []
        vrrp_results = []
        for future in as_completed([f_families, f_vrrp]):
            if future is f_families:
                families_results = future.result().results
            else:
                vrrp_results = future.result().results
    return families_results, vrrp_results
```

### Pattern 3: Sequential Fallback for Edge-case Endpoints

**What:** When an endpoint doesn't support the required filter (e.g., no `device` filter on `juniper_bgp_neighbors`), fall back to a loop over parent records. Keep the fallback efficient with bulk-prefetch on the parent side.

**When to use:** When the primary (direct device-scoped) query fails or is unsupported in some environments. v1.9 Phase 34 used this for BGP neighbors.

**Trade-offs:**
- ✅ Works across all Nautobot/plugin versions — graceful degradation
- ⚠️ N+1 remains in the fallback path — document the assumption that primary path is always used
- ⚠️ Fallback should use bulk-prefetch on the parent (groups) to minimize calls

**Example:**
```python
# Primary: direct device filter (bulk — no N+1)
try:
    return cms_list(client, "juniper_bgp_neighbors", ..., device=device_id)
except Exception:
    pass

# Fallback: loop over groups (still bulk-prefetched)
groups = cms_list(client, "juniper_bgp_groups", ..., device=device_id)  # 1 bulk call
all_neighbors = []
for grp in groups.results:
    nbrs = cms_list(client, "juniper_bgp_neighbors", ..., group=grp.id)   # M calls, M = groups
```

### Pattern 4: Co-Primary Parallelism

**What:** Two independent data sources are fetched in parallel as co-primaries — if one fails, the other continues and its data is returned with a warning. Already used in `get_device_firewall_summary` for filters + policers.

**When to use:** When the composite response has two top-level sections that are logically independent. Works naturally with the `WarningCollector` pattern.

**Trade-offs:**
- ✅ Partial success — agent gets available data even if one source fails
- ⚠️ Increases parallel worker count — plan `max_workers` accordingly

---

## Anti-Patterns

### Anti-Pattern 1: Per-Record Sequential Fetches in a Loop

**What people do:** Call `cms_list()` inside a `for record in records:` loop to fetch child records.

**Why it's wrong:** Creates N sequential HTTP calls. With pynautobot's pagination on PAGE_SIZE=1 endpoints (the CMS plugin default), each iteration may trigger multiple HTTP calls for pagination, making it N×P calls.

**Do this instead:** Pre-fetch all children in a single bulk call with a device-level or parent-ID-level filter, then distribute in-memory with dict lookups.

### Anti-Pattern 2: Nested Sequential Loops

**What people do:** A loop inside a loop, each calling `cms_list()`. Example: units → families → VRRP (3 levels deep).

**Why it's wrong:** Total calls = O(units × families) which can be thousands on high-interface-count devices (HQV-PE1-NEW has 709 units).

**Do this instead:** Pre-fetch at each level independently before the next loop. `all_families = list_interface_families(device=device_id)` → `all_vrrp = list_vrrp_groups(device=device_id)`. Then nest in-memory.

### Anti-Pattern 3: Sharing `WarningCollector` Across Threads

**What people do:** Passing a single `WarningCollector` instance to ThreadPoolExecutor workers and calling `.add()` from multiple threads.

**Why it's wrong:** `WarningCollector` uses a plain `list.append()` internally — not thread-safe. Concurrent appends can corrupt the list or lose entries.

**Do this instead:** Each worker returns its own list of warnings. Collect from `future.result()` in the main thread and extend the shared collector after all workers complete.

---

## Build Order

```
Phase 1 — cms/client.py bulk helpers
  ├── Add _cms_bulk_families_by_unit(client, device_id) → dict
  ├── Add _cms_bulk_vrrp_by_family(client, device_id) → dict
  ├── Add _cms_bulk_terms_by_filter(client, device_id) → dict
  └── Add _cms_bulk_actions_by_policer(client, device_id) → dict
      → No caller changes yet; helpers available for Phase 2

Phase 2 — interfaces.py get_interface_detail
  ├── Replace sequential unit loop with pre-fetch + in-memory distribution
  ├── Replace _get_vrrp_for_family sequential calls with pre-fetch
  └── Add unit test: verify HTTP call count ≤ 4 for any device

Phase 3 — firewalls.py get_device_firewall_summary detail loop
  ├── Replace sequential filter loop with pre-fetch + in-memory terms
  ├── Replace sequential policer loop with pre-fetch + in-memory actions
  └── Add unit test: verify HTTP call count ≤ 6 (filters + policers + terms + actions + 2 co-primaries)

Phase 4 — routing.py list_static_routes fallback loop
  └── Evaluate: if primary path handles >99% of cases, leave as-is
      If fallback triggers often, apply bulk-prefetch pattern

Phase 5 — Smoke test regression gate
  └── Update uat_cms_smoke.py HTTP call thresholds for new call counts
```

---

## Quality Gate Checklist

- [ ] All 5 CMS composite workflows pass within SLA thresholds (target: < 5s each)
- [ ] HTTP call counts verified via `uat_cms_smoke.py` monkey-patch (Phase 33 Plan 02 pattern)
- [ ] No regression in `workflows.py` registry validation (`_validate_registry()` passes)
- [ ] Unit tests added for bulk helper functions (Phase 1)
- [ ] Unit tests added for modified composite functions verifying call count ≤ expected (Phase 2, 3)
- [ ] Thread-safety: `WarningCollector` only modified in main thread after `as_completed()`
- [ ] CLI smoke test: `nautobot-mcp --json cms interfaces detail --device HQV-PE1-NEW` runs without error
- [ ] Memory guard: bulk fetch warns if count > 5000 (prevent unbounded allocation)

---

*Architecture research for: v1.10 CMS N+1 Query Elimination*
*Researched: 2026-03-31*
