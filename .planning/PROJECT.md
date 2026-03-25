# nautobot-mcp-cli

## What This Is

An MCP server, CLI tool, and agent skills library that enables AI agents to interact with Nautobot for network automation. The v1.3 API Bridge consolidates 165 individual tools into 3 universal tools (`nautobot_api_catalog`, `nautobot_call_nautobot`, `nautobot_run_workflow`) plus distributed agent skills — covering devices, interfaces, IP addresses, VLANs, circuits, and full Juniper CMS model coverage (BGP, routing, interfaces, firewalls, policies, ARP). Integrates with vendor-specific MCP servers (Juniper jmcp) to bridge live network state with Nautobot as the source of truth.

## Core Value

AI agents can discover, read, write, and orchestrate all Nautobot data through 3 tools instead of 165, eliminating context window bloat while preserving full functional coverage — including Juniper CMS model records, file-free drift comparison, and composite workflows for common network automation tasks.

## Current Milestone: v1.4 Operational Robustness

**Goal:** Fix confirmed pain points in the MCP bridge to improve partial failure resilience, catalog accuracy, error diagnostics, and response ergonomics.

**Target features:**
- Graceful degradation for composite workflows (partial results + warnings)
- Per-endpoint filter registry replacing incorrect domain-level filter advertisement
- URL dereference support in the REST bridge (linked object follow)
- Fix `verify_data_model` workflow contract (`parsed_config` required + transform)
- Enriched error diagnostics (parse 400 bodies, contextual hints, error provenance)
- Summary mode for large-payload workflows (response size metadata, `limit` param)

**Previous milestones:** v1.0 MVP (2026-03-18) → v1.1 Agent-Native (2026-03-20) → v1.2 Juniper CMS (2026-03-21) → v1.3 API Bridge (2026-03-25)

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

### Active

- ✓ Per-endpoint CMS filter registry — correct FK filters for all 33 CMS endpoints (replaces false `["device"]` for child endpoints) — v1.4 Phase 20
- ✓ UUID path dereference in REST bridge — agents can pass `/api/{app}/{endpoint}/<uuid>/` URLs directly — v1.4 Phase 20

*(See REQUIREMENTS.md for remaining v1.4 requirements)*

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

## Constraints

- **Protocol**: MCP (Model Context Protocol) for AI agent interaction
- **Language**: Python (pyproject.toml with uv)
- **Nautobot API**: REST API v2 at https://nautobot.netnam.vn/
- **CMS Plugin API**: netnam-cms-core plugin REST API at /api/plugins/netnam-cms-core/
- **Vendor scope**: Juniper first, extensible VendorParser ABC for others
- **Dependencies**: Works alongside existing jmcp — complementary, not replacing

---
*Last updated: 2026-03-25 after Phase 20 Catalog Accuracy & Endpoint Dereference completion*
