# nautobot-mcp-cli

## What This Is

An MCP server, CLI tool, and agent skills library that enables AI agents to interact with Nautobot for network automation. The v1.4 API Bridge consolidates 165 individual tools into 3 universal tools (`nautobot_api_catalog`, `nautobot_call_nautobot`, `nautobot_run_workflow`) plus distributed agent skills — covering devices, interfaces, IP addresses, VLANs, circuits, and full Juniper CMS model coverage (BGP, routing, interfaces, firewalls, policies, ARP). Integrates with vendor-specific MCP servers (Juniper jmcp) to bridge live network state with Nautobot as the source of truth. Ships with partial failure resilience, import-time registry validation, actionable error diagnostics, and response ergonomics controls.

## Core Value

AI agents can discover, read, write, and orchestrate all Nautobot data through 3 tools instead of 165, eliminating context window bloat while preserving full functional coverage — including Juniper CMS model records, file-free drift comparison, and composite workflows for common network automation tasks.

## Current Milestone: v1.5 MCP Server Quality & Agent Performance

**Goal:** Improve MCP server quality and optimize for AI agents by reducing round-trips and response token size while hardening reliability, observability, and transport security.

**Target features:**
- P0: Agent-efficiency core upgrades (unified response envelope, `response_mode`, `fields` projection, workflow batch execution)
- P1: Reliability/security/agent guidance improvements (retryable error metadata, HTTP auth hardening, catalog guidance hints)
- P2: Ops + performance maturity (discovery caching, benchmark harness + KPI tracking, health/diagnostic endpoint)

**Previous milestones:** v1.0 MVP (2026-03-18) → v1.1 Agent-Native (2026-03-20) → v1.2 Juniper CMS (2026-03-21) → v1.3 API Bridge (2026-03-25) → v1.4 Operational Robustness (2026-03-26)

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

- [ ] Reduce average AI task round-trips by introducing workflow-level batching and recommended call paths
- [ ] Reduce response payload size with standardized compact modes and field projection
- [ ] Standardize tool response envelope and error semantics for predictable agent planning and retries
- [ ] Improve transport-level security and operational observability for interactive and headless deployments
- [ ] Establish performance baselines and KPI tracking for latency, token footprint, and success rate

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
*Last updated: 2026-03-26 after v1.5 milestone kickoff*
