---
phase: 33
plan: 02
slug: endpoint-discovery
status: draft
wave: 1
dependencies: []
autonomous: false
requirements: [DISC-01, DISC-02]
must_haves:
  - HTTP call count instrumented in smoke test before fix
  - Post-fix smoke run confirms bgp_summary completes in < 5s
  - Discovery findings written to Phase 33 summary document
---

# Plan 02: Endpoint Discovery

**Phase:** 33 — CMS Pagination Fix
**Goal:** Instrument CMS list functions with HTTP call counting; document which endpoints have PAGE_SIZE=1
**Requirements:** DISC-01, DISC-02

## Wave 1

### Task 33-02-01: Instrument `uat_cms_smoke.py` with HTTP call counter

<read_first>
- `scripts/uat_cms_smoke.py` — L1-225 (entire file, current implementation)
- `nautobot_mcp/cms/client.py` — L107-125 (`get_cms_endpoint()`) and L128-159 (`cms_list()`)
</read_first>

<action>
Instrument `scripts/uat_cms_smoke.py` by monkey-patching `requests.Session.get` at the top of `run_workflow()`. The patch wraps the real `get()` call and records the URL called for each HTTP GET. Each `subprocess.run()` call in the smoke test invokes the CLI which internally makes HTTP calls via `requests`. Since we cannot monkey-patch across subprocess boundaries, instead instrument the HTTP call counting at the **pynautobot `Request._make_call`** level, which is invoked within the same process when `nautobot-mcp` CLI is called.

Add the following at the top of `uat_cms_smoke.py`, after the `WORKFLOWS` constant and before `@dataclass`:

```python
# HTTP call counter — instruments pynautobot Request._make_call
_http_call_counts: dict[str, int] = {}
_original_make_call = None

def _counting_make_call(self, *args, **kwargs):
    """Monkey-patch wrapper that counts HTTP GET calls per URL path."""
    global _http_call_counts
    url = args[0] if args else kwargs.get("url", "")
    # Extract path from URL for readability (e.g., /api/plugins/netnam-cms-core/...)
    if hasattr(self, "session") and self.session:
        base = self.session.get("base_url", "")
        if url.startswith(base):
            path = url[len(base):]
        else:
            path = url
    else:
        path = url
    key = path.rstrip("?").split("?")[0]  # strip trailing ? and query for grouping
    _http_call_counts[key] = _http_call_counts.get(key, 0) + 1
    return _original_make_call(self, *args, **kwargs)

def _install_counter():
    """Install HTTP call counter monkey-patch on pynautobot Request class."""
    global _original_make_call
    if _original_make_call is None:
        import pynautobot.core.request as req
        _original_make_call = req.Request._make_call
        req.Request._make_call = _counting_make_call

def _get_counts() -> dict[str, int]:
    """Return snapshot of HTTP call counts and reset."""
    global _http_call_counts
    snap = dict(_http_call_counts)
    _http_call_counts = {}
    return snap
```

Add `import pynautobot.core.request as req` to the imports at the top.

In `run_workflow()`, wrap the subprocess call with counter install/restore:

```python
def run_workflow(workflow: dict) -> WorkflowResult:
    _install_counter()   # install or no-op if already installed
    # ... existing subprocess.run code ...
    counts = _get_counts()
    # Attach counts to result for reporting
```

Since `WorkflowResult` is a `@dataclass`, it cannot carry extra fields without modification. Instead, print the per-workflow counts inline in `print_results()` by storing them in a module-level `dict` keyed by workflow id:

```python
_workflow_counts: dict[str, dict[str, int]] = {}

def run_workflow(workflow: dict) -> WorkflowResult:
    global _workflow_counts
    _install_counter()
    # ... existing code ...
    counts = _get_counts()
    _workflow_counts[workflow["id"]] = counts
    # ... existing result construction ...
```

Then in `print_results()`, after printing elapsed_ms for each result, add a counts summary below the main table:

```python
def print_results(results: list[WorkflowResult], total_ms: float) -> None:
    # ... existing table code ...
    print(f"\n  --- HTTP Call Counts per Workflow ---")
    for wid, counts in _workflow_counts.items():
        total_calls = sum(counts.values())
        print(f"  {wid}: {total_calls} total calls")
        for path, n in sorted(counts.items(), key=lambda x: -x[1])[:5]:
            if n > 1:
                print(f"    {n:3d}x {path}")
    _workflow_counts.clear()
```

This gives an empirical measurement of HTTP call counts per CMS endpoint before and after the fix.
</action>

<acceptance_criteria>
- [ ] `grep -n "_http_call_counts\|_counting_make_call\|_install_counter\|_get_counts" scripts/uat_cms_smoke.py` returns matches in the new instrumentation code
- [ ] `grep -n "_workflow_counts" scripts/uat_cms_smoke.py` returns matches for both write (in `run_workflow()`) and read (in `print_results()`)
- [ ] `grep -n "import pynautobot" scripts/uat_cms_smoke.py` returns 1 match
- [ ] `uv run python -c "exec(open('scripts/uat_cms_smoke.py').read())"` — script parses without syntax errors (import check only)
- [ ] **DISC-01:** Running the smoke test against prod (after Plan 01 fix is applied) shows `bgp_summary` HTTP call count ≈ ceil(151/200) = 1 call for `juniper_bgp_address_families`, not 151
</acceptance_criteria>

---

### Task 33-02-02: Document discovery findings in Phase 33 summary

<read_first>
- `scripts/uat_cms_smoke.py` — the HTTP call count output produced by Task 33-02-01
- `.planning/phases/33-cms-pagination-fix/33-RESEARCH.md` — L1-369 (existing research findings)
</read_first>

<action>
After running the instrumented smoke test post-fix (once Plan 01 is applied), record findings in a new section in `33-RESEARCH.md`. Add the following section at the end of `33-RESEARCH.md`:

```markdown
---

## Discovery Findings (Post-Fix Empirical Results)

**Date:** {date of smoke test run}
**Profile:** prod (https://nautobot.netnam.vn)
**Device:** HQV-PE1-NEW

### HTTP Call Counts (Post-Fix)

| Workflow | Endpoint | HTTP Calls (Post-Fix) | Expected (ceil(N/200)) |
|----------|----------|------------------------|------------------------|
| bgp_summary | juniper_bgp_address_families | TBD | ~1 |
| routing_table | juniper_static_routes | TBD | ~1 |
| firewall_summary | juniper_firewall_filters | TBD | ~1 |
| interface_detail | juniper_interface_units | TBD | ~1 |

### Slow Endpoints Confirmed

| Endpoint | PAGE_SIZE | Records (HQV-PE1-NEW) | Calls Before Fix | Calls After Fix |
|----------|-----------|----------------------|------------------|-----------------|
| juniper_bgp_address_families | 1 (CMS plugin default) | 151 | 151 | ~1 |
| ... | ... | ... | ... | ... |

### Observations

- **All CMS endpoints benefit from `_CMS_BULK_LIMIT = 200`** — the fix is universal and not endpoint-specific
- **No endpoint-specific registry needed** — D-04 confirmed correct
- **DISC-02 satisfied** — findings documented here (not in code registry)
```

Update the table rows with actual measured values from the smoke test run. If no additional slow endpoints are discovered beyond `juniper_bgp_address_families`, note that explicitly.

**DISC-02 resolution:** The "registry" from DISC-02 is implemented as this findings section in `33-RESEARCH.md` (per D-04/D-05). No `CMS_SLOW_ENDPOINTS` dict is added to `cms/client.py`.
</action>

<acceptance_criteria>
- [ ] `grep -n "HTTP Call Counts\|Slow Endpoints Confirmed" .planning/phases/33-cms-pagination-fix/33-RESEARCH.md` returns matches in the new section
- [ ] At least one endpoint table row with empirically measured call counts is present
- [ ] No `CMS_SLOW_ENDPOINTS` dict exists in `nautobot_mcp/cms/client.py` (DISC-02 registry in code is NOT added)
- [ ] **DISC-02 verified:** findings are documented in `33-RESEARCH.md` — not in code
</acceptance_criteria>

---

## Summary

| Task | Requirement | Status |
|------|-------------|--------|
| 33-02-01 | DISC-01 (HTTP call counting instrumented in smoke test) | ⬜ |
| 33-02-02 | DISC-02 (findings documented in 33-RESEARCH.md) | ⬜ |

**Quality gate:** Smoke test runs end-to-end without crash; HTTP call counts are visible in output.
