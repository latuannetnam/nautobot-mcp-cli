# Features Research: Nautobot MCP CLI

## Table Stakes (Must Have)

### Nautobot Data Access
- **Device CRUD** — List, get, create, update, delete devices
- **Interface management** — List interfaces per device, create/update interface details
- **IPAM operations** — Manage prefixes, IP addresses, VLANs
- **Organization data** — Read/write tenants, locations
- **Circuit management** — CRUD operations for circuit data
- **Complexity:** Medium — straightforward REST API wrapping via pynautobot

### Authentication & Connection
- **API token auth** — Secure connection to Nautobot instance
- **Connection validation** — Verify Nautobot reachability and API version
- **Multi-instance support** — Configure different Nautobot servers
- **Complexity:** Low — pynautobot handles this natively

### Golden Config Integration
- **Read intended configs** — Retrieve golden/intended configurations
- **Compliance check** — Compare actual vs intended via API
- **Config backup retrieval** — Get stored device backups
- **Compliance rule management** — CRUD for compliance rules/features
- **Complexity:** Medium — Golden Config plugin has its own API endpoints

### MCP Server
- **Tool discovery** — AI agents discover available tools via MCP protocol
- **Structured responses** — Return data in agent-consumable format
- **Error handling** — Clear error messages for agent decision-making
- **Complexity:** Low-Medium — FastMCP handles protocol, need good tool design

### CLI Interface
- **Human-readable output** — Tables, formatted JSON, colored status
- **Scriptable output** — JSON/CSV output modes for pipelines
- **Shell completion** — Tab completion for commands
- **Complexity:** Low — Typer provides these out of the box

## Differentiators (Competitive Advantage)

### Config Onboarding Workflow
- **Parse JunOS config → Nautobot data model** — Structured extraction of interfaces, IPs, VLANs from router config
- **Diff before commit** — Show what will change in Nautobot before writing
- **Idempotent operations** — Run onboarding multiple times safely
- **Complexity:** High — requires robust config parsing

### Compliance Verification Workflows
- **Live vs Golden Config** — Compare live router config (via jmcp) against Nautobot Golden Config
- **Live vs Data Model** — Verify interfaces/IPs on router match Nautobot records
- **Drift report** — Structured report of differences
- **Complexity:** High — cross-MCP-server coordination, diff logic

### Agent Skills
- **Pre-built multi-step workflows** — "Onboard router", "Verify compliance", "Audit device"
- **Composable** — Skills chain MCP tools across nautobot-mcp and jmcp
- **Complexity:** Medium — workflow orchestration

## Anti-Features (Do NOT Build)

| Feature | Why Not |
|---------|---------|
| Direct device SSH/NETCONF | jmcp handles this; avoid duplication |
| Nautobot web UI | Nautobot already has a UI |
| Config generation/rendering | Golden Config plugin handles this |
| Multi-tenant Nautobot management | Out of scope for v1 |
| Automated remediation | Too risky without human confirmation for v1 |

## Dependencies Between Features

```
Authentication ──→ All Nautobot operations
Device CRUD ──→ Interface management ──→ IPAM operations
Golden Config read ──→ Compliance check
Config parsing (JunOS) ──→ Config onboarding workflow
Nautobot data access + jmcp ──→ Compliance verification workflows
```
