# nautobot-mcp-cli

## What This Is

An MCP server, CLI tool, and agent skills library that enables AI agents to interact with Nautobot for network automation. It provides 46 structured tools for managing network infrastructure data in Nautobot — devices, interfaces, IP addresses, VLANs, circuits, Golden Config — and integrates with vendor-specific MCP servers (Juniper jmcp) to bridge the gap between live network state and Nautobot as the source of truth.

## Core Value

AI agents can read and write Nautobot data through standardized MCP tools, enabling automated network configuration management, device-scoped queries, and file-free drift comparison against Nautobot's source of truth.

## Current State: v1.1 Shipped ✅

**Shipped 2026-03-20** — v1.1 Agent-Native MCP Tools

Key additions in v1.1:
- `nautobot_get_device_ips` — all IPs for a device in one call (M2M traversal)
- `nautobot_get_device_summary` — device health at a glance (interface/IP/VLAN counts)
- `nautobot_list_interfaces(include_ips=True)` — inline IP enrichment (batch query)
- `nautobot_compare_device` — file-free drift: accepts dict or DeviceIPEntry list, no config file
- `verify quick-drift` CLI — human-friendly colored output with per-interface detail

**Stats at v1.1:**
- 46 MCP tools | 105 unit tests passing | ~11k LOC Python
- Tech stack: FastMCP, Typer, pynautobot, DiffSync, Pydantic v2

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

## Next Milestone: v1.2 (TBD)

Run `/gsd-new-milestone` to define requirements and roadmap.

Candidate features:
- Multi-vendor config parsers (Cisco IOS, Arista EOS)
- Bulk device onboarding (batch config files)
- Config remediation suggestions based on drift reports
- Enhanced "Audit Device" agent skill — comprehensive health check

## Out of Scope

- Direct device communication — handled by vendor MCP servers (jmcp for Juniper)
- Nautobot server deployment/management — server already running at nautobot.netnam.vn
- Nautobot plugin development — this tool consumes existing Nautobot APIs
- Automated remediation without confirmation — reports drift only, requires human approval

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

## Constraints

- **Protocol**: MCP (Model Context Protocol) for AI agent interaction
- **Language**: Python (pyproject.toml with uv)
- **Nautobot API**: REST API v2 at https://nautobot.netnam.vn/
- **Vendor scope**: Juniper first, extensible VendorParser ABC for others
- **Dependencies**: Works alongside existing jmcp — complementary, not replacing

---
*Last updated: 2026-03-20 after v1.1 milestone*
