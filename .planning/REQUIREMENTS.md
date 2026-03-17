# Requirements: nautobot-mcp-cli

**Defined:** 2026-03-17
**Core Value:** AI agents can read and write Nautobot data through standardized MCP tools, enabling automated network configuration management and compliance verification.

## v1 Requirements

### Core Infrastructure

- [ ] **CORE-01**: Tool can connect to a Nautobot instance using API token and base URL
- [ ] **CORE-02**: Tool validates Nautobot connectivity and API version on startup
- [ ] **CORE-03**: Tool returns structured error responses with actionable guidance for AI agents
- [ ] **CORE-04**: Tool supports configuration via environment variables and config file

### Devices

- [ ] **DEV-01**: User can list all devices with filtering by location, tenant, role, platform
- [ ] **DEV-02**: User can get detailed information for a specific device by name or ID
- [ ] **DEV-03**: User can create a new device in Nautobot with required fields
- [ ] **DEV-04**: User can update an existing device's attributes
- [ ] **DEV-05**: User can delete a device from Nautobot

### Interfaces

- [ ] **INTF-01**: User can list all interfaces for a specific device
- [ ] **INTF-02**: User can get detailed information for a specific interface
- [ ] **INTF-03**: User can create a new interface on a device
- [ ] **INTF-04**: User can update an existing interface's attributes (description, enabled, type)
- [ ] **INTF-05**: User can assign an IP address to an interface

### IPAM

- [ ] **IPAM-01**: User can list prefixes with filtering by VRF, location, tenant
- [ ] **IPAM-02**: User can create a new prefix in Nautobot
- [ ] **IPAM-03**: User can list IP addresses with filtering by device, interface, prefix
- [ ] **IPAM-04**: User can create and assign an IP address
- [ ] **IPAM-05**: User can list VLANs with filtering by location, tenant, group
- [ ] **IPAM-06**: User can create a new VLAN

### Organization

- [ ] **ORG-01**: User can list and get tenants
- [ ] **ORG-02**: User can create and update tenants
- [ ] **ORG-03**: User can list and get locations
- [ ] **ORG-04**: User can create and update locations

### Circuits

- [ ] **CIR-01**: User can list circuits with filtering by provider, type, location
- [ ] **CIR-02**: User can get detailed circuit information including terminations
- [ ] **CIR-03**: User can create and update circuits

### Golden Config

- [ ] **GC-01**: User can retrieve the intended configuration for a device
- [ ] **GC-02**: User can retrieve the backup (actual) configuration for a device
- [ ] **GC-03**: User can list compliance rules and features
- [ ] **GC-04**: User can create and update compliance rules
- [ ] **GC-05**: User can trigger a compliance check for a device and get results
- [ ] **GC-06**: User can view compliance status summary (pass/fail per feature)

### MCP Server

- [ ] **MCP-01**: MCP server starts and exposes all Nautobot tools via FastMCP
- [ ] **MCP-02**: AI agents can discover available tools through MCP protocol
- [ ] **MCP-03**: Tools return structured data (JSON-serializable) suitable for agent consumption
- [ ] **MCP-04**: Server supports stdio transport for local agent integration

### CLI

- [ ] **CLI-01**: CLI provides commands for all core Nautobot operations (devices, interfaces, IPAM, org, circuits)
- [ ] **CLI-02**: CLI supports both human-readable table output and JSON output mode
- [ ] **CLI-03**: CLI provides shell completion for commands and options
- [ ] **CLI-04**: CLI reads connection settings from environment variables or config file

### Config Parsing

- [ ] **PARSE-01**: Tool can parse JunOS hierarchical config into structured data (interfaces, IPs, VLANs)
- [ ] **PARSE-02**: Parser extracts interface names, descriptions, IP addresses, and status
- [ ] **PARSE-03**: Parser handles common JunOS platform variants (MX, EX, SRX)
- [ ] **PARSE-04**: Parser architecture supports adding new vendor parsers

### Config Onboarding

- [ ] **ONBOARD-01**: User can onboard parsed router config into Nautobot (create/update devices, interfaces, IPs)
- [ ] **ONBOARD-02**: Onboarding shows a dry-run diff before committing changes
- [ ] **ONBOARD-03**: Onboarding is idempotent — running twice produces no duplicates
- [ ] **ONBOARD-04**: Onboarding resolves Nautobot object references (device type, location, manufacturer)

### Compliance Verification

- [ ] **VERIFY-01**: User can compare live router config (from jmcp) against Nautobot Golden Config intended config
- [ ] **VERIFY-02**: User can compare live router interfaces/IPs against Nautobot data model records
- [ ] **VERIFY-03**: Comparison produces a structured drift report (missing, extra, changed items)
- [ ] **VERIFY-04**: Drift report is suitable for both human reading and agent processing

### Agent Skills

- [ ] **SKILL-01**: "Onboard Router Config" skill chains jmcp config pull → parse → Nautobot push
- [ ] **SKILL-02**: "Verify Compliance" skill chains jmcp config pull → Golden Config comparison
- [ ] **SKILL-03**: Skills provide step-by-step progress updates to the agent

## v2 Requirements

### Advanced Features

- **ADV-01**: Multi-vendor config parsers (Cisco IOS, IOS-XE, Arista EOS)
- **ADV-02**: Bulk operations (onboard multiple devices in batch)
- **ADV-03**: Webhook/event integration for real-time Nautobot change notifications
- **ADV-04**: Config remediation suggestions based on drift reports

### Enhanced Skills

- **ESKILL-01**: "Audit Device" skill — comprehensive device health check across Nautobot + live state
- **ESKILL-02**: "Migrate Config" skill — move device config between locations/tenants
- **ESKILL-03**: Interactive skills with agent-user confirmation loops

## Out of Scope

| Feature | Reason |
|---------|--------|
| Direct device SSH/NETCONF | Handled by jmcp and other vendor MCP servers |
| Nautobot web UI replacement | Nautobot already has a full UI |
| Config generation/rendering | Golden Config plugin handles this |
| Multi-tenant Nautobot management | Beyond v1 scope |
| Automated remediation without confirmation | Safety risk — v1 reports drift only |
| Nautobot server deployment | Server already running at nautobot.netnam.vn |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | — | Pending |
| CORE-02 | — | Pending |
| CORE-03 | — | Pending |
| CORE-04 | — | Pending |
| DEV-01 | — | Pending |
| DEV-02 | — | Pending |
| DEV-03 | — | Pending |
| DEV-04 | — | Pending |
| DEV-05 | — | Pending |
| INTF-01 | — | Pending |
| INTF-02 | — | Pending |
| INTF-03 | — | Pending |
| INTF-04 | — | Pending |
| INTF-05 | — | Pending |
| IPAM-01 | — | Pending |
| IPAM-02 | — | Pending |
| IPAM-03 | — | Pending |
| IPAM-04 | — | Pending |
| IPAM-05 | — | Pending |
| IPAM-06 | — | Pending |
| ORG-01 | — | Pending |
| ORG-02 | — | Pending |
| ORG-03 | — | Pending |
| ORG-04 | — | Pending |
| CIR-01 | — | Pending |
| CIR-02 | — | Pending |
| CIR-03 | — | Pending |
| GC-01 | — | Pending |
| GC-02 | — | Pending |
| GC-03 | — | Pending |
| GC-04 | — | Pending |
| GC-05 | — | Pending |
| GC-06 | — | Pending |
| MCP-01 | — | Pending |
| MCP-02 | — | Pending |
| MCP-03 | — | Pending |
| MCP-04 | — | Pending |
| CLI-01 | — | Pending |
| CLI-02 | — | Pending |
| CLI-03 | — | Pending |
| CLI-04 | — | Pending |
| PARSE-01 | — | Pending |
| PARSE-02 | — | Pending |
| PARSE-03 | — | Pending |
| PARSE-04 | — | Pending |
| ONBOARD-01 | — | Pending |
| ONBOARD-02 | — | Pending |
| ONBOARD-03 | — | Pending |
| ONBOARD-04 | — | Pending |
| VERIFY-01 | — | Pending |
| VERIFY-02 | — | Pending |
| VERIFY-03 | — | Pending |
| VERIFY-04 | — | Pending |
| SKILL-01 | — | Pending |
| SKILL-02 | — | Pending |
| SKILL-03 | — | Pending |

**Coverage:**
- v1 requirements: 53 total
- Mapped to phases: 0
- Unmapped: 53 ⚠️

---
*Requirements defined: 2026-03-17*
*Last updated: 2026-03-17 after initial definition*
