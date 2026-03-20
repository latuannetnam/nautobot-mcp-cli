# Changelog

All notable changes to **nautobot-mcp-cli** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [v1.1] — 2026-03-20

### Added

**Device Queries**
- `nautobot_get_device_ips` — returns all IP addresses on all interfaces for a device in one call,
  using M2M traversal via `ip_address_to_interface` (more reliable than direct device filter)
- `nautobot_get_device_summary` — single-call device health check: interface count, IP count, VLAN
  count, enabled/disabled link-state statistics
- `nautobot_list_interfaces(include_ips=True)` — embeds IPs inline per interface using a batch M2M
  query (≤2 API calls total, not N+1 per interface)

**Cross-Entity Filters**
- `nautobot_list_ip_addresses(device=...)` — filter IPs to a specific device
- `nautobot_list_vlans(device=...)` — filter VLANs to a specific device's interfaces

**File-Free Drift Comparison**
- `nautobot_compare_device` — compare structured interface data against Nautobot records; no config
  file required; input auto-detected as flat dict or DeviceIPEntry list (chainable from
  `nautobot_get_device_ips`)
- Pydantic models: `InterfaceDrift`, `DriftSummary`, `QuickDriftReport`
- Lenient IP validation: accepts IPs without prefix length with a warning (real-world jmcp output)

**CLI Commands**
- `nautobot-mcp devices summary DEVICE` — compact device overview; `--detail` for full breakdown
- `nautobot-mcp ipam ips list --device DEVICE` — device-scoped IP query
- `nautobot-mcp ipam vlans list --device DEVICE` — device-scoped VLAN query
- `nautobot-mcp interfaces list --include-ips` — interfaces with IPs inline
- `nautobot-mcp verify quick-drift DEVICE` — file-free drift check with multiple input modes:
  - `--interface`/`--ip`/`--vlan` flags for single-interface quick checks
  - `--data` JSON string for bulk inline input
  - `--file` JSON file for scripted flows
  - stdin pipe for agent-driven workflows
  - `--json` for machine-readable output
  - Colored table output: ✅ OK / ❌ DRIFT per interface with missing/extra detail

**Agent Skills**
- `verify-compliance` skill guide updated with "File-Free Drift Check" section:
  jmcp chaining workflow and `nautobot_get_device_ips` → `nautobot_compare_device` chain

### Stats

- MCP tools: 44 → **46**
- Unit tests: 76 → **105**
- Files changed since v1.0: 75 (+8225 / -156)

---

## [v1.0] — 2026-03-18

Initial release — full Nautobot automation via MCP and CLI.

### Added

**Core Infrastructure**
- `NautobotClient` — pynautobot wrapper with profile support, SSL control, and pagination
- Multi-source config loading: YAML file → env vars → CLI flags (layered precedence)
- Named profiles (`default`, `staging`, etc.) in `.nautobot-mcp.yaml`
- FastMCP 3.0 MCP server with automatic tool registration from type hints

**MCP Tools (44 total)**
- **Devices** — list, get, create, update, delete
- **Interfaces** — list, get, create, update, assign IP
- **IPAM** — prefixes, IP addresses, VLANs (list + create)
- **Organization** — tenants, locations (list, get, create, update)
- **Circuits** — list, get, create, update
- **Golden Config** — intended config, backup config, compliance features/rules/results, quick diff
- **Onboarding** — parse config, onboard to Nautobot (dry-run safe)
- **Verification** — compliance check (Golden Config), DiffSync data model drift report

**CLI**
- Typer-based CLI mirroring all MCP tools
- `--json` global flag for machine-readable output
- `--profile` / `--url` / `--token` / `--no-verify` global flags

**Config Parsing & Onboarding**
- JunOS JSON config parser (`juniper_junos`) via `show configuration | display json`
- Extensible `VendorParser` ABC + `ParserRegistry` for future vendors
- Onboarding engine: parse → dry-run preview → commit (Device → Interfaces → IPs → VLANs)

**Verification**
- Golden Config compliance check via quick diff
- DiffSync-based data model verification: per-object diff with `missing`, `extra`, `changed` statuses
  for interfaces, IP addresses, and VLANs

**Agent Skills**
- `onboard-router-config` — step-by-step skill guide for jmcp → parse → onboard workflow
- `verify-compliance` — skill guide for compliance checks and data model drift detection

### Stats

- MCP tools: **44**
- Unit tests: **76**
- Lines of code: ~3,400 Python

---

## [Unreleased]

> Changes targeting the next milestone (v1.2) will appear here.

Candidates:
- Multi-vendor config parsers (Cisco IOS/IOS-XE, Arista EOS)
- Bulk device onboarding (batch config files)
- Config remediation suggestions based on drift reports
- Enhanced "Audit Device" agent skill

---

*For full per-phase details see [`.planning/milestones/`](.planning/milestones/).*
