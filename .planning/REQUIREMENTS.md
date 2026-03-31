# Requirements: nautobot-mcp-cli

**Defined:** 2026-03-26
**Updated for v1.7:** 2026-03-29
**Updated for v1.8:** 2026-03-30
**Core Value:** AI agents can discover, read, write, and orchestrate Nautobot data through 3 tools — with predictable contracts, minimal round-trips, compact responses, and production-grade reliability.

## v1.8 Requirements

Fix N+1 pynautobot pagination in CMS composite functions. Root cause: `limit=0` (falsy) not sent as HTTP param → Nautobot CMS plugin uses PAGE_SIZE=1 → 151 sequential HTTP calls (~80s). Fix: pass `_CMS_BULK_LIMIT = 200` when `limit == 0` in `cms_list()`.

### CMS Pagination Fix (PAG)

- [ ] **PAG-01**: `cms_list()` passes `_CMS_BULK_LIMIT = 200` to `endpoint.all()` / `endpoint.filter()` when `limit == 0` — collapses N sequential calls to ceil(N/200) calls
- [ ] **PAG-02**: `limit > 0` values pass through unchanged — caller intent is preserved
- [ ] **PAG-03**: `_CMS_BULK_LIMIT` constant documented with rationale (Nautobot cap, CMS plugin compatibility, safety margin)
- [ ] **PAG-04**: Unit tests verify `cms_list(limit=0)` calls `endpoint.all(limit=200)` — not `limit=0`
- [ ] **PAG-05**: Unit tests verify `cms_list(limit=50)` calls `endpoint.all(limit=50)` — explicit limit preserved
- [ ] **PAG-06**: Unit tests verify `cms_list(limit=0, filters)` calls `endpoint.filter(..., limit=200)` — bulk limit with filters

### Endpoint Discovery (DISC)

- [x] **DISC-01**: Instrument all CMS list functions with HTTP call counting to discover which endpoints have PAGE_SIZE=1 (empirical test against prod server)
- [x] **DISC-02**: Document slow endpoints found and add them to a registry in `cms/client.py` for future reference

### Regression Prevention (REG)

- [ ] **REG-01**: `scripts/uat_cms_smoke.py` — bgp_summary completes in < 5s (was 80s before fix)
- [ ] **REG-02**: All existing unit tests pass after changes — no behavioral regression
- [ ] **REG-03**: `scripts/uat_cms_smoke.py` committed and pushed to repository

## v1.7 Requirements

Requirements to eliminate 414 Request-URI Too Large errors and address VLANs 500 errors. All fixes use existing codebase patterns (direct HTTP, comma-separated DRF format, pynautobot Record wrapping).

### Direct HTTP Bulk Fetch (URI)

- [ ] **URI-01**: `get_device_ips()` replaces `.filter(interface=chunk)` M2M loop with a single direct HTTP call using comma-separated interface UUIDs (`?interface=uuid1,uuid2,uuid3`)
- [ ] **URI-02**: `get_device_ips()` replaces `.filter(id__in=chunk)` IP detail loop with a single direct HTTP call using comma-separated IP UUIDs (`?id__in=uuid1,uuid2,uuid3`)
- [ ] **URI-03**: Direct HTTP bulk fetch follows pagination `next` links to collect all results when response exceeds page size
- [ ] **URI-04**: Direct HTTP responses are wrapped back into pynautobot `Record` objects via `return_obj()` so existing attribute access (`ip.id`, `ip.address`, `ip.status.display`) continues to work
- [ ] **URI-05**: Empty IP/M2M result sets are handled gracefully — early return before HTTP call when no IDs to fetch
- [ ] **URI-06**: M2M bulk fetch uses a fallback chunking strategy (chunk size 100) if comma-separated format is not supported by the `ip_address_to_interface` endpoint

### Bridge Param Guard (BRIDGE)

- [ ] **BRIDGE-01**: `_execute_core()` intercepts `__in` list values in `params` before passing to `.filter()`; lists > 500 items raise `NautobotValidationError` with descriptive message
- [ ] **BRIDGE-02**: `_execute_cms()` implements the same `__in` list guard for CMS endpoint params
- [ ] **BRIDGE-03**: Lists ≤ 500 items in `__in` params are converted to comma-separated strings before passing to `.filter()` (DRF-native format)
- [ ] **BRIDGE-04**: Non-`__in` list params (e.g., `tag=[foo, bar]`) are passed through unchanged — only `__in` list sizes are restricted
- [ ] **BRIDGE-05**: Bridge param guard is covered by unit tests: small list (≤ 500) works, large list (> 500) raises validation error, non-`__in` lists pass through

### VLANs 500 Mitigation (VLAN)

**Root cause found:** CLI passes `location=HQV` (name) to `/api/ipam/vlans/count/`. Nautobot's `VLANViewSet` uses an annotated queryset (`annotate(prefix_count=count_related(...))`) shared between list and count. The ManyToMany `locations` JOIN combined with name-based filtering triggers an ORM crash → 500. Passing `location=<uuid>` (resolved first) avoids the name→object resolution fallback path.

- [ ] **VLAN-01**: All `client.count("ipam", "vlans", location=...)` call sites resolve the location name to a UUID before calling count — `location=<uuid>` instead of `location=HQV`
- [ ] **VLAN-02**: `client.count()` catches HTTP 500 as a safety fallback — returns `None` when all retry attempts are exhausted; operation continues without the count
- [ ] **VLAN-03**: Count values of `None` are handled gracefully in `devices summary` and `devices inventory` output — count fields show `null` rather than crashing
- [ ] **VLAN-04**: A warning is added to the output when any VLAN count fails, indicating it was unavailable

### Regression (TEST)

- [ ] **TEST-01**: All existing unit tests pass after changes — no behavioral regression in working paths
- [ ] **TEST-02**: `device-ips DEVICE` command works correctly on a device with known many IPs (verified against prod with HQV-PE1-NEW or similar)
- [ ] **TEST-03**: `devices inventory DEVICE --detail ips` completes successfully for large-IP-count devices without 414

## v1.6 Requirements

Requirements for query performance optimization. All rooted in root-cause analysis of the `--limit 5` slow response for large devices.

### Count Optimization (PERF)

- [ ] **PERF-01**: `devices inventory` skips `count()` call when `detail=interfaces|ips|vlans` AND `limit > 0`; `has_more` inferred from `returned_count == limit`
- [ ] **PERF-02**: `devices inventory --detail all` fetches all three counts concurrently via parallel API calls
- [ ] **PERF-03**: Direct Nautobot `/count/` endpoint as fallback when count IS needed — bypasses pynautobot's auto-pagination; returns O(1) result
- [ ] **PERF-04**: All `count()` calls replaced with direct `/count/` endpoint usage throughout codebase (devices.py, ipam.py, cms/client.py)

### Observability (OBS)

- [ ] **OBS-01**: `devices inventory` output includes per-section `api_calls` count and total `latency_ms` when `--json` is used
- [ ] **OBS-02**: `nautobot_call_nautobot` response envelope includes `latency_ms` per operation

### CLI UX (UX)

- [ ] **UX-01**: `--no-count` flag on `devices inventory` skips all count operations regardless of `detail` value
- [ ] **UX-02**: `devices inventory --limit 0` (unlimited) fetches all records with zero count overhead

## v1.5 Requirements

Requirements for MCP server quality and AI-agent performance optimization. All built on existing 3-tool API Bridge architecture.

### Contract & Envelope Stability (ENV)

- [ ] **ENV-01**: Every tool response (all 3 MCP tools) includes standardized metadata: `request_id`, `timestamp`, `status` (`ok`/`partial`/`error`), `warnings`, `latency_ms`, `response_size_bytes`
- [ ] **ENV-02**: Error responses include `error`, `hint`, and `retryable` fields; HTTP 429/502/503/504 errors include `retry_after` hint
- [ ] **ENV-03**: `nautobot_api_catalog` response includes `capabilities` block: supported `response_modes`, `max_batch_items`, `projection_depth`, `observability_fields`, and `security_policies`
- [ ] **ENV-04**: All tool responses maintain immutable minimum key contract — existing agents and skills continue working without changes in default mode
- [ ] **ENV-05**: Contract snapshot tests validate envelope schema stability across all 3 tools

### Batch Execution & Round-trip Reduction (BAT)

- [ ] **BAT-01**: `nautobot_run_workflow` accepts `batch` execution mode that fans out the same workflow to multiple targets with independent per-item result envelopes
- [ ] **BAT-02**: Batch items preserve successful results when other items fail (no all-or-nothing abort)
- [ ] **BAT-03**: Batch returns aggregate `status` (`ok`/`partial`/`error`) with per-item `status`, `data`, `error`, `latency_ms`
- [ ] **BAT-04**: Batch validates each item through the same execution path as single calls (validation bypass prevention)
- [ ] **BAT-05**: Resource guardrails: `max_batch_items` limit, per-item `limit` clamped by `MAX_LIMIT`

### Projection & Token Efficiency (PRT)

- [ ] **PRT-01**: `nautobot_call_nautobot` and `nautobot_run_workflow` accept optional `options.response_mode` (`full`/`standard`/`minimal`)
- [ ] **PRT-02**: Field projection via `options.fields` (include list) using jmespath on result objects
- [ ] **PRT-03**: Projection safelist rejects unknown field names with validation error + hint
- [ ] **PRT-04**: Projection always includes required identity fields (`id`, `url`) — enforcing a minimum-field floor
- [ ] **PRT-05**: Projection applied consistently across both core (`/api/*`) and CMS (`cms:*`) execution paths
- [ ] **PRT-06**: `minimal` mode strips nested arrays, keeps counts and top-level identity fields

### Security & Observability (SEC)

- [ ] **SEC-01**: Configurable endpoint allowlist — starts with `/api/` and `cms:` prefixes; additional plugin path patterns (e.g., `/api/plugins/<name>/`) can be registered; rejects arbitrary external URLs and unlisted paths
- [ ] **SEC-02**: UUID-path normalization preserved through all new execution paths
- [ ] **SEC-03**: Request-size guardrails: `max_projection_fields`, `max_batch_items`, payload size limits; oversized requests return deterministic validation error
- [ ] **SEC-04**: Optional bearer-token authentication for non-stdio transports (audit-only mode first)
- [ ] **SEC-05**: All tool calls emit structured events: `request_id`, tool name, endpoint/workflow, method, status, latency, truncation flag
- [ ] **SEC-06**: `/health` readiness endpoint for HTTP transport (returns version, status, uptime)

### KPI Benchmarking & Verification (KPI)

- [ ] **KPI-01**: Benchmark harness measuring: round-trips/task, response size (bytes), p50/p95/p99 latency, error rate, partial-success rate
- [ ] **KPI-02**: 4 benchmark scenarios: catalog discovery, projected list GET, mixed batch workflow, CMS composite
- [ ] **KPI-03**: Live/UAT test validating KPI targets: round-trips reduced 40–60%, token footprint reduced 35–55%, p95 < 3s
- [ ] **KPI-04**: Prometheus-compatible `/metrics` endpoint exposing: `mcp_requests_total`, `mcp_request_duration_seconds`, `mcp_response_size_bytes`

## v1.4 Requirements (completed)

Requirements derived from verified user-reported pain points (see analysis report). Each maps to roadmap phases.

### Partial Failure Resilience (PFR)

- [x] **PFR-01**: Composite workflows return partial data with `status: "partial"` when child queries fail, instead of all-or-nothing `status: "error"`
- [x] **PFR-02**: `bgp_summary` workflow returns groups and neighbors even if policy association or address family queries fail
- [x] **PFR-03**: Response envelope includes `warnings` list with per-child-call failure details when partial
- [x] **PFR-04**: `routing_table`, `firewall_summary`, and `interface_detail` composite functions implement same graceful degradation pattern

### Catalog Accuracy (CAT)

- [x] **CAT-07**: Per-endpoint filter registry in `cms_discovery.py` replaces domain-level `CMS_DOMAIN_FILTERS`
- [x] **CAT-08**: Catalog advertises only filters actually supported at runtime for each CMS endpoint (e.g., `group` for `juniper_bgp_neighbors`, not `device`)
- [x] **CAT-09**: Existing unit tests updated to validate per-endpoint filter accuracy

### Endpoint Dereference (DRF)

- [x] **DRF-01**: REST bridge strips UUID path segments from endpoints before validation (e.g., `/api/dcim/device-types/<uuid>/` → `/api/dcim/device-types/` + `id=<uuid>`)
- [x] **DRF-02**: Agent can follow linked object URLs from response payloads directly through `call_nautobot`
- [x] **DRF-03**: Existing bridge unit tests extended with dereference scenarios

### Workflow Contracts (WFC)

- [x] **WFC-01**: `verify_data_model` workflow entry lists `parsed_config` as required parameter
- [x] **WFC-02**: `verify_data_model` workflow entry includes `ParsedConfig.model_validate` transform for `parsed_config`
- [x] **WFC-03**: Workflow registry validation catches required-param mismatches at import time (startup self-check)

### Error Diagnostics (ERR)

- [x] **ERR-01**: 400 (validation) errors parse response body and include field-level error details in `NautobotValidationError.errors`
- [x] **ERR-02**: Error hints are contextual to the specific endpoint and filter being used (not generic "check server logs")
- [x] **ERR-03**: Composite workflow errors include `origin` field showing which child operation failed
- [x] **ERR-04**: `NautobotAPIError` default hint replaced with operation-specific guidance

### Response Ergonomics (RSP)

- [x] **RSP-01**: `interface_detail` workflow supports `detail` toggle (summary mode strips unit/family/filter details, keeps counts)
- [x] **RSP-02**: Composite workflow envelopes include `response_size_bytes` metadata
- [x] **RSP-03**: Composite workflows support optional `limit` parameter to cap items in response

## v2 Requirements

Deferred to future release.

### Performance at Scale

- **PERF-09**: Streaming response support for `--limit 0` (yields results page-by-page without buffering all in memory)
- **PERF-10**: Bulk IP enrichment via batch M2M query (currently N+1 for `include_ips=True`)

## Future Requirements

### Multi-Domain Scaling

- **SCALE-01**: When adding a new domain, only catalog entries needed (zero new `@mcp.tool` definitions)
- **SCALE-02**: Split into multiple MCP sub-servers when tool count exceeds 40

### Extended Tooling

- **EXT-01**: Multi-vendor config parsers (Cisco IOS/IOS-XE, Arista EOS)
- **EXT-02**: Bulk device onboarding (batch config files)
- **EXT-03**: Config remediation suggestions based on drift reports

## Out of Scope

| Feature | Reason |
|---------|--------|
| pynautobot upstream fix | We work around pynautobot's behavior; fixing upstream is out-of-scope |
| Nautobot server changes | This tool consumes the existing Nautobot API; server-side changes not applicable |
| Real-time streaming/WebSocket | Adds complexity; HTTP pagination is sufficient for current needs |
| CMS plugin server-side filter changes | We consume REST API as-is; fix is on our catalog metadata |
| Response streaming / chunked transfer | MCP protocol limitation; use summary mode + limit instead |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PERF-01 | Phase 28 | Pending |
| PERF-02 | Phase 28 | Pending |
| PERF-03 | Phase 29 | Pending |
| PERF-04 | Phase 29 | Pending |
| OBS-01 | Phase 28 | Pending |
| OBS-02 | Phase 29 | Pending |
| UX-01 | Phase 28 | Pending |
| UX-02 | Phase 28 | Pending |
| PFR-01 | Phase 19 | Complete |
| PFR-02 | Phase 19 | Complete |
| PFR-03 | Phase 19 | Complete |
| PFR-04 | Phase 19 | Complete |
| CAT-07 | Phase 20 | Complete |
| CAT-08 | Phase 20 | Complete |
| CAT-09 | Phase 20 | Complete |
| DRF-01 | Phase 20 | Complete |
| DRF-02 | Phase 20 | Complete |
| DRF-03 | Phase 20 | Complete |
| WFC-01 | Phase 21 | Complete |
| WFC-02 | Phase 21 | Complete |
| WFC-03 | Phase 21 | Complete |
| ERR-01 | Phase 21 | Complete |
| ERR-02 | Phase 21 | Complete |
| ERR-03 | Phase 21 | Complete |
| ERR-04 | Phase 21 | Complete |
| RSP-01 | Phase 22 | Complete |
| RSP-02 | Phase 22 | Complete |
| RSP-03 | Phase 22 | Complete |
| ENV-01 | TBD | Pending |
| ENV-02 | TBD | Pending |
| ENV-03 | TBD | Pending |
| ENV-04 | TBD | Pending |
| ENV-05 | TBD | Pending |
| BAT-01 | TBD | Pending |
| BAT-02 | TBD | Pending |
| BAT-03 | TBD | Pending |
| BAT-04 | TBD | Pending |
| BAT-05 | TBD | Pending |
| PRT-01 | TBD | Pending |
| PRT-02 | TBD | Pending |
| PRT-03 | TBD | Pending |
| PRT-04 | TBD | Pending |
| PRT-05 | TBD | Pending |
| PRT-06 | TBD | Pending |
| SEC-01 | TBD | Pending |
| SEC-02 | TBD | Pending |
| SEC-03 | TBD | Pending |
| SEC-04 | TBD | Pending |
| SEC-05 | TBD | Pending |
| SEC-06 | TBD | Pending |
| KPI-01 | TBD | Pending |
| KPI-02 | TBD | Pending |
| KPI-03 | TBD | Pending |
| KPI-04 | TBD | Pending |
| URI-01 | TBD | Pending |
| URI-02 | TBD | Pending |
| URI-03 | TBD | Pending |
| URI-04 | TBD | Pending |
| URI-05 | TBD | Pending |
| URI-06 | TBD | Pending |
| BRIDGE-01 | TBD | Pending |
| BRIDGE-02 | TBD | Pending |
| BRIDGE-03 | TBD | Pending |
| BRIDGE-04 | TBD | Pending |
| BRIDGE-05 | TBD | Pending |
| VLAN-01 | TBD | Pending |
| VLAN-02 | TBD | Pending |
| VLAN-03 | TBD | Pending |
| VLAN-04 | TBD | Pending |
| PAG-01 | Phase 33 | Pending |
| PAG-02 | Phase 33 | Pending |
| PAG-03 | Phase 33 | Pending |
| PAG-04 | Phase 33 | Pending |
| PAG-05 | Phase 33 | Pending |
| PAG-06 | Phase 33 | Pending |
| DISC-01 | Phase 33 | Complete |
| DISC-02 | Phase 33 | Complete |
| REG-01 | Phase 33 | Pending |
| REG-02 | Phase 33 | Pending |
| REG-03 | Phase 33 | Pending |
| TEST-01 | TBD | Pending |
| TEST-02 | TBD | Pending |
| TEST-03 | TBD | Pending |

**Coverage:**
- v1.4 requirements: 20 total — all complete ✓
- v1.5 requirements: 24 total — pending roadmap
- v1.6 requirements: 8 total — all complete ✓
- v1.7 requirements: 15 total — all complete ✓
- v1.8 requirements: 11 total — Phase 33

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-30 after v1.8 milestone kickoff*

## v1.10 Requirements

### CMS-Query-Performance (CQP)

- [ ] **CQP-01**: `get_interface_detail` makes ≤3 HTTP calls regardless of device unit count (1 bulk families, 1 bulk VRRP, 1 bulk units) — eliminates per-unit family refetch N+1
- [ ] **CQP-02**: `get_device_firewall_summary` with `detail=True` makes ≤6 HTTP calls regardless of filter/policer count — eliminates per-filter/policer loop N+1
- [ ] **CQP-03**: `get_device_routing_table` removes per-route nexthop fallback loop; bulk nexthop map is considered complete
- [ ] **CQP-04**: `get_device_bgp_summary` guards per-neighbor AF/policy fallback behind `len(af_by_nbr) > 0` and `len(policy_by_nbr) > 0` checks
- [ ] **CQP-05**: All N+1 fixes preserve existing `WarningCollector` partial-failure behavior

### Regression-Gate (RGP)

- [ ] **RGP-01**: `uat_cms_smoke.py` validates all 5 workflows pass within thresholds on HQV-PE1 (all: <60s)
- [ ] **RGP-02**: All existing unit tests continue to pass — no regression from refactored code paths

## Out of Scope (v1.10)

| Feature | Reason |
|---------|--------|
| Global (non-device-scoped) bulk fetches | AF/policy endpoints timeout at >60s globally |
| Remove all fallback patterns entirely | Tests and real environments differ |
| asyncio/httpx/aiohttp rewrite | Full async rewrite; codebase committed to sync |

## Traceability (v1.10)

| Requirement | Phase | Status |
|-------------|-------|--------|
| CQP-01 | Phase 35 | Pending |
| CQP-02 | Phase 36 | Pending |
| CQP-03 | Phase 37 | Pending |
| CQP-04 | Phase 37 | Pending |
| CQP-05 | Phase 35 | Pending |
| RGP-01 | Phase 38 | Pending |
| RGP-02 | Phase 38 | Pending |

**Coverage:**
- v1.10 requirements: 7 total
- Mapped to phases: 0 (roadmap pending)
- Unmapped: 0 ✓

---
*Last updated: 2026-03-31 after v1.10 milestone kickoff*

