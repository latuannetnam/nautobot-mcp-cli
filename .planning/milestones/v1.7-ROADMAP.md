# Roadmap: nautobot-mcp-cli

**Created:** 2026-03-26
**Granularity:** Coarse (3-5 phases per milestone)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-18) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Agent-Native MCP Tools** — Phases 5-7 (shipped 2026-03-20) — [Archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Juniper CMS Model MCP Tools** — Phases 8-14 (shipped 2026-03-21) — [Archive](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 API Bridge MCP Server** — Phases 15-18 (shipped 2026-03-25) — [Archive](milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 Operational Robustness** — Phases 19-22 (shipped 2026-03-26) — [Archive](milestones/v1.4-ROADMAP.md)
- ✅ **v1.5 Agent Performance & Quality** — Phases 23-27 (scope only — not built; requirements deferred) — [Archive](milestones/v1.5-ROADMAP.md)
- ✅ **v1.6 Query Performance Optimization** — Phases 28-29 (shipped 2026-03-28) — [Archive](milestones/v1.6-ROADMAP.md)
- ⏳ **v1.7 URI Limit & Server Resilience** — Phases 30-32 (not started)

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

<details>
<summary>✅ v1.5 Agent Performance & Quality (Phases 23-27) — NOT BUILT</summary>

- [~] Phase 23: Contract & Envelope Stability (ENV-01..ENV-05) — not started
- [~] Phase 24: Batch Execution Engine (BAT-01..BAT-05) — not started
- [~] Phase 25: Projection & Token Efficiency (PRT-01..PRT-06) — not started
- [~] Phase 26: Security & Resource Guardrails (SEC-01..SEC-06) — not started
- [~] Phase 27: KPI Benchmarks & Verification (KPI-01..KPI-04) — not started

*Scope only — requirements deferred to next milestone*

</details>

<details>
<summary>✅ v1.6 Query Performance Optimization (Phases 28-29) — SHIPPED 2026-03-28</summary>

- [x] Phase 28: Adaptive Count & Fast Pagination (1/1 plan) — completed 2026-03-28
- [x] Phase 29: Direct /count/ Endpoint & Consistency (1/1 plan) — completed 2026-03-28

</details>

### v1.7 URI Limit & Server Resilience (Not Started)

<details>
<summary>Phase 30: Direct HTTP Bulk Fetch for get_device_ips() — fix 414 at the source</summary>

**Goal:** Replace all `.filter(id__in=chunk)` and `.filter(interface=chunk)` in `ipam.py get_device_ips()` with direct HTTP calls using DRF comma-separated format.

**Requirements:** URI-01, URI-02, URI-03, URI-04, URI-05, URI-06

**Success criteria:**
1. `get_device_ips()` uses `client.api.http_session.get()` for both M2M and IP bulk fetch passes — no `.filter()` loops
2. Both passes use comma-separated `?interface=uuid1,uuid2` and `?id__in=uuid1,uuid2` format
3. Pagination is followed when `next` link is present in HTTP response
4. Raw HTTP responses are wrapped into pynautobot `Record` objects via `return_obj()`
5. Empty ID sets are handled with early return — no HTTP call with empty ID list
6. Unit tests cover: normal device with IPs, device with no IPs, device with > 500 IPs

</details>

<details>
<summary>Phase 31: Bridge Param Guard — prevent 414 from external callers</summary>

**Goal:** Add `_guard_filter_params()` in `bridge.py` to intercept oversized `__in` lists in `params` before they reach `.filter()`.

**Requirements:** BRIDGE-01, BRIDGE-02, BRIDGE-03, BRIDGE-04, BRIDGE-05

**Success criteria:**
1. `_execute_core()` raises `NautobotValidationError` when any `__in` param has > 500 items
2. `_execute_cms()` raises `NautobotValidationError` for the same condition
3. Lists ≤ 500 in `__in` params are converted to comma-separated strings before `.filter()` call
4. Non-`__in` list params (`tag=[foo, bar]`) pass through unchanged
5. Unit tests cover: small list (≤ 500) works, large list (> 500) raises error, non-`__in` lists pass through

</details>

<details>
<summary>Phase 32: VLANs 500 Fix + Regression Tests</summary>

**Goal:** Fix VLANs 500 by passing location UUID instead of name to `/count/`. Add regression tests and live verification.

**Requirements:** VLAN-01, VLAN-02, VLAN-03, VLAN-04, TEST-01, TEST-02, TEST-03

**Success criteria:**
1. All `client.count("ipam", "vlans", location=...)` call sites pass `location=<uuid>` (resolved) instead of `location=<name>`
2. `client.count()` catches HTTP 500 as a safety fallback — returns `None`, does not raise
3. `None` counts display as `null` in CLI output — no crash or error message
4. Warning is added to output when VLAN count fails
5. All existing unit tests pass — no regression
6. `uv run nautobot-mcp --profile prod --json ipam addresses device-ips HQV-PE1-NEW` completes without 414
7. `uv run nautobot-mcp --profile prod --json devices inventory HQV-PE1-NEW --detail ips --limit 0` completes without 414

</details>

---
*Last updated: 2026-03-29 — v1.7 roadmap defined*
