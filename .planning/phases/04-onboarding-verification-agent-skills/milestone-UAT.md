---
status: complete
phase: milestone-v1.0
source: [automated smoke tests, live Nautobot API, code inspection]
started: 2026-03-17T21:04:00+07:00
updated: 2026-03-18T08:06:00+07:00
---

## Tests

### 1. Cold Start Smoke Test
expected: `pip install -e ".[dev]"` succeeds, `pytest tests/ -v` shows 76 pass, `nautobot-mcp --help` shows CLI with subcommands
result: ✅ PASS — 76 tests pass, CLI help shows all 9 command groups

### 2. List Devices from Nautobot
expected: `nautobot-mcp devices list` returns a formatted table of devices from nautobot.netnam.vn
result: ✅ PASS — 62 devices returned (BPOP-HITC, CEN, ...)

### 3. Get Device Detail
expected: `nautobot-mcp devices get <device-name>` returns detailed device info
result: ✅ PASS — BPOP-HITC: Status=Active, Location=HITC/HAN, Role=ACC, Platform=h3c_comware

### 4. List Device Interfaces
expected: `nautobot-mcp interfaces list <device-name>` returns a table of interfaces
result: ✅ PASS — 44 interfaces on BPOP-HITC (GigabitEthernet1/0/1..44, type=Other)

### 5. Parse JunOS Config
expected: Parser extracts interfaces, IPs, VLANs from JunOS JSON fixture
result: ✅ PASS — Parsed: interfaces=[ge-0/0/0], IPs=[10.0.0.1/30]
note: Bug fixed — JunOS JSON wraps scalars in `[{"data": "value"}]`. Added `_scalar()` helper to parser.

### 6. Onboard Config Dry-Run
expected: Shows planned actions without making changes to Nautobot
result: ✅ PASS — 4 actions: [create] device test-junos-01, [create] ge-0/0/0, [create] prefix 10.0.0.0/30, [skip] 10.0.0.1/30 (already exists)
note: Bug fixed — 400 validation errors from Nautobot (device not found) now handled gracefully in dry-run.

### 7. Verify Data Model
expected: Drift report comparing parsed config vs Nautobot records
result: ✅ PASS — total_drifts=49 (1 missing in Nautobot: ge-0/0/0, 44 extra in Nautobot: real device interfaces, 0 VLANs)
note: Bug fixed — was fetching ALL 10k VLANs globally. Now scopes to only VIDs in parsed config. Speed: ~2min (network) vs previously hanging forever.

### 8. MCP Server Starts
expected: Server exposes tools with `nautobot_` prefix
result: ✅ PASS — 44 tools registered (nautobot_assign_ip_to_interface, nautobot_create_circuit, nautobot_create_device, ...)

### 9. Agent Skill Guide — Onboard Router Config
expected: `.agent/skills/onboard-router-config/SKILL.md` exists with workflow + tool references
result: ✅ PASS — File present. References nautobot_onboard_config, dry_run param documented, step workflow present.

### 10. Agent Skill Guide — Verify Compliance
expected: `.agent/skills/verify-compliance/SKILL.md` exists with compliance + drift workflows
result: ✅ PASS — File present. References nautobot_verify_config_compliance, nautobot_verify_data_model, DriftReport documented.

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0

## Bugs Found and Fixed During UAT

1. **JunOS parser `_scalar()` missing** — parser read `[{"data":"ge-0/0/0"}]` as a list object and called `.startswith()` on it. Fixed by adding `_scalar()` helper applied to all 16 string reads.
2. **Onboarding dry-run on unknown device** — Nautobot returns 400 (not 404) when interface is queried for a non-existent device. Fixed by broadening exception catch in `_resolve_interfaces`.
3. **Config test isolation** — 3 `test_config.py` tests failed when `NAUTOBOT_URL`/`NAUTOBOT_TOKEN` env vars were set. Fixed with `monkeypatch.delenv`.
4. **`IPAddressSummary` namespace required** — API doesn't always return namespace on IP records. Made field optional.
5. **VLAN performance** — `verify_data_model` fetched ALL 10k VLANs with no filter, causing 10+ minute hangs. Fixed by scoping VLAN queries to only VIDs in parsed config; skip entirely when parsed config has no VLANs.
