# Milestones

## v1.7 URI Limit & Server Resilience (Shipped: 2026-03-29)

**Phases completed:** 27 phases, 57 plans, 47 tasks

**Key accomplishments:**

- [Rule 3 - Blocking] Hatchling build backend
- `tests/test_cms_arp.py`
- Adaptive count skipping with has_more inference, per-section timing, and parallel counts for detail=all
- O(1) /count/ via direct HTTP, latency instrumentation in bridge, all 8 call sites migrated
- Direct HTTP bulk fetch replaces O(3N/chunk_size) chunked .filter() loops in get_device_ips() with O(3) comma-separated UUID calls, plus partial failure detection for stale IPs
- Phase:
- Phase:
- Phase:

---

## v1.6 Query Performance Optimization (Shipped: 2026-03-28)

**Phases completed:** 24 phases, 56 plans, 44 tasks

**Key accomplishments:**

- [Rule 3 - Blocking] Hatchling build backend
- `tests/test_cms_arp.py`
- Adaptive count skipping with has_more inference, per-section timing, and parallel counts for detail=all
- O(1) /count/ via direct HTTP, latency instrumentation in bridge, all 8 call sites migrated

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

- (none recorded)

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

**Last phase number:** 7

---

## v1.0 MVP (Shipped: 2026-03-18)

**Phases completed:** 4 phases, 13 plans, 0 tasks

**Key accomplishments:**

- 44+ MCP tools for Device, Interface, IPAM, Organization, Circuit, Golden Config
- CLI interface with Typer
- JunOS config parser with VendorParser ABC
- Config onboarding and verification workflows
- Agent skills (onboard-router-config, verify-compliance)

**Last phase number:** 4

---
