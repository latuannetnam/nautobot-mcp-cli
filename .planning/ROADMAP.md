# Roadmap: nautobot-mcp-cli

**Created:** 2026-03-17
**Granularity:** Coarse (3-5 phases)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-18)
- 🔵 **v1.1 Agent-Native MCP Tools** — Phases 5-7 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-03-18</summary>

- [x] Phase 1: Core Foundation & Nautobot Client (4/4 plans) — completed 2026-03-17
- [x] Phase 2: MCP Server & CLI (3/3 plans) — completed 2026-03-17
- [x] Phase 3: Golden Config & Config Parsing (3/3 plans) — completed 2026-03-17
- [x] Phase 4: Onboarding, Verification & Agent Skills (3/3 plans) — completed 2026-03-18

</details>

### v1.1 Agent-Native MCP Tools

- [x] Phase 5: Device-Scoped IP Queries & Cross-Entity Filters (2/2 plans) — completed 2026-03-20
- [ ] Phase 6: Device Summary & Enriched Interface Data
- [ ] Phase 7: File-Free Drift Comparison

---

## v1.1 Phase Details

### Phase 5: Device-Scoped IP Queries & Cross-Entity Filters

**Goal:** Add the most critical missing tools — let agents query IPs by device and filter addresses/VLANs by device in one call.

**Requirements:** DEVIP-01, DEVIP-02, DEVIP-03, FILT-01, FILT-02

**Success Criteria:**
1. `nautobot_get_device_ips("HQV-PE-TestFake")` returns all IPs mapped to interfaces in one call
2. `nautobot-mcp ipam addresses list --device X` CLI command works
3. `nautobot_list_ip_addresses(device_name="X")` MCP tool accepts and filters by device
4. `nautobot_list_vlans(device_name="X")` MCP tool accepts and filters by device
5. All existing unit tests continue to pass

### Phase 6: Device Summary & Enriched Interface Data

**Goal:** Add composite tools that answer "tell me everything about this device" in one call, and enrich interface listings with inline IPs.

**Requirements:** SUMM-01, SUMM-02, SUMM-03, FILT-03, ENRICH-01, ENRICH-02

**Success Criteria:**
1. `nautobot_device_summary("X")` returns device info + interfaces + IPs + VLANs + counts
2. `nautobot-mcp devices summary X` CLI command displays aggregated overview
3. `nautobot_list_interfaces(device_name="X", include_ips=True)` embeds IPs in response
4. IP enrichment uses batch query (≤2 API calls) not N+1 per interface
5. Summary includes link state statistics (up/down counts)

### Phase 7: File-Free Drift Comparison

**Goal:** Enable drift detection using structured data (from any source) instead of requiring a config.json file, so agents can chain jmcp output → drift check without filesystem.

**Requirements:** DRIFT-01, DRIFT-02, DRIFT-03, DRIFT-04

**Success Criteria:**
1. `nautobot_compare_device_ips(device_name, interfaces_data={...})` accepts dict and returns structured diff
2. Drift tool returns {missing_from_nautobot, extra_in_nautobot, unlinked_ips}
3. Works with arbitrary input data — not tied to JunOS parser
4. `nautobot-mcp verify quick-drift X --interface ae0.0 --ip 10.1.1.1/30` CLI command works
5. Agent can chain: jmcp `show interfaces terse` → parse → MCP drift check — zero Python scripting

## Phase Summary

| # | Phase | Requirements | Status |
|---|-------|-------------|--------|
| 5 | Device-Scoped IP Queries & Cross-Entity Filters | DEVIP-01..03, FILT-01..02 | ✅ Completed |
| 6 | Device Summary & Enriched Interface Data | SUMM-01..03, FILT-03, ENRICH-01..02 | ⬜ Not started |
| 7 | File-Free Drift Comparison | DRIFT-01..04 | ⬜ Not started |

**Total:** 3 phases | 15 requirements | All v1.1 requirements mapped ✓

> Full v1.0 phase details: [.planning/milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

---
*Roadmap created: 2026-03-17*
*Last updated: 2026-03-20 after v1.1 milestone start*
