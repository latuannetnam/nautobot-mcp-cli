# Plan 02 — Unit Test Gate (RGP-02)

**Phase:** 38-regression-gate
**Requirement:** RGP-02
**Wave:** 1
**Status:** Ready to execute

---

## Objective

Run full unit test suite, verify no regressions from the Phase 35–37 N+1 refactors.

---

## Task 38-02-01 — Run Unit Test Suite

### <read_first>

- `pytest.ini` at project root — test configuration and testpaths
- `tests/test_cms_interfaces_n1.py` — Phase 35 N+1 tests (8 tests)
- `tests/test_cms_firewalls_n1.py` — Phase 36 N+1 tests (8 tests)
- `tests/test_cms_routing_n1.py` — Phase 37 N+1 tests (9 tests)
- `38-RESEARCH.md` — baseline: 558 collected, 569 total (11 deselected)

### <action>

```bash
uv run pytest -q
```

> No credentials required — all tests are mocked/unit.

### <acceptance_criteria>

- [ ] All 558 tests collected → 558 passed
- [ ] 0 failed, 0 errored, 0 xfailed (unless expected)
- [ ] Exit code 0
- [ ] Count matches baseline (558 from 38-RESEARCH.md; any delta needs justification)

### <rollback>

Not applicable — unit tests are read-only.

---

## Success Criteria

- `uv run pytest -q` → `558 passed in ~Xs`
- RGP-02 satisfied → mark RGP-02 **Done** in `.planning/REQUIREMENTS.md`
- Both RGP-01 and RGP-02 complete → Phase 38 COMPLETE
