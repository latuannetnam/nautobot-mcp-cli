# Roadmap: nautobot-mcp-cli

**Created:** 2026-03-17
**Granularity:** Coarse (3-5 phases)
**Total Requirements:** 53

## Phases

### Phase 1: Core Foundation & Nautobot Client

**Goal:** Establish the project structure, Nautobot API client, and core data model operations (Devices, Interfaces, IPAM, Org, Circuits). By the end, all CRUD operations work via shared core library.

**Requirements:**
- CORE-01, CORE-02, CORE-03, CORE-04
- DEV-01, DEV-02, DEV-03, DEV-04, DEV-05
- INTF-01, INTF-02, INTF-03, INTF-04, INTF-05
- IPAM-01, IPAM-02, IPAM-03, IPAM-04, IPAM-05, IPAM-06
- ORG-01, ORG-02, ORG-03, ORG-04
- CIR-01, CIR-02, CIR-03

**Success Criteria:**
1. `pynautobot` client connects to nautobot.netnam.vn and authenticates
2. All device CRUD operations work and return structured data
3. Interface, IPAM, Org, and Circuit operations work end-to-end
4. Structured error responses include action guidance
5. Unit tests cover core client operations

---

### Phase 2: MCP Server & CLI

**Goal:** Expose all core operations through FastMCP server and Typer CLI. AI agents can discover and call Nautobot tools. Humans can use CLI for the same operations.

**Requirements:**
- MCP-01, MCP-02, MCP-03, MCP-04
- CLI-01, CLI-02, CLI-03, CLI-04

**Success Criteria:**
1. FastMCP server starts and exposes all core tools via stdio transport
2. AI agent (Claude) can discover tools and query Nautobot devices
3. CLI `nautobot-mcp devices list` returns formatted table output
4. CLI `--json` flag outputs machine-readable JSON
5. CLI reads config from environment variables

---

### Phase 3: Golden Config & Config Parsing

**Goal:** Integrate with Nautobot Golden Config plugin and build JunOS config parser. This enables reading intended/backup configs and structured parsing of router configurations.

**Requirements:**
- GC-01, GC-02, GC-03, GC-04, GC-05, GC-06
- PARSE-01, PARSE-02, PARSE-03, PARSE-04

**Success Criteria:**
1. Tool retrieves intended and backup configs from Golden Config plugin
2. Compliance rules can be managed (CRUD) via API
3. Compliance check returns pass/fail status per device/feature
4. JunOS parser extracts interfaces, IPs, and VLANs from hierarchical config
5. Parser handles MX, EX, and SRX config variants

---

### Phase 4: Onboarding, Verification & Agent Skills

**Goal:** Build the high-value workflows: config onboarding (parse → push to Nautobot), compliance verification (live vs golden/data model), and agent skills that chain nautobot-mcp + jmcp tools.

**Requirements:**
- ONBOARD-01, ONBOARD-02, ONBOARD-03, ONBOARD-04
- VERIFY-01, VERIFY-02, VERIFY-03, VERIFY-04
- SKILL-01, SKILL-02, SKILL-03

**Success Criteria:**
1. Onboarding creates/updates Nautobot objects from parsed JunOS config
2. Dry-run mode shows planned changes without committing
3. Running onboarding twice produces no duplicates
4. Live router config compared against Golden Config produces drift report
5. Live router interfaces compared against Nautobot records identifies discrepancies
6. "Onboard Router Config" skill works end-to-end (jmcp pull → parse → Nautobot push)
7. "Verify Compliance" skill works end-to-end (jmcp pull → comparison → report)

---

## Phase Summary

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Core Foundation & Nautobot Client | Nautobot API client + all CRUD operations | 27 reqs | 5 |
| 2 | MCP Server & CLI | FastMCP server + Typer CLI interfaces | 8 reqs | 5 |
| 3 | Golden Config & Config Parsing | Golden Config plugin + JunOS parser | 10 reqs | 5 |
| 4 | Onboarding, Verification & Skills | Workflows + agent skills | 11 reqs | 7 |

**Total:** 4 phases | 53 requirements | All v1 requirements covered ✓

---
*Roadmap created: 2026-03-17*
*Last updated: 2026-03-17 after initial creation*
