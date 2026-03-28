# Requirements: nautobot-mcp-cli v1.5

**Defined:** 2026-03-26
**Core Value:** AI agents can discover, read, write, and orchestrate Nautobot data through 3 tools — with predictable contracts, minimal round-trips, compact responses, and production-grade reliability.

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

**Coverage:**
- v1.4 requirements: 20 total — all complete ✓
- v1.5 requirements: 24 total — pending roadmap
- v1.6 requirements: 8 total — Phases 28-29 defined

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 after v1.6 milestone kickoff*
