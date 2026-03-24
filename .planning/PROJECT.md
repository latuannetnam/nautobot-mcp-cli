# nautobot-mcp-cli

## What This Is

An MCP server, CLI tool, and agent skills library that enables AI agents to interact with Nautobot for network automation. It provides 164 structured tools for managing network infrastructure data in Nautobot — devices, interfaces, IP addresses, VLANs, circuits, Golden Config, and full Juniper CMS model coverage (BGP, routing, interfaces, firewalls, policies, ARP) — and integrates with vendor-specific MCP servers (Juniper jmcp) to bridge the gap between live network state and Nautobot as the source of truth.

## Core Value

AI agents can read and write Nautobot data — including Juniper CMS model records — through standardized MCP tools, enabling automated network configuration management, file-free drift comparison against Nautobot's source of truth, and comprehensive device audits that chain live device state (jmcp) against CMS records.

## Current State: v1.3 In Progress 🔄

**Previous:** v1.2 Juniper CMS Model MCP Tools (shipped 2026-03-21)

## Current Milestone: v1.3 API Bridge MCP Server

**Goal:** Re-architect MCP server from 165 individual tools to 3 tools (`nautobot_api_catalog`, `call_nautobot`, `run_workflow`) + agent skills, solving context window bloat and agent accuracy degradation.

**Target features:**
- API Catalog engine (static core + dynamic CMS plugin discovery)
- Universal REST bridge (`call_nautobot`) with endpoint routing, validation, auto-pagination
- Workflow registry (`run_workflow`) wrapping existing composite domain functions
- Agent skills distributed as files (not served via MCP)
- Clean break migration (no backwards compatibility aliases)
- Full test coverage with UAT against Nautobot dev server

**Design:** [API Bridge MCP Architecture Design v2](docs/plans/2026-03-24-api-bridge-mcp-design.md)

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

### Active

- [ ] API Catalog engine — static core + dynamic CMS plugin discovery
- [ ] Universal REST bridge — endpoint routing, validation, auto-pagination
- [ ] Workflow registry — server-side composite workflows
- [ ] Agent skills — distributed as files, referencing new 3-tool API
- [ ] Consolidated server.py (~200 lines / 3 tools replacing 3,883 / 165 tools)
- [ ] Updated tests + UAT against Nautobot dev

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
| API Bridge MCP Server (v1.3) | 165 tools → 3 via catalog + REST bridge + workflows; 96% token reduction | In progress |

## Constraints

- **Protocol**: MCP (Model Context Protocol) for AI agent interaction
- **Language**: Python (pyproject.toml with uv)
- **Nautobot API**: REST API v2 at https://nautobot.netnam.vn/
- **CMS Plugin API**: netnam-cms-core plugin REST API at /api/plugins/netnam-cms-core/
- **Vendor scope**: Juniper first, extensible VendorParser ABC for others
- **Dependencies**: Works alongside existing jmcp — complementary, not replacing

---
*Last updated: 2026-03-24 after v1.3 pivot from Generic Resource Engine to API Bridge*
