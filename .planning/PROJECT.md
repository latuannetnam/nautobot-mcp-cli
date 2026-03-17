# nautobot-mcp-cli

## What This Is

An MCP server, CLI tool, and agent skills library that enables AI agents to interact with Nautobot for network automation. It provides structured tools for managing network infrastructure data in Nautobot — devices, interfaces, IP addresses, VLANs, circuits — and integrates with vendor-specific MCP servers (starting with Juniper jmcp) to bridge the gap between live network state and Nautobot as the source of truth.

## Core Value

AI agents can read and write Nautobot data through standardized MCP tools, enabling automated network configuration management and compliance verification against Nautobot's source of truth.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] MCP server exposing Nautobot core data models as tools
- [ ] CLI interface for human/script access to the same operations
- [ ] Agent skills for multi-step workflows (onboard config, verify compliance)
- [ ] Nautobot REST API client with authentication
- [ ] Device management (CRUD operations via Nautobot API)
- [ ] Interface management (list, create, update interfaces in Nautobot)
- [ ] IPAM operations (prefixes, IP addresses, VLANs)
- [ ] Organization data (tenants, locations)
- [ ] Circuit management
- [ ] Golden Config plugin integration (read intended configs, compare with live)
- [ ] Config onboarding workflow (pull from router via jmcp → parse → push to Nautobot)
- [ ] Config verification workflow (compare live router config vs Nautobot Golden Config)
- [ ] Data model verification (compare live router state vs Nautobot data models)
- [ ] Juniper config parser (structured data extraction from JunOS config)
- [ ] Extensible vendor architecture (add Cisco, Arista parsers later)

### Out of Scope

- Direct device communication — handled by vendor MCP servers (jmcp for Juniper)
- Nautobot server deployment/management — server already running at nautobot.netnam.vn
- Multi-vendor parsers beyond Juniper in v1 — extensible architecture, but Juniper first
- Nautobot plugin development — this tool consumes existing Nautobot APIs

## Context

- Nautobot server running at https://nautobot.netnam.vn/ with all devices already onboarded
- Juniper MCP server (jmcp) already configured and operational for direct router access
- Network includes Juniper and Cisco devices; Juniper is the primary target for v1
- The tool sits between AI agents and Nautobot, complementing jmcp which handles direct router interaction
- Python project using uv for dependency management (pyproject.toml already initialized)
- Target architecture: shared core library + thin MCP server layer + thin CLI layer + agent skills

## Constraints

- **Protocol**: MCP (Model Context Protocol) for AI agent interaction
- **Language**: Python (existing project setup with pyproject.toml)
- **Nautobot API**: REST API v2 (Nautobot's standard API)
- **Vendor scope**: Juniper first, extensible architecture for others
- **Dependencies**: Must work alongside existing jmcp server — complementary, not replacing

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Shared core library with thin MCP/CLI layers | Avoid duplicating logic, single source of truth for Nautobot operations | — Pending |
| MCP + CLI + Skills as three interfaces | MCP for agents, CLI for humans/scripts, Skills for complex multi-step workflows | — Pending |
| Juniper-first, extensible vendor architecture | jmcp already exists; build parser infrastructure that supports future vendors | — Pending |
| Nautobot REST API (not GraphQL) | Standard, well-documented, broad coverage of all data models | — Pending |

---
*Last updated: 2026-03-17 after initialization*
