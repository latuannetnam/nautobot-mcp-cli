# nautobot-mcp-cli

## What This Is

An MCP server, CLI tool, and agent skills library that enables AI agents to interact with Nautobot for network automation. It provides 46 structured tools for managing network infrastructure data in Nautobot — devices, interfaces, IP addresses, VLANs, circuits, Golden Config — and integrates with vendor-specific MCP servers (Juniper jmcp) to bridge the gap between live network state and Nautobot as the source of truth.

## Core Value

AI agents can read and write Nautobot data through standardized MCP tools, enabling automated network configuration management, device-scoped queries, and file-free drift comparison against Nautobot's source of truth.

## Current State: v1.2 Complete ✅

**Shipped 2026-03-21** — v1.2 Juniper CMS Model MCP Tools

Phase 14 complete — all v1.2 requirements met (CLI + Skills):
- `nautobot-mcp cms drift bgp/routes` — CLI drift verification commands
- `.agent/skills/cms-device-audit/SKILL.md` — 8-step CMS-aware device audit skill
- 293 unit tests passing | ~13k LOC Python

**v1.2 Summary — all 7 phases complete:**
- Phase 8: CMS plugin client foundation (`NautobotClient.cms`, 39-endpoint registry)
- Phase 9: Routing models (8 Pydantic models, 14 MCP tools, 13 CLI commands, 22 tests)
- Phase 10: Interface models (full CRUD, device-scoped, VLAN handling)
- Phase 11: Firewall & Policy models (filters, terms, policers, policies)
- Phase 12: ARP and composite summary tools (BGP summary, routing table, interface detail, firewall summary)
- Phase 13: CMS drift verification engine (DiffSync-based, compare_bgp_neighbors, compare_static_routes)
- Phase 14: CLI commands & agent skill guides (drift CLI, CMS device audit skill)

<details>
<summary>v1.0 context (shipped 2026-03-18)</summary>

**Shipped 2026-03-18** with ~3,400 LOC Python, 76 tests, 44 MCP tools.

Requirements validated:
- ✓ MCP server exposing 44+ Nautobot operations as named tools
- ✓ CLI interface for human/script access to all operations
- ✓ Nautobot REST API client with authentication and profile support
- ✓ Device, Interface, IPAM, Organization, Circuit management
- ✓ Golden Config plugin integration
- ✓ JunOS config parser with extensible vendor architecture
- ✓ Config onboarding workflow (parse → dry-run → commit to Nautobot)
- ✓ Config verification workflow (live vs Golden Config + data model drift)
- ✓ Agent skills for multi-step workflows (onboard-router-config, verify-compliance)

</details>

## Current Milestone: v1.2 — Juniper CMS Model MCP Tools

**Goal:** Add full CRUD MCP tools for all Juniper-specific models in the netnam-cms-core Nautobot plugin, plus composite summary tools and live drift verification against CMS model records.

**Target features:**
- Full CRUD MCP tools for all 5 Juniper model domains (Routing, Interfaces, Firewalls, Policies, ARP)
- Composite summary tools (device BGP summary, routing table, interface detail, firewall summary)
- Drift verification: compare live Juniper state (via jmcp) against CMS model records in Nautobot
- CLI commands for all new tools
- Agent skill guides for CMS-aware workflows

<details>
<summary>Candidate features deferred</summary>

- Multi-vendor config parsers (Cisco IOS, Arista EOS)
- Bulk device onboarding (batch config files)
- Config remediation suggestions based on drift reports
- Enhanced "Audit Device" agent skill — comprehensive health check

</details>

## Out of Scope

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
| netnam-cms-core via plugin REST API | Plugin exposes 49 DRF endpoints under /api/plugins/netnam-cms-core/ | — Pending |

## Constraints

- **Protocol**: MCP (Model Context Protocol) for AI agent interaction
- **Language**: Python (pyproject.toml with uv)
- **Nautobot API**: REST API v2 at https://nautobot.netnam.vn/
- **CMS Plugin API**: netnam-cms-core plugin REST API at /api/plugins/netnam-cms-core/
- **Vendor scope**: Juniper first, extensible VendorParser ABC for others
- **Dependencies**: Works alongside existing jmcp — complementary, not replacing

---
*Last updated: 2026-03-21 after v1.2 milestone complete (Phase 14)*
