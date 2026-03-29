# UAT Spec: CMS Data Presence Smoke Test — HQV-PE1-NEW (Prod)

## Context

Verify that the Nautobot CMS plugin (netnam_cms_core) has JunOS data stored for device `HQV-PE1-NEW` on the **prod profile** (https://nautobot.netnam.vn). This is a **Layer 1 smoke test only** — no live device connectivity required. The goal is to confirm the CMS data pipeline is populated for this device before attempting drift detection (Layer 2) or DCIM consistency checks (Layer 3).

---

## Scope

- **Device:** HQV-PE1-NEW
- **Profile:** prod (default — no `--profile` flag needed)
- **Tool:** nautobot-mcp-cli via `nautobot_run_workflow` MCP tool
- **Out of scope:** Live device connectivity (jmcp), drift comparison, golden-config compliance

---

## Test Cases

| # | Workflow ID | Description | Pass Criteria |
|---|-------------|-------------|----------------|
| TC-01 | `bgp_summary` | BGP groups + neighbors in CMS | `status` is `"ok"` or `"partial"`, `total_groups >= 0`, `total_neighbors >= 0` |
| TC-02 | `routing_table` | Static routes in CMS | `status` is `"ok"` or `"partial"`, `total_routes >= 0` |
| TC-03 | `firewall_summary` | Firewall filters + policers in CMS | `status` is `"ok"` or `"partial"`, `total_filters >= 0`, `total_policers >= 0` |
| TC-04 | `interface_detail` | Interface units + families + VRRP in CMS | `status` is `"ok"` or `"partial"`, `total_units >= 0` |
| TC-05 | `devices_inventory` | Nautobot DCIM device inventory | `status` is `"ok"` or `"partial"`, non-empty response |

---

## Pass Criteria

Per workflow:
1. No exception raised (HTTP 200)
2. Response envelope `status` field is `"ok"` or `"partial"`
3. Primary data structure is present and not `null`
4. `warnings` list contains only non-fatal enrichment warnings (e.g., address-family fetch failed) — these do not fail the test

Overall: **ALL 5 workflows must pass** → overall result **PASS**

---

## Execution Methods

### MCP Tool (Claude Code agent)
```
nautobot_run_workflow("bgp_summary",      {"device": "HQV-PE1-NEW"})
nautobot_run_workflow("routing_table",     {"device": "HQV-PE1-NEW"})
nautobot_run_workflow("firewall_summary",  {"device": "HQV-PE1-NEW"})
nautobot_run_workflow("interface_detail",  {"device": "HQV-PE1-NEW"})
nautobot_run_workflow("devices_inventory", {"device": "HQV-PE1-NEW"})
```

### CLI (scripts/uat_cms_smoke.py)
```bash
uv run nautobot-mcp --json cms routing bgp-summary --device HQV-PE1-NEW
uv run nautobot-mcp --json cms routing routing-table --device HQV-PE1-NEW
uv run nautobot-mcp --json cms firewalls firewall-summary --device HQV-PE1-NEW
uv run nautobot-mcp --json cms interfaces detail --device HQV-PE1-NEW
uv run nautobot-mcp --json devices inventory --device HQV-PE1-NEW
```

---

## Deliverable

`scripts/uat_cms_smoke.py` — standalone UAT script that:
- Reads `NAUTOBOT_URL` + `NAUTOBOT_TOKEN` from environment (prod profile)
- Runs all 5 workflows via `uv run nautobot-mcp --json ...` subprocess calls
- Prints a summary table: `PASS | FAIL | SKIP` per workflow
- Prints total elapsed time
- Exits `0` if all pass, `1` otherwise
- Uses `--json` flag equivalent via Python API calls to avoid Unicode encoding issues

---

## Success Definition

All 5 CMS data presence checks return `status != "error"` and primary data is accessible. "Empty data" (e.g., `total_groups = 0`) is a **valid pass** — it means the device legitimately has no BGP configured.

## Next Steps (Post-UAT)

- If any workflow returns `"error"` status → investigate CMS plugin data population pipeline for HQV-PE1-NEW
- If all pass → proceed to Layer 2 UAT (CMS vs Live device drift via jmcp)
