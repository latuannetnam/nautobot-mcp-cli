# Roadmap: nautobot-mcp-cli

**Created:** 2026-03-17
**Granularity:** Coarse (3-5 phases per milestone)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-18) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Agent-Native MCP Tools** — Phases 5-7 (shipped 2026-03-20) — [Archive](milestones/v1.1-ROADMAP.md)
- 🔵 **v1.2 Juniper CMS Model MCP Tools** — Phases 8-14

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-03-18</summary>

- [x] Phase 1: Core Foundation & Nautobot Client (4/4 plans)
- [x] Phase 2: MCP Server & CLI (3/3 plans)
- [x] Phase 3: Golden Config & Config Parsing (3/3 plans)
- [x] Phase 4: Onboarding, Verification & Agent Skills (3/3 plans)

</details>

<details>
<summary>✅ v1.1 Agent-Native MCP Tools (Phases 5-7) — SHIPPED 2026-03-20</summary>

- [x] Phase 5: Device-Scoped IP Queries & Cross-Entity Filters (2/2 plans)
- [x] Phase 6: Device Summary & Enriched Interface Data (2/2 plans)
- [x] Phase 7: File-Free Drift Comparison (2/2 plans)

</details>

### v1.2 — Juniper CMS Model MCP Tools

#### Phase 8: CMS Plugin Client Foundation

**Goal:** Build the core client layer for communicating with netnam-cms-core plugin API endpoints, establishing patterns for all subsequent CMS model tools.

**Requirements:** (Foundation — enables all subsequent requirements)

**Success criteria:**
1. CMS API client module can authenticate and query plugin endpoints at `/api/plugins/netnam-cms-core/`
2. Pydantic models for CMS API responses are defined and validated
3. Pagination and error handling work consistently with existing Nautobot client patterns
4. Unit tests verify client against mocked API responses

---

#### Phase 9: Routing Models — Static Routes & BGP

**Goal:** Add full CRUD MCP tools, CLI commands for Juniper routing models — static routes (with next-hops) and BGP (groups, neighbors, address families, policy associations, received routes, routing instances).

**Requirements:** RTG-01, RTG-02, RTG-03, RTG-04, RTG-05, RTG-06, RTG-07, RTG-08, RTG-09, RTG-10

**Success criteria:**
1. Agent can list static routes for a device filtered by destination/routing-instance
2. Agent can create a static route with simple and qualified next-hops in one call
3. Agent can list BGP neighbors for a device with peer AS, session state, and prefix counts
4. Agent can create BGP group → neighbor → address family hierarchy
5. Agent can list routing instances and filter routes by instance

---

#### Phase 10: Interface Models — Units, Families, VRRP

**Goal:** Add full CRUD MCP tools and CLI commands for Juniper interface-specific models — interface units (VLAN, QinQ), families (inet/inet6/mpls), filter/policer associations, and VRRP groups with tracking.

**Requirements:** INTF-01, INTF-02, INTF-03, INTF-04, INTF-05, INTF-06, INTF-07

**Success criteria:**
1. Agent can list interface units for a device with VLAN mode, encapsulation, and outer/inner VLANs
2. Agent can create an interface unit with QinQ VLAN configuration
3. Agent can list families for an interface and see associated filters and policers
4. Agent can list VRRP groups with virtual IP, priority, preempt, and tracking info
5. Agent can manage VRRP track routes and track interfaces

---

#### Phase 11: Firewall & Policy Models

**Goal:** Add full CRUD MCP tools and CLI commands for Juniper firewall filters (terms, match conditions, actions, policers) and policy statements (JPS terms, match conditions, actions, prefix lists, communities, AS paths).

**Requirements:** FW-01, FW-02, FW-03, FW-04, FW-05, FW-06, FW-07, POL-01, POL-02, POL-03, POL-04, POL-05, POL-06, POL-07, POL-08

**Success criteria:**
1. Agent can list firewall filters for a device with family and term counts
2. Agent can create a complete filter → term → match conditions → actions hierarchy
3. Agent can list policy statements with term counts and BGP association counts
4. Agent can create a policy with terms, match conditions (route-filter, community), and actions
5. Agent can manage prefix lists, communities, and AS paths for a device

---

#### Phase 12: ARP & Composite Summary Tools

**Goal:** Add ARP entry CRUD tools and build composite summary tools that aggregate data across multiple CMS models in a single call — device BGP summary, routing table, interface detail, firewall summary.

**Requirements:** ARP-01, ARP-02, COMP-01, COMP-02, COMP-03, COMP-04

**Success criteria:**
1. Agent can list/create/delete ARP entries for a device or interface
2. `nautobot_get_device_bgp_summary` returns groups → neighbors → session state → prefix counts in one call
3. `nautobot_get_device_routing_table` returns static routes with all next-hops and routing instances
4. `nautobot_get_interface_detail` returns unit → families → filters → policers → VRRP → ARP
5. `nautobot_get_device_firewall_summary` returns filters → term counts, policers, interface associations

---

#### ~~Phase 13: CMS Drift Verification~~ ✅ (2/2 plans)

**Goal:** Build drift comparison tools that compare live Juniper device state (via jmcp) against Nautobot CMS model records, using DiffSync for semantic diffing.

**Requirements:** DRIFT-01, DRIFT-02

**Success criteria:**
1. Agent can compare live BGP neighbors (from `show bgp summary`) against Nautobot CMS BGP records
2. Agent can compare live static routes (from `show route static`) against Nautobot CMS static route records
3. Drift report shows added/removed/changed entries with field-level detail
4. Works end-to-end with real jmcp device and Nautobot dev server

---

#### Phase 14: CLI Commands & Agent Skill Guides

**Goal:** Expose all CMS model tools via CLI commands and create agent skill guides for CMS-aware workflows.

**Requirements:** CLI-01, CLI-02, CLI-03, SKILL-01

**Success criteria:**
1. `nautobot-mcp cms routing list-static-routes --device X` and similar commands work for all domains
2. `nautobot-mcp cms summary bgp --device X` works for composite tools
3. `nautobot-mcp cms drift bgp --device X` works for drift verification
4. Agent skill guide documents the CMS-aware device audit workflow
5. All new CLI commands have `--help` documentation

---

## Phase → Requirement Mapping

| Phase | Requirements | Count |
|-------|-------------|-------|
| Phase 8 | (Foundation) | 0 |
| Phase 9 | RTG-01–10 | 10 |
| Phase 10 | INTF-01–07 | 7 |
| Phase 11 | FW-01–07, POL-01–08 | 15 |
| Phase 12 | ARP-01–02, COMP-01–04 | 6 |
| Phase 13 | DRIFT-01–02 | 2 |
| Phase 14 | CLI-01–03, SKILL-01 | 4 |
| **Total** | | **44** |

**Coverage:** All 42 v1.2 requirements mapped ✓ (Phase 8 adds 2 implicit foundation requirements)

---
*Roadmap created: 2026-03-17*
*Last updated: 2026-03-20 — v1.2 roadmap added (7 phases)*
