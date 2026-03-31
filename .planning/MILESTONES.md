# Milestones

## v1.10 CMS N+1 Query Elimination (PLANNING)

**Goal:** Eliminate N+1 HTTP call patterns in CMS composite workflows so all 5 smoke test workflows complete within 60s on HQV-PE1.

**Root causes:**
1. `interface_detail`: Bulk-fetches families once, discards result, refetches one-by-one per unit (~2,000 units → ~2,000 extra requests)
2. `firewall_summary` detail: Per-filter term refetch + per-term action refetch → N×M sequential requests
3. `routing_table`: Per-route nexthop fallback loop after bulk nexthop fetch
4. `bgp_summary`: Per-neighbor AF/policy fallback loops without `len(...) > 0` guards

**Requirements:** CQP-01..CQP-05, RGP-01..RGP-02 (see `.planning/REQUIREMENTS.md`)

**Phase 35:** `interface_detail` N+1 Fix — CQP-01, CQP-05
**Phase 36:** `firewall_summary` Detail N+1 Fix — CQP-02, CQP-05
**Phase 37:** `routing_table` + `bgp_summary` N+1 Fixes — CQP-03, CQP-04
**Phase 38:** Regression Gate — RGP-01, RGP-02

**Started:** 2026-03-31

---

## v1.9 CMS Performance Fix (Shipped: 2026-03-30)

**Phases completed:** 1 phase (Phase 34), 2 plans

**Key accomplishments:**

- AF/policy fetches gated behind `if detail and all_neighbors:` — eliminates unconditional 60s+ timeout calls; `bgp_summary` default path: 85s → 2.2s
- `devices_inventory` CLI default `--limit` lowered 50 → 10 — 709-interface fetch now returns fast paginated results
- Live UAT: 5/5 PASS — bgp_summary 2251ms, routing_table 1554ms, firewall_summary 2070ms, interface_detail 2002ms, devices_inventory 10776ms

---

## v1.8 CMS Pagination Fix (Shipped: 2026-03-30)

**Phases completed:** 1 phase (Phase 33), 2 plans

**Key accomplishments:**

- `_CMS_BULK_LIMIT = 200` constant in `cms/client.py` — collapses 151 sequential HTTP calls into 1 for CMS endpoints with PAGE_SIZE=1
- `cms_list()` updated: `limit=0 → limit=200` via kwarg; explicit `limit > 0` preserved via `elif` branch
- `uat_cms_smoke.py` regression gate with per-workflow HTTP call counting via pynautobot monkey-patch
- 57 new/modified unit tests pass — no regression

---

## v1.7 URI Limit & Server Resilience (Shipped: 2026-03-29)

**Phases completed:** 3 phases (30-32), 3 plans

**Key accomplishments:**

- Direct HTTP bulk fetch for `get_device_ips()` — replaces O(3N/chunk_size) chunked `.filter()` loops with O(3) comma-separated UUID calls
- `_guard_filter_params()` for `__in` lists > 500 — prevents 414 Request-URI Too Large
- VLAN count graceful degradation — `vlan_count=None` + `warnings` on 500; live verified on HQV-PE1-NEW (2381 VLANs, was 500)

---

## v1.6 Query Performance Optimization (Shipped: 2026-03-28)

**Phases completed:** 2 phases (28-29), 2 plans

**Key accomplishments:**

- `skip_count` with `has_more` inference from `len(results) == limit` — eliminates wasteful O(n) count pagination
- Direct `/count/` endpoint via HTTP — O(1) count instead of O(n) pynautobot auto-pagination
- Per-section timing instrumentation — `interfaces_latency_ms`, `ips_latency_ms`, `vlans_latency_ms`
- Parallel counts via `ThreadPoolExecutor(max_workers=3)` for `detail=all`

---

## v1.4 Operational Robustness (Shipped: 2026-03-26)

**Phases completed:** 4 phases, 7 plans, 18 tasks | 55 commits | 371 files changed | +60,732 / -959 lines

**Key accomplishments:**

- **Partial failure resilience** — `WarningCollector`, 3-tier status (`ok`/`partial`/`error`), all 4 composites return `(result, warnings)` tuples; co-primaries pattern in `firewall_summary` (filters + policers fetched independently)
- **Import-time registry validation** — `_validate_registry()` catches param/signature drift at module load; caught and fixed 3 pre-existing bugs in the workflow registry
- **Error diagnostics** — DRF 400 body parsing (field-level errors), `ERROR_HINTS` (10 endpoint-specific hints), `STATUS_CODE_HINTS` (429/500/502/503/504), `NautobotAPIError` status-code-derived defaults
- **Catalog accuracy** — Per-endpoint `CMS_ENDPOINT_FILTERS` (43 entries) replaces domain-level `CMS_DOMAIN_FILTERS`; correct FK filters for all CMS endpoints
- **UUID path normalization** — REST bridge strips UUID from `/api/.../<uuid>/` paths; agents can pass linked object URLs directly
- **Response ergonomics** — `response_size_bytes` in all envelopes; `detail=False` summary mode (strips `families[]`/`vrrp_groups[]`); `limit=N` independently caps all nested arrays
- **476 unit tests** — up from 397 at v1.3; zero regressions across all phases

---

## v1.3 API Bridge MCP Server (Shipped: 2026-03-25)

**Phases completed:** 4 phases, 8 plans, 0 tasks

**Key accomplishments:**

- 3-tool API Bridge consolidates 165 MCP tools into `nautobot_api_catalog`, `nautobot_call_nautobot`, `nautobot_run_workflow`
- Static core + dynamic CMS plugin endpoint discovery
- Universal REST bridge with auto-pagination, fuzzy suggestions, UUID normalization
- Workflow registry with 10 composite workflows and parameter normalization
- Agent skills rewritten for 3-tool API (`cms-device-audit`, `onboard-router-config`, `verify-compliance`)

---

## v1.2 Juniper CMS Model MCP Tools (Shipped: 2026-03-21)

**Phases completed:** 6 phases, 18 plans | 62 commits | 98 files changed | +21,735 lines

**Key accomplishments:**

- **164 MCP tools** — full CRUD for 5 Juniper CMS model domains: routing (BGP + static routes), interfaces (units, families, VRRP), firewalls, policies, ARP
- **4 composite summary tools** — `get_device_bgp_summary`, `get_device_routing_table`, `get_interface_detail`, `get_device_firewall_summary` (single-call aggregations)
- **DiffSync drift engine** — `compare_bgp_neighbors` + `compare_static_routes`; live jmcp data vs Nautobot CMS records; no config files required
- **`nautobot-mcp cms` CLI** — routing, interfaces, firewalls, policies, drift subcommands
- **`cms-device-audit` agent skill** — 8-step jmcp → CMS comparison audit workflow
- **293 unit tests** — up from 105 at v1.1; full coverage across all 6 phases

---

## v1.1 Agent-Native MCP Tools (Shipped: 2026-03-20)

**Phases completed:** 7 phases, 19 plans

**Key accomplishments:**

- `nautobot_get_device_ips` — all IPs for a device in one call (M2M traversal)
- `nautobot_get_device_summary` — device health at a glance
- `nautobot_list_interfaces(include_ips=True)` — inline IP enrichment
- `nautobot_compare_device` — file-free drift detection
- `verify quick-drift` CLI command
- 46 MCP tools | 105 unit tests | ~11k LOC

---

## v1.0 MVP (Shipped: 2026-03-18)

**Phases completed:** 4 phases, 13 plans, 0 tasks

**Key accomplishments:**

- 44+ MCP tools for Device, Interface, IPAM, Organization, Circuit, Golden Config
- CLI interface with Typer
- JunOS config parser with VendorParser ABC
- Config onboarding and verification workflows
- Agent skills (onboard-router-config, verify-compliance)

---
*Last updated: 2026-03-31 — v1.10 milestone started*
