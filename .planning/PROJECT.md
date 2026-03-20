# nautobot-mcp-cli

## What This Is

An MCP server, CLI tool, and agent skills library that enables AI agents to interact with Nautobot for network automation. It provides 44+ structured tools for managing network infrastructure data in Nautobot — devices, interfaces, IP addresses, VLANs, circuits, Golden Config — and integrates with vendor-specific MCP servers (Juniper jmcp) to bridge the gap between live network state and Nautobot as the source of truth.

## Core Value

AI agents can read and write Nautobot data through standardized MCP tools, enabling automated network configuration management and compliance verification against Nautobot's source of truth.

## Requirements

### Validated (v1.0)

- ✓ MCP server exposing 44+ Nautobot operations as named tools — v1.0
- ✓ CLI interface for human/script access to all operations — v1.0
- ✓ Nautobot REST API client with authentication and profile support — v1.0
- ✓ Device management (CRUD operations via Nautobot API) — v1.0
- ✓ Interface management (list, create, update interfaces in Nautobot) — v1.0
- ✓ IPAM operations (prefixes, IP addresses, VLANs) — v1.0
- ✓ Organization data (tenants, locations) — v1.0
- ✓ Circuit management — v1.0
- ✓ Golden Config plugin integration (intended/backup configs, compliance) — v1.0
- ✓ JunOS config parser with extensible vendor architecture — v1.0
- ✓ Config onboarding workflow (parse → dry-run → commit to Nautobot) — v1.0
- ✓ Config verification workflow (live vs Golden Config + data model drift) — v1.0
- ✓ Agent skills for multi-step workflows (onboard-router-config, verify-compliance) — v1.0

## Current Milestone: v1.1 Agent-Native MCP Tools

**Goal:** Make MCP tools fully usable by AI agents without manual Python scripting — one MCP call should answer one complete question.

**Target features:**
- Device-scoped IP query tool (get IPs by device in one call)
- Cross-entity filters on existing tools (--device filter for addresses/VLANs)
- Composite device summary tool (device + interfaces + IPs in one response)
- File-free drift comparison tool (accepts structured data, not file paths)
- Enriched interface listing with inline IP data
- jmcp large output handling fix

### Active (v1.2+)

- [ ] Multi-vendor config parsers (Cisco IOS, IOS-XE, Arista EOS)
- [ ] Bulk device onboarding (multiple devices from batch config files)
- [ ] Config remediation suggestions based on drift reports
- [ ] Enhanced "Audit Device" agent skill — comprehensive health check

### Out of Scope

- Direct device communication — handled by vendor MCP servers (jmcp for Juniper)
- Nautobot server deployment/management — server already running at nautobot.netnam.vn
- Nautobot plugin development — this tool consumes existing Nautobot APIs
- Automated remediation without confirmation — v1 reports drift only

## Context

- **Shipped v1.0 2026-03-18** with ~3,400 LOC Python
- Tech stack: FastMCP, Typer, pynautobot, DiffSync, pydantic v2
- Nautobot server running at https://nautobot.netnam.vn/
- Juniper MCP server (jmcp) configured and operational
- 76 unit tests, all passing
- Architecture: shared core library + thin MCP layer + thin CLI layer + agent skills

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------| 
| Shared core library with thin MCP/CLI layers | Avoid duplicating logic, single source of truth | ✓ Good — clean separation, easy to add tools |
| MCP + CLI + Skills as three interfaces | MCP for agents, CLI for humans, Skills for workflows | ✓ Good — all three patterns work independently |
| Juniper-first, extensible vendor architecture | jmcp exists; VendorParser ABC for future vendors | ✓ Good — ParserRegistry ready for Cisco/Arista |
| Nautobot REST API (not GraphQL) | Standard, well-documented, broad coverage | ✓ Good — pynautobot handles all operations |
| DiffSync for data model verification | Semantic diff vs string diff for structured comparison | ✓ Good — clean drift reports with missing/extra/changed |
| dry_run=True default for onboarding | Safety first — preview before committing | ✓ Good — avoids accidental bulk writes |

## Constraints

- **Protocol**: MCP (Model Context Protocol) for AI agent interaction
- **Language**: Python (pyproject.toml with uv)
- **Nautobot API**: REST API v2
- **Vendor scope**: Juniper first, extensible VendorParser ABC for others
- **Dependencies**: Works alongside existing jmcp — complementary, not replacing

---
*Last updated: 2026-03-18 after v1.0 milestone*
