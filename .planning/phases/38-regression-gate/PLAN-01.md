# Plan 01 — Smoke Test Gate (RGP-01)

**Phase:** 38-regression-gate
**Requirement:** RGP-01
**Wave:** 1
**Status:** Ready to execute

---

## Objective

Run UAT smoke test against HQV-PE1-NEW, verify all 5 CMS workflows pass within thresholds.

---

## Task 38-01-01 — Run Smoke Test

### <read_first>

- `scripts/uat_cms_smoke.py` — smoke test script (391 lines)
  - Lines 191–201: `THRESHOLD_MS` dict
  - Lines 218–328: `run_workflow()` — subprocess runner with threshold check
  - Lines 331–358: `print_results()` — summary table + HTTP call counts

### <action>

```bash
uv run python scripts/uat_cms_smoke.py HQV-PE1-NEW --profile prod
```

> Requires: `NAUTOBOT_URL` + `NAUTOBOT_TOKEN` set (or `--profile prod` using `.nautobot-mcp.yaml` credentials).

### <acceptance_criteria>

- [ ] All 5 workflow rows show `PASS` in the result column
- [ ] No row exceeds `THRESHOLD_MS` (bgp_summary ≤ 5000ms, others ≤ 15000ms)
- [ ] No timeout (120s hard limit) or parse error
- [ ] Exit code 0 (`All CMS smoke tests PASSED.`)
- [ ] Actual elapsed_ms per workflow recorded in phase summary

### <rollback>

Not applicable — read-only smoke test, no mutations.

---

## Success Criteria

- All 5 workflows: `PASS`
- RGP-01 satisfied → mark RGP-01 **Done** in `.planning/REQUIREMENTS.md`
