# Requirements: nautobot-mcp-cli

**Defined:** 2026-03-20
**Core Value:** AI agents can read and write Nautobot data through standardized MCP tools — one call = one complete answer

## v1.1 Requirements

Requirements for v1.1 release. Each maps to roadmap phases.
Continues numbering from v1.0 (which had 53 requirements).

### Device IP Query (DEVIP)

- [x] **DEVIP-01**: Agent can retrieve all IP addresses assigned to a device's interfaces in one MCP call, returning {interface → [IPs]}
- [x] **DEVIP-02**: CLI command `nautobot-mcp ipam addresses list --device DEVICE` returns IPs filtered by device
- [x] **DEVIP-03**: MCP tool `nautobot_get_device_ips` returns structured JSON: [{interface, address, status}]

### Cross-Entity Filters (FILT)

- [x] **FILT-01**: `nautobot_list_ip_addresses` MCP tool accepts optional `device_name` parameter to filter by device
- [x] **FILT-02**: `nautobot_list_vlans` MCP tool accepts optional `device_name` parameter to filter by device
- [ ] **FILT-03**: `nautobot_list_interfaces` MCP tool accepts optional `include_ips` boolean that embeds IP addresses inline per interface

### Device Summary (SUMM)

- [ ] **SUMM-01**: Agent can get complete device overview (info + interfaces + IPs + VLANs) in one MCP call via `nautobot_device_summary`
- [ ] **SUMM-02**: CLI command `nautobot-mcp devices summary DEVICE` outputs aggregated device info
- [ ] **SUMM-03**: Device summary includes interface count, IP count, VLAN count, and link state statistics

### File-Free Drift Comparison (DRIFT)

- [ ] **DRIFT-01**: Agent can pass structured interface/IP data (dict) directly to drift comparison MCP tool — no config.json file required
- [ ] **DRIFT-02**: MCP tool `nautobot_compare_device_ips` accepts {interface → [IPs]} map and returns {missing, extra, unlinked}
- [ ] **DRIFT-03**: Drift tool works with data from any source (jmcp, manual input, parsed text) — not tied to JunOS parser
- [ ] **DRIFT-04**: CLI command `nautobot-mcp verify quick-drift DEVICE` accepts --interface/--ip flags for ad-hoc comparison

### Enriched Interface Data (ENRICH)

- [ ] **ENRICH-01**: `nautobot_list_interfaces` with `include_ips=True` returns each interface with its assigned IPs embedded
- [ ] **ENRICH-02**: Interface IP enrichment uses efficient batch query (not N+1 per interface)

## v1.2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Multi-Vendor

- **VENDOR-01**: Cisco IOS/IOS-XE config parser
- **VENDOR-02**: Arista EOS config parser
- **VENDOR-03**: Bulk device onboarding (batch config files)

### Remediation

- **REMED-01**: Config remediation suggestions based on drift reports
- **REMED-02**: Enhanced "Audit Device" agent skill — comprehensive health check

## Out of Scope

| Feature | Reason |
|---------|--------|
| jmcp large output fix | jmcp is a separate project — only document workarounds |
| Direct device communication | Handled by vendor MCP servers (jmcp for Juniper) |
| Nautobot plugin development | This tool consumes existing Nautobot REST APIs |
| Automated remediation without confirmation | v1.x reports drift only, requires human approval |
| GraphQL queries | REST API via pynautobot is well-established and sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEVIP-01 | Phase 5 | Complete |
| DEVIP-02 | Phase 5 | Complete |
| DEVIP-03 | Phase 5 | Complete |
| FILT-01 | Phase 5 | Complete |
| FILT-02 | Phase 5 | Complete |
| FILT-03 | Phase 6 | Pending |
| SUMM-01 | Phase 6 | Pending |
| SUMM-02 | Phase 6 | Pending |
| SUMM-03 | Phase 6 | Pending |
| DRIFT-01 | Phase 7 | Pending |
| DRIFT-02 | Phase 7 | Pending |
| DRIFT-03 | Phase 7 | Pending |
| DRIFT-04 | Phase 7 | Pending |
| ENRICH-01 | Phase 6 | Pending |
| ENRICH-02 | Phase 6 | Pending |

**Coverage:**
- v1.1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-20*
*Last updated: 2026-03-20 after v1.1 milestone start*
