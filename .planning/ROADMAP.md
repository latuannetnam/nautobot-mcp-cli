# Roadmap: nautobot-mcp-cli

**Created:** 2026-03-26
**Granularity:** Coarse (3-5 phases per milestone)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-18) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Agent-Native MCP Tools** — Phases 5-7 (shipped 2026-03-20) — [Archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Juniper CMS Model MCP Tools** — Phases 8-14 (shipped 2026-03-21) — [Archive](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 API Bridge MCP Server** — Phases 15-18 (shipped 2026-03-25) — [Archive](milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 Operational Robustness** — Phases 19-22 (shipped 2026-03-26) — [Archive](milestones/v1.4-ROADMAP.md)
- 🔄 **v1.5 Agent Performance & Quality** — Phases 23-27 (planning) — [Current](ROADMAP.md)
- ⏳ **v1.6 Query Performance Optimization** — Phases 28-29 — [Current](ROADMAP.md)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-03-18</summary>

- [x] Phase 1: Core Foundation & Nautobot Client (4/4 plans)
- [x] Phase 2: MCP Server & CLI (3/3 plans)
- [x] Phase 3: Golden Config & Config Parsing (3/3 plans)
- [x] Phase 4: Onboarding, Verification & Agent Skills (3/3 plans)

</details>

<details>
<summary>✅ v1.1 Agent-Native MCP Tools (Phases 5-7) — SHIPPED 2026-03-20</summary>

- [x] Phase 5: Device-Scoped IP Queries & Cross-Entity Filters (2/2 plans)
- [x] Phase 6: Device Summary & Enriched Interface Data (2/2 plans)
- [x] Phase 7: File-Free Drift Comparison (2/2 plans)

</details>

<details>
<summary>✅ v1.2 Juniper CMS Model MCP Tools (Phases 8-14) — SHIPPED 2026-03-21</summary>

- [x] Phase 8: CMS Plugin Client Foundation (2/2 plans)
- [x] Phase 9: Routing Models — Static Routes & BGP (3/3 plans)
- [x] Phase 10: Interface Models — Units, Families, VRRP (3/3 plans)
- [x] Phase 11: Firewall & Policy Models (3/3 plans)
- [x] Phase 12: ARP & Composite Summary Tools (4/4 plans)
- [x] Phase 13: CMS Drift Verification (2/2 plans)
- [x] Phase 14: CLI Commands & Agent Skill Guides (2/2 plans)

</details>

<details>
<summary>✅ v1.3 API Bridge MCP Server (Phases 15-18) — SHIPPED 2026-03-25</summary>

- [x] Phase 15: Catalog Engine & Core Endpoints (2/2 plans) — completed 2026-03-24
- [x] Phase 16: REST Bridge & Universal CRUD (2/2 plans) — completed 2026-03-24
- [x] Phase 17: Workflow Registry & Server Consolidation (2/2 plans) — completed 2026-03-24
- [x] Phase 18: Agent Skills, Tests & UAT (2/2 plans) — completed 2026-03-25

</details>

<details>
<summary>✅ v1.4 Operational Robustness (Phases 19-22) — SHIPPED 2026-03-26</summary>

- [x] Phase 19: Partial Failure Resilience (2/2 plans) — completed 2026-03-25
- [x] Phase 20: Catalog Accuracy & Endpoint Dereference (2/2 plans) — completed 2026-03-26
- [x] Phase 21: Workflow Contracts & Error Diagnostics (2/2 plans) — completed 2026-03-26
- [x] Phase 22: Response Ergonomics & UAT (1/1 plan) — completed 2026-03-26

</details>

### v1.5 Agent Performance & Quality (Phases 23-27)

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|-------------|----------------|
| 23 | Contract & Envelope Stability | Standardize response envelopes, error contracts, and catalog capabilities | ENV-01, ENV-02, ENV-03, ENV-04, ENV-05 | 5 |
| 24 | Batch Execution Engine | Workflow batch with per-item envelopes and partial-success semantics | BAT-01, BAT-02, BAT-03, BAT-04, BAT-05 | 5 |
| 25 | Projection & Token Efficiency | Response modes, field projection, minimal compact output | PRT-01, PRT-02, PRT-03, PRT-04, PRT-05, PRT-06 | 6 |
| 26 | Security & Resource Guardrails | Endpoint allowlist, auth hardening, resource limits | SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06 | 6 |
| 27 | KPI Benchmarks & Verification | Observability, metrics endpoint, benchmark harness, UAT | KPI-01, KPI-02, KPI-03, KPI-04 | 4 |
| 28 | Adaptive Count & Fast Pagination | Skip count when paginating; infer has_more; add timing instrumentation | Complete    | 2026-03-28 |
| 29 | Direct /count/ Endpoint & Consistency | O(1) count fallback; replace all count() calls; add latency to bridge | PERF-03, PERF-04, OBS-02 | 3 |

#### Phase Details

**Phase 23: Contract & Envelope Stability**
Goal: Standardize response metadata, error semantics, and catalog capability discovery across all 3 MCP tools without breaking existing clients.
Requirements: ENV-01, ENV-02, ENV-03, ENV-04, ENV-05
Success criteria:
1. All 3 MCP tool responses include `request_id`, `timestamp`, `status`, `warnings`, `latency_ms`, `response_size_bytes`
2. Error responses include `hint` and `retryable` fields; HTTP 429/502/503/504 include `retry_after`
3. `nautobot_api_catalog` returns `capabilities` block with supported modes, limits, and policies
4. Existing agent skills and clients work unchanged in default mode
5. Contract snapshot tests pass for all 3 tools

**Phase 24: Batch Execution Engine**
Goal: Add batch execution to `nautobot_run_workflow` with isolated per-item results and aggregate partial-success status.
Requirements: BAT-01, BAT-02, BAT-03, BAT-04, BAT-05
Success criteria:
1. Batch mode fans out same workflow to multiple targets in one tool call
2. Successful items are preserved when other items fail (no all-or-nothing)
3. Aggregate `status` reflects `ok/partial/error` correctly
4. Each batch item validates through the same path as single calls
5. Resource limits (`max_batch_items`, per-item `limit` caps) enforced

**Phase 25: Projection & Token Efficiency**
Goal: Add response modes and field projection to reduce token footprint while maintaining agent actionability.
Requirements: PRT-01, PRT-02, PRT-03, PRT-04, PRT-05, PRT-06
Success criteria:
1. `options.response_mode` (`full`/`standard`/`minimal`) accepted by both `call_nautobot` and `run_workflow`
2. `options.fields` (jmespath projection) works on all result shapes
3. Unknown projection fields rejected with validation error
4. Identity fields (`id`, `url`) always included regardless of projection
5. Projection applied consistently across both core and CMS execution paths
6. `minimal` mode strips nested arrays, keeps counts and top-level fields

**Phase 26: Security & Resource Guardrails**
Goal: Harden the MCP server boundary with endpoint allowlist, optional auth, and resource limits.
Requirements: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06
Success criteria:
1. Configurable allowlist accepts `/api/`, `cms:`, and registered plugin paths; rejects external URLs
2. UUID path normalization works through all new execution paths
3. Oversized requests (batch count, projection fields, payload size) return deterministic validation error
4. Bearer-token auth available for non-stdio transports (audit-only mode)
5. All tool calls emit structured events with request_id, tool, endpoint, status, latency
6. `/health` readiness endpoint returns version, status, uptime for HTTP transport

**Phase 27: KPI Benchmarks & Verification**
Goal: Establish performance baselines, metrics infrastructure, and UAT validation for all v1.5 capabilities.
Requirements: KPI-01, KPI-02, KPI-03, KPI-04
Success criteria:
1. Benchmark harness measures round-trips/task, response size, p50/p95/p99 latency, error rate, partial-success rate
2. 4 benchmark scenarios pass: catalog discovery, projected list GET, mixed batch workflow, CMS composite
3. KPI targets met: round-trips reduced 40-60%, token footprint reduced 35-55%, p95 < 3s
4. `/metrics` endpoint exposes Prometheus counters and histograms for all tracked dimensions

**Phase 28: Adaptive Count & Fast Pagination**
Goal: Fix `devices inventory` slow performance for large devices by skipping expensive `count()` calls when paginating and adding `--no-count` flag.
Requirements: PERF-01, PERF-02, OBS-01, UX-01, UX-02
Status: ✅ Plan 01 COMPLETE (1/1 plans, 2026-03-28)
Commits: `92cb90f`, `27ea778`, `c68e5ed`, `78620b3`, `498fe80`, `c7206bd`, `1cd0305`
Success criteria:
1. `devices inventory DEVICE --limit N --detail interfaces` returns in <1s for any device (no count fetch)
2. `has_more` is inferred from `len(results) == limit` when count is skipped
3. `devices inventory DEVICE --detail all` fetches all 3 counts concurrently (parallel)
4. `--no-count` flag skips all count operations regardless of detail
5. `devices inventory --json` output includes `interfaces_latency_ms`, `ips_latency_ms`, `vlans_latency_ms`, `total_latency_ms`

**Phase 29: Direct /count/ Endpoint & Consistency**
Goal: Replace all pynautobot `.count()` calls with direct `/count/` endpoint usage for O(1) counts; add latency tracking to bridge.
Requirements: PERF-03, PERF-04, OBS-02
Success criteria:
1. `NautobotClient` exposes `count(endpoint, **filters)` method using direct `/count/` endpoint
2. All `client.api.dcim.interfaces.count(...)` calls in devices.py replaced with direct count method
3. All `client.api.ipam.*.count(...)` calls in ipam.py replaced with direct count method
4. All `count()` in cms/client.py replaced with direct count method
5. `nautobot_call_nautobot` response includes `latency_ms` field

---
*Last updated: 2026-03-28 — v1.6 roadmap created (2 phases)*