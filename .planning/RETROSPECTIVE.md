# Retrospective

Living milestone retrospective for nautobot-mcp-cli.

---

## Milestone: v1.2 — Juniper CMS Model MCP Tools

**Shipped:** 2026-03-21
**Phases:** 6 | **Plans:** 18 | **Commits:** 62

### What Was Built

- Full CRUD for 5 Juniper CMS model domains: routing (BGP + static routes), interfaces (units, families, VRRP), firewalls, policies, ARP — 118 MCP tools total
- 4 composite summary tools: `get_device_bgp_summary`, `get_device_routing_table`, `get_interface_detail`, `get_device_firewall_summary`
- DiffSync-based CMS drift engine: `compare_bgp_neighbors` + `compare_static_routes`
- `nautobot-mcp cms` CLI covering all new model domains + drift
- `cms-device-audit` agent skill for 8-step jmcp → CMS audit workflow
- 293 unit tests (up from 105 at v1.1)

### What Worked

- **1:1 Pydantic model strategy** — mirroring the API shape exactly eliminated impedance mismatch friction; adding new endpoints was mechanical and fast
- **Phase-by-domain split** — one phase per model domain (routing/interfaces/firewalls/policies) kept each session focused; no cross-domain coordination overhead
- **Composite tools planned from the start** — building composite aggregators in Phase 12 *after* all primitive CRUD was in place was the right order; composites were thin wrappers
- **DiffSync for drift** — reusing DiffSync patterns from v1.1 `nautobot_compare_device` made the CMS drift engine natural; same report format, same adapter pattern
- **Tests written per-phase** — never accumulated a test debt, each plan included its own tests

### What Was Inefficient

- **CLI extraction needed a separate phase** — CLI commands for CMS tools were scattered across model phases; Phase 14 had to extract drift CLI from routing CLI; better to define CLI modules as part of each model phase from the start
- **REQUIREMENTS.md never ticked during execution** — 35 requirements were all left `[ ]` and had to be bulk-ticked at milestone completion; next milestone should tick off requirements as each plan completes
- **Phase 12 scope grew mid-phase** — composite tools + ARP were combined; ended up being 4 plans instead of 2; should be separate phases next time

### Patterns Established

- `nautobot_mcp/cms/<domain>.py` — one module per CMS model domain, with CRUD functions and composite helpers
- `nautobot_mcp/models/cms/<domain>.py` — one Pydantic model file per domain
- `nautobot_mcp/cli/cms_<domain>.py` — one CLI module per domain, registered under `nautobot-mcp cms <domain>`
- DiffSync adapters: `Live<Model>Adapter` + `CMS<Model>Adapter` pair per drift comparison
- Composite tools return a typed `*Response` model with counts + nested data

### Key Lessons

- Always include CLI module stub as part of each model domain plan — not as a separate phase
- Tick REQUIREMENTS.md requirements off during execution, not at milestone completion
- Define composite tools in their own phase *after* all primitive CRUD is done — this worked well, keep it
- For CMS-style APIs: start with endpoint registry first (Phase 8 pattern) before adding models — this paid dividends for 14+ subsequent plans

### Cost Observations

- Sessions: ~15 conversations across 2 days (2026-03-20 to 2026-03-21)
- Notable: 62 commits, 98 files, +21,735 lines in under 2 days — high throughput due to mechanical nature of CRUD + Pydantic pattern

---

## Milestone: v1.3 — API Bridge MCP Server

**Shipped:** 2026-03-25
**Phases:** 4 (Phases 15-18) | **Plans:** 8 | **Commits:** 38

### What Was Built

- API Catalog engine (`nautobot_api_catalog`) — static core endpoints + dynamic CMS plugin discovery, domain filtering, workflow stubs
- Universal REST bridge (`nautobot_call_nautobot`) — endpoint routing, fuzzy-matching error hints, auto-pagination, CMS prefix routing
- Workflow registry (`nautobot_run_workflow`) — 10 composite workflows wrapping existing domain functions with parameter normalization and response envelopes
- `server.py` consolidated from 3,883 lines / 165 tools to ~200 lines / 3 tools (96% token reduction)
- All 3 agent skills rewritten for 3-tool API: `cms-device-audit`, `onboard-router-config`, `verify-compliance`
- UAT test suite: 11 pytest tests (`@pytest.mark.live`) + 9-check standalone smoke script; both validated against dev server
- 397 unit tests passing, CI/CD clean with `live` marker exclusion

### What Worked

- **Rejected milestone pivot worked cleanly** — Generic Resource Engine was rejected and replaced by API Bridge in the same sprint day; the GSD planning structure made this pivot cost-free (no code written, just planning artifacts)
- **3-tool architecture proved correct** — the catalog → call → workflow progression matched how agents actually reason about unfamiliar APIs; zero backwards-compat aliases needed
- **CMS routing via `cms:` prefix** — elegant extension point; agents use the same `call_nautobot` tool for both Nautobot core REST and CMS plugin endpoints
- **UAT as first-class gate** — requiring 11 live tests to pass against dev server before closing the milestone caught real integration issues that unit tests would have missed
- **Smoke script for quick validation** — standalone `uat_smoke_test.py` is useful for non-pytest verification (ops team, CI without test deps)

### What Was Inefficient

- **REQUIREMENTS.md traceability lag** — WFL-* and SVR-* requirements were all implemented in Phase 17 but not ticked; had to bulk-tick at milestone completion again (same v1.2 problem — not yet fixed as a habit)
- **Smoke script Windows encoding bug** — Unicode ✓/✗ characters broke on Windows CP1252 terminal; should default to ASCII-safe output from the start on any cross-platform script
- **Architecture pivot consumed 1 session** — the Generic Resource Engine research session was not wasted (informed the API Bridge design) but ideally the pivot decision should be faster

### Patterns Established

- 3-tool pattern: `catalog` (discover) → `call_nautobot` (CRUD) → `run_workflow` (composite) — add new workflows to `WORKFLOW_REGISTRY`, never new MCP tools
- Response envelope: `{"status": "ok|error", "workflow": "id", "data": {...}}` — all workflow outputs standardized
- `@pytest.mark.live` + `addopts = "-m 'not live'"` — live server tests always excluded from CI by default; run explicitly with `-m live`
- Agent skills as `.md` files in `nautobot_mcp/skills/` — not served via MCP, distributed as part of the package

### Key Lessons

- Tick REQUIREMENTS.md at plan completion, not milestone completion — set this as a habit in the phase execution workflow
- Use ASCII-safe output for cross-platform scripts from day 1 (avoid Unicode symbols)
- The "clean break" migration (no backwards-compat aliases) was the right call — made the code dramatically simpler
- UAT smoke scripts should be OS-agnostic and test the same logic as pytest UAT for redundancy

### Cost Observations

- Sessions: ~8 conversations across 1 day (2026-03-24 to 2026-03-25)
- Notable: 38 commits, 54 files changed, +8,169 lines — significantly more efficient than v1.2 despite architectural complexity; API Bridge design was well-specified before implementation began

---

## Milestone: v1.4 — Operational Robustness

**Shipped:** 2026-03-26
**Phases:** 4 (19-22) | **Plans:** 7 | **Commits:** 55 | **Duration:** 2 days

### What Was Built

- **Partial failure resilience** — `WarningCollector`, 3-tier status (`ok`/`partial`/`error`), all 4 composites return `(result, warnings)` tuples; co-primaries pattern in `firewall_summary` (filters + policers fetched independently)
- **Import-time registry validation** — `_validate_registry()` at module load; caught 3 pre-existing bugs (wrong param keys, wrong required list, too-strict validation)
- **Error diagnostics** — DRF 400 body parsing (field-level errors), `ERROR_HINTS` (10 endpoint-specific hints), `STATUS_CODE_HINTS` (429/500/502/503/504), status-code-derived `NautobotAPIError` defaults
- **Catalog accuracy** — Per-endpoint `CMS_ENDPOINT_FILTERS` (43 entries) replaces domain-level `CMS_DOMAIN_FILTERS`; agents see correct FK filters for all CMS endpoints
- **UUID path normalization** — REST bridge strips UUID from `/api/.../<uuid>/` paths; linked object URLs work directly
- **Response ergonomics** — `response_size_bytes` in all envelopes; `detail=False` summary mode (strips `families[]`/`vrrp_groups[]`); `limit=N` independently caps all nested arrays
- 476 unit tests (up from 397 at v1.3), 14 new tests for RSP features

### What Worked

- **WarningCollector as shared pattern** — single dataclass used consistently across all 4 composites; envelope shape stays uniform regardless of which operation fails
- **Import-time validation found real bugs** — `_validate_registry()` immediately caught 3 pre-existing registry bugs that had never been validated; the self-check pattern is now proven to pay for itself
- **Bug found and fixed mid-execution** — Phase 22 caught a missing `limit` cap in the BGP else branch (`bc191f8`); verification step proved its value
- **GSD verification gate before UAT** — `VERIFICATION.md` was written with explicit code-line checks before running pytest; caught the BGP bug before it reached tests
- **UAT done programmatically** — ran pytest suites directly rather than prompting user for each test; covered 14 tests across 3 suites in parallel

### What Was Inefficient

- **REQUIREMENTS.md checkboxes still not ticked during execution** — same problem as v1.2 and v1.3: PFR-01 through PFR-04 were all implemented in Phase 19 but left unchecked until milestone completion; still not a habit
- **Phase 22 had no separate plan for UAT** — `22-PLAN.md` conflated implementation and UAT in 11 tasks; smoke test development happened in the implementation wave instead of as a separate gate
- **No live smoke run** — the smoke script requires a live Nautobot dev server and was marked "manual" in VERIFICATION.md; real end-to-end validation never ran in CI

### Patterns Established

- `WarningCollector` + tuple return pattern: `(result, warnings)` — use this for all future composite functions
- Three-tier status: `ok` → `partial` → `error` with appropriate `warnings` list — never bare string errors
- `_validate_registry()` at module import: call it at the bottom of `workflows.py` so it runs at import time
- ERR-03 pattern: exception → `{operation, error}` dict in `warnings[]` — preserves `status: error` while adding provenance
- Independent co-primaries: fetch parallel resources independently, aggregate warnings if one fails, raise if both fail

### Key Lessons

- **Tick REQUIREMENTS.md checkboxes at plan completion** — not at milestone completion; make it part of the execute-phase workflow's "close plan" step
- **Keep UAT as a separate verification gate** — smoke test and pytest UAT should be Wave N+1, not woven into implementation tasks
- **Mark "requires live server" tests clearly** — if smoke/UAT requires dev server, that should be a known gap before milestone close, not discovered at UAT time
- **Verification.md before pytest** — writing explicit line-level code checks (e.g., "L666 present") catches bugs before they reach tests

### Cost Observations

- Sessions: ~12 conversations across 2 days (2026-03-25 to 2026-03-26)
- Notable: 55 commits, 371 files, +60,732 lines — highest LOC added per session of any milestone, partly due to large test suite expansion (79 new tests across phases 19-22)

---

## Milestone: v1.6 — Query Performance Optimization

**Shipped:** 2026-03-28
**Phases:** 2 (Phases 28-29) | **Plans:** 2 | **Commits:** 14 | **Duration:** ~1 day

### What Was Built

- **Adaptive count skipping (Phase 28)** — `skip_count` plumbed through CLI → MCP tool → bridge → `get_device_inventory()`; paginated requests no longer waste O(n) count fetches; `has_more` inferred from `len(results) == limit`
- **Per-section timing instrumentation (Phase 28)** — `interfaces_latency_ms`, `ips_latency_ms`, `vlans_latency_ms`, `total_latency_ms` in `DeviceInventoryResponse`; parallel counts via `ThreadPoolExecutor(max_workers=3)` for `detail=all`
- **`NautobotClient.count()` O(1) (Phase 29)** — `NautobotClient.count(app, endpoint, **filters)` calls `GET /api/{app}/{endpoint}/count/?...` directly via `http_session.get`, bypassing pynautobot's O(n) auto-pagination; 404 fallback to pynautobot for plugin endpoints
- **`latency_ms` in bridge (Phase 29)** — wall-clock timing added to every `call_nautobot` success response via `t_start = time.time()` before try block; covers full execution including `resolve_device_id` for CMS calls
- **All 8 call sites migrated (Phase 29)** — `devices.py` fully migrated from `.count()` to `client.count()`; zero raw `.count()` occurrences remain

### What Worked

- **Root-cause driven scope** — v1.6 scope was derived from a single concrete performance problem (`--limit 5` slow for large devices); having a reproducible benchmark target made success unambiguous
- **v1.5 skipped cleanly** — Phase 23-27 (Contract, Batch, Projection, Security, KPI) were never planned/built; accepted this and focused on what was actually needed; avoided scope pollution
- **Exact code in plans** — Phase 29 plan contained exact method implementations (the `count()` method code); eliminated implementation ambiguity, reduced task-level back-and-forth

### What Was Inefficient

- **Requirements traceability still lagging** — PERF-01..PERF-04, OBS-01..OBS-02, UX-01..UX-02 were all implemented across phases 28-29 but not ticked in REQUIREMENTS.md until milestone close; this is the 4th consecutive milestone with this problem
- **Two-phase execution for one feature** — count optimization could have been a single phase (28) with all three implementations: skip in `get_device_inventory`, `client.count()`, and `latency_ms`; splitting across phases added planning overhead with no benefit
- **No live performance benchmark** — the performance improvement was verified via code inspection and unit tests; no actual before/after latency comparison against a real Nautobot server

### Patterns Established

- `NautobotClient.count()` pattern: `http_session.get` → check `resp.ok` → return `resp.json()["count"]` → 404 fallback → non-404 `raise_for_status()`
- `ThreadPoolExecutor(max_workers=3)` for parallel count fan-out — shared with Phase 28 parallel counts
- Wall-clock timing: `t_start = time.time()` before try block, `latency_ms = round((time.time() - t_start) * 1000, 1)` after success
- `skip_count` as first-class parameter: CLI flag → MCP tool param → bridge param → function param (never optional in the wrong layer)

### Key Lessons

- **Write live benchmarks** — add a simple `time.time()` measurement against the real Nautobot server before and after performance work; validates the improvement actually matters
- **Tick REQUIREMENTS.md checkboxes at plan close** — this has been a known problem since v1.2 and is still unresolved; make it a hard requirement in the plan execution workflow checklist
- **Two-phase for one feature = overhead** — Phase 28 and 29 were functionally the same feature split artificially; consolidate similar work into single phases
- **Scope must match execution** — planning 23-27 for v1.5 and shipping 28-29 for v1.6 meant milestone scope never matched what was built; always align ROADMAP with what you plan to build, not aspirational goals

### Cost Observations

- Sessions: ~3 conversations across 1 day (2026-03-28)
- Notable: 14 commits, 17 files, +1,193 / -63 lines — lean milestone; concentrated single-focus work with minimal overhead

---

## Cross-Milestone Trends

| Milestone | Duration | Commits | Files | Lines Added | MCP Tools | Tests |
|-----------|----------|---------|-------|-------------|-----------|-------|
| v1.0 | 1 day | ~30 | ~60 | ~10k | 44 | 76 |
| v1.1 | 1 day | ~25 | 75 | +8,225 | 46 | 105 |
| v1.2 | 2 days | 62 | 98 | +21,735 | 164 | 293 |
| v1.3 | 1 day | 38 | 54 | +8,169 | 3 (+ 10 workflows) | 397+11 UAT |
| v1.4 | 2 days | 55 | 371 | +60,732 | 3 (+ 10 workflows) | 476+11 UAT |
| v1.6 | 1 day | 14 | 17 | +1,193 | 3 (+ 10 workflows) | 478+11 UAT |

**Trend:** v1.4 expanded test coverage aggressively (476 unit tests, 79 new tests) while keeping MCP tool count flat at 3. The API Bridge pattern from v1.3 means all new features are additive workflows, never new tools. Error diagnostics and registry validation added infrastructure depth rather than surface area.
