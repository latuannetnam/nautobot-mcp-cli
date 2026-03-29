# nautobot-mcp-cli

## What This Is

An MCP server, CLI tool, and agent skills library that enables AI agents to interact with Nautobot for network automation. The v1.4 API Bridge consolidates 165 individual tools into 3 universal tools (`nautobot_api_catalog`, `nautobot_call_nautobot`, `nautobot_run_workflow`) plus distributed agent skills — covering devices, interfaces, IP addresses, VLANs, circuits, and full Juniper CMS model coverage (BGP, routing, interfaces, firewalls, policies, ARP). Integrates with vendor-specific MCP servers (Juniper jmcp) to bridge live network state with Nautobot as the source of truth. Ships with partial failure resilience, import-time registry validation, actionable error diagnostics, and response ergonomics controls.

## Core Value

AI agents can discover, read, write, and orchestrate all Nautobot data through 3 tools instead of 165, eliminating context window bloat while preserving full functional coverage — including Juniper CMS model records, file-free drift comparison, and composite workflows for common network automation tasks.

## Current Milestone: Planning Next (v1.8)

**Previous milestones:** v1.0 MVP (2026-03-18) → v1.1 Agent-Native (2026-03-20) → v1.2 Juniper CMS (2026-03-21) → v1.3 API Bridge (2026-03-25) → v1.4 Operational Robustness (2026-03-26) → v1.5 Agent Performance & Quality (2026-03-28 — scope only) → v1.6 Query Performance (2026-03-28) → v1.7 URI Limit & Server Resilience (2026-03-29) → **v1.8 (planning)**

## Requirements

### Validated

- ✓ MCP server exposing 44+ core Nautobot operations — v1.0
- ✓ CLI interface for human/script access to all operations — v1.0
- ✓ Nautobot REST API client with authentication and profile support — v1.0
- ✓ Device, Interface, IPAM, Organization, Circuit management — v1.0
- ✓ Golden Config plugin integration — v1.0
- ✓ JunOS config parser with extensible vendor architecture — v1.0
- ✓ Config onboarding workflow (parse → dry-run → commit to Nautobot) — v1.0
- ✓ Config verification workflow (live vs Golden Config + data model drift) — v1.0
- ✓ Agent skills for multi-step workflows (onboard-router-config, verify-compliance) — v1.0
- ✓ Device-scoped IP query (`nautobot_get_device_ips`) — v1.1
- ✓ Device health summary (`nautobot_get_device_summary`) — v1.1
- ✓ Enriched interface list with inline IPs — v1.1
- ✓ File-free drift comparison (`nautobot_compare_device`) — v1.1
- ✓ Full CRUD for Juniper routing models (BGP groups, neighbors, static routes) — v1.2
- ✓ Full CRUD for Juniper interface models (units, families, VRRP, ARP) — v1.2
- ✓ Full CRUD for Juniper firewall and policy models — v1.2
- ✓ Composite summary tools (BGP summary, routing table, interface detail, firewall summary) — v1.2
- ✓ CMS drift verification (compare live jmcp data vs Nautobot CMS records) — v1.2
- ✓ `nautobot-mcp cms` CLI for all CMS model operations — v1.2
- ✓ `cms-device-audit` agent skill for CMS-aware device audit workflows — v1.2
- ✓ API Catalog engine — static core + dynamic CMS plugin discovery — v1.3
- ✓ Universal REST bridge (`nautobot_call_nautobot`) — endpoint routing, validation, auto-pagination, fuzzy suggestions — v1.3
- ✓ Workflow registry (`nautobot_run_workflow`) — 10 composite workflows, parameter normalization, response envelopes — v1.3
- ✓ Consolidated server.py — 3 tools replacing 165 individual tool wrappers — v1.3
- ✓ Agent skills rewritten for 3-tool API (`cms-device-audit`, `onboard-router-config`, `verify-compliance`) — v1.3
- ✓ UAT pytest suite (11 live tests) + standalone smoke script (9 checks) against dev server — v1.3
- ✓ Partial failure resilience — `WarningCollector`, 3-tier status, co-primaries pattern — v1.4
- ✓ Import-time registry validation (`_validate_registry()`) — catches param/signature drift at load — v1.4
- ✓ Error diagnostics — DRF 400 parsing, `ERROR_HINTS`, `STATUS_CODE_HINTS`, status-code-derived `NautobotAPIError` defaults — v1.4
- ✓ Per-endpoint CMS filter registry (`CMS_ENDPOINT_FILTERS`, 43 entries) — v1.4
- ✓ UUID path normalization in REST bridge — agents pass linked object URLs directly — v1.4
- ✓ Response ergonomics — `response_size_bytes`, `detail=False` summary mode, `limit=N` capping — v1.4

### Active

- [ ] v1.5 requirements: ENV-01..ENV-05 (Contract & Envelope), BAT-01..BAT-05 (Batch), PRT-01..PRT-06 (Projection), SEC-01..SEC-06 (Security), KPI-01..KPI-04 (KPI Benchmarks) — all planned for v1.5 but not built; deferred to future milestone
- [ ] v1.8 requirements: TBD

### Validated (v1.6 — Query Performance)

- ✓ Eliminate wasteful `count()` auto-pagination — `skip_count` plumbed through CLI, MCP tool, bridge, `get_device_inventory()` — v1.6
- ✓ `has_more` inference from `len(results) == limit` when count skipped — v1.6
- ✓ Direct `/count/` endpoint for O(1) count — `NautobotClient.count()` via `http_session.get`, 404 fallback to pynautobot — v1.6
- ✓ All `count()` call sites replaced throughout codebase — `devices.py` fully migrated — v1.6
- ✓ Per-section timing instrumentation — `interfaces_latency_ms`, `ips_latency_ms`, `vlans_latency_ms` in `DeviceInventoryResponse` — v1.6
- ✓ Parallel counts via `ThreadPoolExecutor` for `detail=all` — v1.6
- ✓ `latency_ms` in `call_nautobot` response envelope — wall-clock timing for all operations — v1.6
- ✓ `--no-count` CLI flag — skips all count operations regardless of detail — v1.6
- ✓ `--limit 0` auto-enables `skip_count` — unlimited mode with zero count overhead — v1.6

### Validated (v1.7 — Phase 32: VLANs 500 Fix)

- ✓ VLAN count graceful degradation: `vlan_count` → `Optional[int]`, `warnings: Optional[list[dict]]` in `DeviceStatsResponse` and `DeviceInventoryResponse` — v1.7 Phase 32
- ✓ `device.location.id` (UUID) used at all VLAN count call sites instead of `location.name` — v1.7 Phase 32
- ✓ `NautobotAPIError` caught in all 4 VLAN count paths: summary, inventory sequential, inventory parallel, inventory fallback — v1.7 Phase 32
- ✓ `RetryError` catch in `client.count()` — HTTP retries exhaust on 500 → pynautobot fallback works cleanly — v1.7 Phase 32
- ✓ `N/A` display in CLI when `vlan_count` is null — v1.7 Phase 32
- ✓ Live verified: `devices summary HQV-PE1-NEW` → `"vlan_count": 2381` (was 500) — v1.7 Phase 32
- ✓ 11 new unit tests: `TestVLANCount500` (3) + `TestDeviceVLANCountErrorHandling` (8) — v1.7 Phase 32
- ✓ 443 total unit tests pass — no regression — v1.7 Phase 32

### Validated (v1.7 — Phase 31: Bridge Param Guard)

- ✓ `_guard_filter_params()` guard function in bridge.py — intercepts `__in`-suffixed filter params before `.filter()` calls — v1.7 Phase 31
- ✓ Raises `NautobotValidationError` for `__in` lists > 500 items — prevents 414 Request-URI Too Large from external callers — v1.7 Phase 31
- ✓ Converts `__in` lists ≤ 500 to DRF-native comma-separated strings — reduces query string size for large-but-valid lists — v1.7 Phase 31
- ✓ Non-`__in` list params (tag, status, location) pass through unchanged — no regression on existing callers — v1.7 Phase 31
- ✓ Guard wired into `_execute_core()` and `_execute_cms()` — covers both Nautobot core and CMS plugin endpoints — v1.7 Phase 31
- ✓ 18 unit tests: `TestParamGuard` (13) + `TestParamGuardIntegration` (5) — full coverage of guard logic and integration — v1.7 Phase 31

### Validated (v1.7 — Phase 30: Direct HTTP Bulk Fetch)

- ✓ `_bulk_get_by_ids()` helper — single direct HTTP call with DRF comma-separated UUIDs, auto-follows `next` links, wraps via `endpoint.return_obj()` — v1.7 Phase 30
- ✓ `get_device_ips()` Pass 2 & 3 refactored: chunked `.filter()` loops → `_bulk_get_by_ids()` — no 414 for large devices — v1.7 Phase 30
- ✓ Stale IP detection: `fetched_ids - requested_ids` surfaces deleted IPs as `unlinked_ips` stubs — v1.7 Phase 30
- ✓ 11 new unit tests in `tests/test_ipam.py` — 29 total tests pass — v1.7 Phase 30

### Rejected

- ~~Generic Resource Engine (unified resource registry + dispatcher)~~ — Rejected 2026-03-24; superseded by API Bridge architecture

### Future

- [ ] Multi-vendor config parsers (Cisco IOS/IOS-XE, Arista EOS)
- [ ] Bulk device onboarding (batch config files)
- [ ] Config remediation suggestions based on drift reports
- [ ] Extended drift coverage (interfaces, firewalls via CMS drift engine)

### Out of Scope

- Direct device communication — handled by vendor MCP servers (jmcp for Juniper)
- Nautobot server deployment/management — server already running at nautobot.netnam.vn
- Nautobot plugin development — this tool consumes existing Nautobot APIs
- Automated remediation without confirmation — reports drift only, requires human approval
- Modifying netnam-cms-core plugin code — we only consume its REST API

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Shared core library with thin MCP/CLI layers | Single source of truth | ✓ Clean separation, easy to add tools |
| MCP + CLI + Skills as three interfaces | MCP for agents, CLI for humans, Skills for workflows | ✓ All three patterns work |
| Juniper-first, extensible vendor architecture | jmcp exists; VendorParser ABC for future | ✓ ParserRegistry ready for Cisco/Arista |
| Nautobot REST API (not GraphQL) | Standard, well-documented, broad coverage | ✓ pynautobot handles all operations |
| DiffSync for data model verification | Semantic diff vs string diff | ✓ Clean drift reports |
| dry_run=True default for onboarding | Safety first — preview before committing | ✓ Avoids accidental bulk writes |
| M2M traversal for device-IP queries | `ip_addresses.filter(device=...)` unreliable in Nautobot | ✓ Reliable via `ip_address_to_interface` |
| Auto-detecting drift input shape | Allows chaining `get_device_ips` output directly | ✓ Zero transformation needed |
| netnam-cms-core via plugin REST API | Plugin exposes 49 DRF endpoints under /api/plugins/netnam-cms-core/ | ✓ Full CRUD on all 5 domains |
| 1:1 Pydantic model per CMS endpoint | Mirrors API shape exactly; avoids impedance mismatch | ✓ 40+ CMS Pydantic models, clean validation |
| Composite tools as thin aggregators | Single-call UX for common agent workflows | ✓ Reduces agent round-trips from N to 1 |
| DiffSync for CMS drift (not set comparison) | Field-level change detection vs presence-only | ✓ Reports changed fields, not just missing/extra |
| ~~Generic Resource Engine (v1.3)~~ | ~~165 tools → ~18 via unified dispatcher~~ | ❌ Rejected — superseded by API Bridge |
| API Bridge MCP Server (v1.3) | 165 tools → 3 via catalog + REST bridge + workflows; ~96% token reduction | ✓ Shipped v1.3 |
| `live` pytest marker for UAT | UAT tests hit real server; excluded from CI by `addopts = "-m 'not live'"` | ✓ Clean CI/CD isolation |
| Smoke script as Windows-safe ASCII output | Replaced ✓/✗ Unicode with [PASS]/[FAIL] for CP1252 compatibility | ✓ Portable on Windows terminals |
| Three-tier workflow status (`ok`/`partial`/`error`) | Agents see partial data immediately instead of all-or-nothing failure | ✓ Shipped v1.4; proven in practice |
| `WarningCollector` dataclass | Shared warning accumulation pattern across all composites | ✓ Consistent envelope shape |
| Independent co-primaries in composites | Fetch filters + policers in parallel, one failure doesn't block the other | ✓ `firewall_summary` uses it |
| Import-time registry self-validation | `_validate_registry()` catches param/signature drift before runtime | ✓ Caught 3 pre-existing bugs |
| DRF 400 body parsing | Field-level validation errors surfaced in `NautobotValidationError.errors` | ✓ Ships in v1.4 |
| Status-code-derived error defaults | `NautobotAPIError` derives hint from HTTP status when no explicit hint | ✓ No more generic placeholders |
| Per-endpoint filter registry | Each CMS endpoint advertises correct FK filter(s); not domain-level | ✓ 43 entries; replaced 1-size-fits-all |
| UUID path normalization | REST bridge strips UUID segments; linked object URLs work directly | ✓ Agents can pass full URLs |
| Summary mode + limit ergonomics | `detail=False` strips nested arrays; `limit=N` caps all arrays independently | ✓ Ships in v1.4 |
| Skip count for paginated results | `count()` wastes O(n) fetches when users only want a page | ✓ Shipped v1.6 |
| Direct `/count/` endpoint for O(1) counts | pynautobot's `.count()` uses auto-pagination; Nautobot has fast `/count/` endpoint | ✓ Shipped v1.6 |
| Infer `has_more` from result count | When limit is respected, `returned_count == limit` → more available | ✓ Shipped v1.6 |
| 404 fallback to pynautobot | Some plugin endpoints don't expose `/count/`; 404 is not an error, it's a signal to use O(n) fallback | ✓ Shipped v1.6 |
| Wall-clock `latency_ms` in bridge | `_execute_core`/`_execute_cms` time, not ORM-to-dict time; covers full call path including `resolve_device_id` | ✓ Shipped v1.6 |
| Parallel counts via `ThreadPoolExecutor(max_workers=3)` | Max of 3 latencies instead of sum when `detail=all`; sequential fallback on any failure | ✓ Shipped v1.6 |
| DRF comma-separated for bulk fetch | `?interface=uuid1,uuid2,uuid3` ~3x shorter than repeated `?interface=uuid1&interface=uuid2` — eliminates 414 | ✓ Shipped v1.7 Phase 30 |
| Raise for oversized `__in` lists | 414 from external callers is prevented by raising `NautobotValidationError` before `.filter()` — guides callers to chunk | ✓ Shipped v1.7 Phase 31 |
| 500-item threshold on `__in` lists | Matches pynautobot's natural limit; raises before pynautobot crashes | ✓ Shipped v1.7 Phase 31 |
| Location UUID instead of name for VLANs count | UUID bypasses Nautobot's `TreeNodeMultipleChoiceFilter` name→object resolution ORM crash | ✓ Shipped v1.7 Phase 32 |
| Graceful VLAN count degradation | 500 → `vlan_count=None` + `warnings` field; operation continues, count shows `null`/`N/A` | ✓ Shipped v1.7 Phase 32 |
| RetryError → pynautobot fallback | HTTP `/count/` retries 3x on 500 → raises `RetryError` before `HTTPError` catch; adding `RetryError` catch routes to working pynautobot fallback | ✓ Shipped v1.7 Phase 32 |
| `dict[str, Any]` for warnings field | Pydantic 2.12 rejects `bool` coercion in `dict[str, str]`; `dict[str, Any]` allows `recoverable: bool` | ✓ Shipped v1.7 Phase 32 |
| `e.message` attribute for error strings | `NautobotAPIError.__str__` includes hint text; use `e.message` attribute directly to avoid Pydantic repr artifacts | ✓ Shipped v1.7 Phase 32 |

## Constraints

- **Protocol**: MCP (Model Context Protocol) for AI agent interaction
- **Language**: Python (pyproject.toml with uv)
- **Nautobot API**: REST API v2 at https://nautobot.netnam.vn/
- **CMS Plugin API**: netnam-cms-core plugin REST API at /api/plugins/netnam-cms-core/
- **Vendor scope**: Juniper first, extensible VendorParser ABC for others
- **Dependencies**: Works alongside existing jmcp — complementary, not replacing

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-29 after v1.7 milestone shipped*
