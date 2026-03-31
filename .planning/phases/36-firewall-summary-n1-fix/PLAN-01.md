---
gsd:
  wave: 1
  depends_on: []
  files_modified:
    - nautobot_mcp/cms/firewalls.py
  autonomous: true
---

# Plan 01: Bulk Terms Prefetch — Eliminate Per-Filter N+1 Loop

## Goal

Replace the per-filter `list_firewall_terms(filter_id=fw_filter.id)` loop in `get_device_firewall_summary(detail=True)` with a single device-scoped bulk fetch, then index by `filter_id` for O(1) lookup.

**Addresses CQP-02** (≤6 HTTP calls) and **CQP-05** (WarningCollector preserved).

## Actions

### A. Add bulk terms prefetch block inside `if detail:` in `get_device_firewall_summary`

Insert **after** line 702 (`if not filters_ok and not policers_ok: raise`) and **before** line 704 (`if detail:`), inside the existing `if detail:` block — as the very first thing in the detail branch, before the filter loop at line 707:

```python
    if detail:
        # ------------------------------------------------------------------
        # BULK TERM PREFETCH (replaces per-filter list_firewall_terms loop)
        # ------------------------------------------------------------------
        device_id = resolve_device_id(client, device)

        terms_by_filter: dict[str, list] = {}
        try:
            all_terms_resp = cms_list(
                client,
                "juniper_firewall_terms",
                FirewallTermSummary,
                device=device_id,
                limit=0,
            )
            for t in all_terms_resp.results:
                terms_by_filter.setdefault(t.filter_id, []).append(t)
        except Exception as e:
            collector.add("bulk_terms_fetch", str(e))
            terms_by_filter = {}

        # ------------------------------------------------------------------
        # BULK ACTION PREFETCH (replaces per-policer list_firewall_policer_actions loop)
        # ------------------------------------------------------------------
        actions_by_policer: dict[str, list] = {}
        try:
            all_actions_resp = cms_list(
                client,
                "juniper_firewall_policer_actions",
                FirewallPolicerActionSummary,
                device=device_id,
                limit=0,
            )
            for a in all_actions_resp.results:
                actions_by_policer.setdefault(a.policer_id, []).append(a)
        except Exception as e:
            collector.add("bulk_actions_fetch", str(e))
            actions_by_policer = {}

        # Now populate filter_dicts using the prefetched lookup maps
        filter_dicts = []
        for fw_filter in filters_data:
            fd = fw_filter.model_dump()
            terms_list = terms_by_filter.get(fw_filter.id, [])
            terms_capped = terms_list[:limit] if limit > 0 else terms_list
            fd["terms"] = [t.model_dump() for t in terms_capped]
            fd["term_count"] = len(terms_list)
            filter_dicts.append(fd)
        # Cap filters[] at limit
        filter_dicts = filter_dicts[:limit] if limit > 0 else filter_dicts

        # Populate policer_dicts using the prefetched lookup maps
        policer_dicts = []
        for policer in policers_data:
            pd = policer.model_dump()
            actions_list = actions_by_policer.get(policer.id, [])
            actions_capped = actions_list[:limit] if limit > 0 else actions_list
            pd["actions"] = [a.model_dump() for a in actions_capped]
            pd["action_count"] = len(actions_list)
            policer_dicts.append(pd)
        # Cap policers[] at limit
        policer_dicts = policer_dicts[:limit] if limit > 0 else policer_dicts
```

**Delete entirely** the original filter loop (lines 707-719) and original policer loop (lines 721-735) — they are replaced by the new block above.

**Keep** the original `else:` block (lines 736-741) — it remains unchanged.

**After the `if detail:` / `else:` branches**, the existing result construction (lines 743-750) remains unchanged.

### B. Type annotation

Confirm `dict` is available in `get_device_firewall_summary`'s scope. Python 3.11+ has `dict` built-in; no import needed. `FirewallTermSummary` and `FirewallPolicerActionSummary` are already imported at module lines 27-34.

## Verification

```bash
cd d:/latuan/Programming/nautobot-mcp-cli
uv run pytest tests/test_cms_firewalls_n1.py -v
```

All 8 tests must pass.

## must_haves

- `nautobot_mcp/cms/firewalls.py` contains `terms_by_filter: dict[str, list] = {}`
- `nautobot_mcp/cms/firewalls.py` contains `actions_by_policer: dict[str, list] = {}`
- `nautobot_mcp/cms/firewalls.py` contains `collector.add("bulk_terms_fetch", str(e))`
- `nautobot_mcp/cms/firewalls.py` contains `collector.add("bulk_actions_fetch", str(e))`
- `nautobot_mcp/cms/firewalls.py` does NOT contain `list_firewall_terms(client, filter_id=fw_filter.id`
- `nautobot_mcp/cms/firewalls.py` does NOT contain `list_firewall_policer_actions(client, policer_id=policer.id`
- `tests/test_cms_firewalls_n1.py` exists and has 8 test functions
- `uv run pytest tests/test_cms_firewalls_n1.py` exits 0
