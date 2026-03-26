# Changelog

All notable changes to **nautobot-mcp-cli** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

> Changes targeting the next milestone will appear here.

Candidates:
- Multi-vendor config parsers (Cisco IOS/IOS-XE, Arista EOS)
- Bulk device onboarding (batch config files)
- Config remediation suggestions based on drift reports
- Extended drift coverage (interfaces, firewalls)

---

## [v1.4] — 2026-03-26

### Partial Failure Resilience

Composite workflows now gracefully degrade instead of all-or-nothing failure. Sub-operation errors are captured as structured warnings in the response envelope while valid results are still returned.

- `WarningCollector` dataclass (`nautobot_mcp/warnings.py`) — thread-safe warning accumulation with `add(operation, error)` and `summary(total_ops)` methods
- Three-tier response status: `ok` (full success), `partial` (some results + warnings), `error` (complete failure)
- All 4 composite functions (`bgp_summary`, `routing_table`, `firewall_summary`, `interface_detail`) return `(result, warnings)` tuples
- Independent co-primaries in `firewall_summary`: filter and policer fetches are independent — one failure does not block the other

### Workflow Contract Validation

Import-time self-validation catches registry/signature drift before runtime.

- `_validate_registry()` runs at module load — raises `NautobotValidationError` if any registry entry's `param_map` keys don't match the actual function signature
- Caught and fixed 3 pre-existing bugs: `onboard_config` param key, `compare_device` required list, `verify_data_model` missing transforms
- Registry param_map keys must be actual function parameter names (not agent-facing aliases)

### Error Diagnostics & Actionable Hints

All API errors now include context-specific guidance rather than generic messages.

- DRF 400 responses parsed for field-level validation errors — `NautobotValidationError.errors` populated from response body
- `ERROR_HINTS` dict with 10 endpoint-specific actionable hints (longest-match lookup)
- `STATUS_CODE_HINTS` for 429/500/502/503/504/422 with rate-limit guidance, retry windows, upstream error context
- `NautobotAPIError` default hint is status-code-derived — no more generic placeholder messages
- Composite workflow exceptions captured as structured warning entries in the error envelope (`ERR-03`)

### Catalog Accuracy

CMS endpoint filters corrected and UUID path segments supported.

- Per-endpoint `CMS_ENDPOINT_FILTERS` dict (43 entries) replaces domain-level `CMS_DOMAIN_FILTERS` — each CMS endpoint now advertises the correct primary FK filter(s)
- UUID path segment detection: agents can pass `/api/dcim/devices/<uuid>/` directly to `call_nautobot()` without manually decomposing

### Response Ergonomics

Composite workflow responses now include sizing metadata and summary modes for token-efficient agent consumption.

- `response_size_bytes` in all composite workflow envelopes — `len(json.dumps(data))` measured at the workflow engine level
- `detail=False` summary mode for `interface_detail`: strips `families[]` and `vrrp_groups[]` arrays, keeps `family_count` and `vrrp_group_count` integers
- `limit=N` parameter on all 4 composites: independently caps arrays within each composite (`groups[]`, `neighbors[]` per group, `routes[]`, `filters[]`, `policers[]`, `terms[]`, `actions[]`, `units[]`, `families[]`, `arp_entries[]`)
- Smoke test suite with 10 checks covering all 3 ergonomics requirements

### Stats

- MCP tools: 3 (unchanged)
- Unit tests: 397 → **476**
- Phases: 19-22 (Partial Failure Resilience, Catalog Accuracy, Workflow Contracts & Error Diagnostics, Response Ergonomics)

---

## [v1.3] — 2026-03-25

### API Bridge Architecture

Replaced the 164-tool MCP server with a **3-tool API Bridge** — eliminating per-resource tool sprawl and reducing agent token overhead by ~90%.

| Tool | Purpose |
|---|---|
| `nautobot_api_catalog` | Discover all available endpoints and workflows, optionally filtered by domain (`dcim`, `ipam`, `cms`, `workflows`, …) |
| `nautobot_call_nautobot` | Universal REST dispatcher — GET, POST, PATCH, DELETE against any endpoint; routes automatically to pynautobot core or CMS plugin |
| `nautobot_run_workflow` | Execute composite server-side workflows by ID; returns a standard response envelope |

### Catalog Engine

- `get_catalog(domain=None)` assembles a unified endpoint + workflow catalog from three sources: static core endpoints, dynamic CMS discovery, and workflow stubs
- Domain filtering: `dcim`, `ipam`, `circuits`, `tenancy`, `cms`, `workflows`
- CMS endpoints auto-discovered from `CMS_ENDPOINTS` — adding a new CMS model automatically appears in the catalog without code changes
- Catalog response designed to stay under 1,500 tokens

### REST Bridge

- Routes `/api/*` endpoints to pynautobot core accessors
- Routes `cms:*` endpoints to CMS plugin helpers (auto-resolves device name → UUID)
- Fuzzy-match error hints via `difflib` for invalid endpoint names
- Hard cap at 200 results per GET; default 50; response includes `truncated` + `total_available` metadata when capped
- Validates endpoints against catalog; raises `NautobotValidationError` with suggestion before hitting the server

### Workflow Registry

10 composite workflows registered in `nautobot_mcp/workflows.py`:

| Workflow ID | Description |
|---|---|
| `bgp_summary` | All BGP groups + neighbor counts for a device |
| `routing_table` | Static routes with inlined next-hops |
| `firewall_summary` | Firewall filters with term counts |
| `interface_detail` | Interface units with families, filters, VRRP, ARP |
| `onboard_config` | Parse + onboard config to Nautobot (dry-run safe) |
| `compare_device` | File-free drift — live interfaces vs Nautobot |
| `verify_data_model` | DiffSync data model drift report |
| `verify_compliance` | Golden Config compliance check |
| `compare_bgp` | Live BGP neighbors vs CMS records |
| `compare_routes` | Live static routes vs CMS records |

All workflows return a standard envelope: `{workflow, device, status, data, error, timestamp}`.

### Agent Skills

All 3 agent skill guides rewritten for the 3-tool API:

- `cms-device-audit` — consolidated 8-step audit into 6 steps; multi-step collect+compare patterns replaced with single `nautobot_run_workflow` calls; added Step 0 discovery
- `onboard-router-config` — replaces `nautobot_onboard_config` → `nautobot_run_workflow("onboard_config", ...)` with correct `config_data` param
- `verify-compliance` — replaces all legacy tool calls; adds device IP lookup via `nautobot_call_nautobot`

### UAT Test Suite

- `tests/test_uat.py` — 11 tests in 4 classes with `@pytest.mark.live`; excluded from normal `pytest` runs (requires `NAUTOBOT_UAT_URL` + `NAUTOBOT_TOKEN`)
- `scripts/uat_smoke_test.py` — standalone 9-check script with ✓/✗ output; exits 0 on all-pass, 1 on any failure
- `pyproject.toml` — `live` marker registered; `addopts = "-m 'not live'"` keeps UAT out of CI

### Stats

- MCP tools: 164 → **3**
- Unit tests: 293 → **397**
- Phases: 15-18 (Catalog Engine, REST Bridge, Workflow Registry, Skills & UAT)

---

## [v1.2] — 2026-03-21

### Juniper CMS Model CRUD Tools

Full CRUD MCP tools for all Juniper-specific models in the `netnam-cms-core` Nautobot plugin — 5 model domains, 40+ Pydantic models, and a new `nautobot_mcp/cms/` subpackage.

**Routing** (BGP groups, BGP neighbors, static routes with inlined next-hops, routing instances)
- `nautobot_cms_list_static_routes` / `nautobot_cms_get_static_route` / `nautobot_cms_create_static_route` / `nautobot_cms_delete_static_route`
- `nautobot_cms_list_bgp_groups` / `nautobot_cms_get_bgp_group` / `nautobot_cms_create_bgp_group` / `nautobot_cms_delete_bgp_group`
- `nautobot_cms_list_bgp_neighbors` / `nautobot_cms_get_bgp_neighbor` / `nautobot_cms_create_bgp_neighbor` / `nautobot_cms_delete_bgp_neighbor`
- `nautobot_cms_list_bgp_address_families` / `nautobot_cms_list_bgp_policy_associations` / `nautobot_cms_list_bgp_received_routes`
- `nautobot_cms_list_routing_instances` / `nautobot_cms_list_static_route_nexthops`

**Interfaces** (interface units, address families, filter/policer associations, VRRP)
- `nautobot_cms_list_interface_units` / `nautobot_cms_get_interface_unit` / `nautobot_cms_create_interface_unit` / `nautobot_cms_delete_interface_unit`
- `nautobot_cms_list_interface_families` / `nautobot_cms_get_interface_family`
- `nautobot_cms_list_ff_associations` / `nautobot_cms_create_ff_association` / `nautobot_cms_delete_ff_association`
- `nautobot_cms_list_fp_associations` / `nautobot_cms_create_fp_association` / `nautobot_cms_delete_fp_association`
- `nautobot_cms_list_vrrp_groups` / `nautobot_cms_get_vrrp_group` / `nautobot_cms_create_vrrp_group` / `nautobot_cms_delete_vrrp_group`

**Firewalls & Policies** (firewall filters, terms, match conditions, policers, policy statements)
- `nautobot_cms_list_firewall_filters` / `nautobot_cms_get_firewall_filter` / `nautobot_cms_create_firewall_filter` / `nautobot_cms_delete_firewall_filter`
- `nautobot_cms_list_firewall_terms` / `nautobot_cms_create_firewall_term` / `nautobot_cms_delete_firewall_term`
- `nautobot_cms_list_firewall_policers` / `nautobot_cms_create_firewall_policer` / `nautobot_cms_delete_firewall_policer`
- `nautobot_cms_list_policy_statements` / `nautobot_cms_create_policy_statement` / `nautobot_cms_delete_policy_statement`
- Plus policy terms, match conditions, actions, prefix lists, communities, AS paths

**ARP**
- `nautobot_cms_list_arp_entries` / `nautobot_cms_get_arp_entry` / `nautobot_cms_create_arp_entry` / `nautobot_cms_delete_arp_entry`

### Composite Summary Tools

Single-call summaries aggregating across related models:
- `nautobot_cms_get_device_bgp_summary` — all BGP groups + neighbor counts + session state in one call; `detail=True` expands per-group neighbors with address families and policy associations
- `nautobot_cms_get_device_routing_table` — all static routes with inlined next-hops and routing instances
- `nautobot_cms_get_interface_detail` — full interface unit view: families, filter/policer associations, VRRP groups, ARP entries
- `nautobot_cms_get_device_firewall_summary` — all firewall filters with term counts and policer associations

### CMS Drift Verification

DiffSync-based live-vs-CMS comparison — no config files required:
- `nautobot_cms_compare_bgp_neighbors` — compare BGP neighbors collected from a live device (via jmcp) against Nautobot CMS records; returns `CMSDriftReport` with `missing`, `extra`, and `changed` sections
- `nautobot_cms_compare_static_routes` — same for static routes; nexthop comparison is order-independent

### CLI Commands

CMS model operations under `nautobot-mcp cms`:
- `nautobot-mcp cms routing <subcommand>` — full CRUD + `bgp-summary` + `routing-table`
- `nautobot-mcp cms interfaces <subcommand>` — full CRUD + `detail` + ARP (`list-arp-entries`, `get-arp-entry`)
- `nautobot-mcp cms firewalls <subcommand>` — full CRUD + `firewall-summary`
- `nautobot-mcp cms policies <subcommand>` — full CRUD
- `nautobot-mcp cms drift bgp --device DEVICE --from-file live.json` — BGP drift check
- `nautobot-mcp cms drift routes --device DEVICE --from-file live.json` — route drift check

### Agent Skills

- `cms-device-audit` skill — 8-step CMS-aware device audit workflow: confirm device in Nautobot → collect live BGP + routes via jmcp → compare against CMS records → review interface detail + firewall summary → compile audit report with action guidance

### Stats

- MCP tools: 46 → **164**
- Unit tests: 105 → **293**
- Phases: 7 (CMS foundation, routing, interfaces, firewalls/policies, ARP+composites, drift engine, CLI+skills)

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

*For full per-phase details see [`.planning/milestones/`](.planning/milestones/).*
