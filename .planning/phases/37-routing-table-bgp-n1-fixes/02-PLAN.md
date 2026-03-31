---
plan: 02
wave: 1
depends_on: []
requirements_addressed: [CQP-04]
files_modified:
  - nautobot_mcp/cms/routing.py
autonomous: true
---

<objective>

Verify that `get_device_bgp_summary()` in `nautobot_mcp/cms/routing.py` has correct per-neighbor AF/policy fallback guards. The guards are already in place and are sufficient — no code changes are required. This plan documents the guard pattern with an inline comment so future maintainers understand why the fallback never fires under normal conditions.

CQP-04 is already satisfied. This plan adds a documentation comment only.

</objective>

<read_first>

- `nautobot_mcp/cms/routing.py` — L639-779 (`get_device_bgp_summary`). Focus on:
  - L687: `if detail and all_neighbors:` (Guard #1)
  - L709-711: `neighbor_ids`, `af_keyed_usable`, `pol_keyed_usable`
  - L728-731: shared-enrichment fallback when `af_keyed_usable=False`
  - L734-747: per-neighbor fallback with triple guards (Guards #2 and #3)
  - L748-751: `af_bulk_failed` / `pol_bulk_failed` hard-fail guards

</read_first>

<action>

**File:** `nautobot_mcp/cms/routing.py`

**No code changes.** Add one inline comment above Guard #1 to document the guard pattern for maintainers.

Find this block in `get_device_bgp_summary()` (around L687):

```python
        # Bulk fetch AFs/policies only when detail=True AND there are neighbors.
        # Without this guard, both endpoints cause 60s+ timeouts even at limit=1
        # (unindexed global scans on the Nautobot CMS plugin). HQV-PE1-NEW has
        # 0 BGP groups so these fetches serve no purpose in the default path.
        af_by_nbr: dict = {}
```

Replace it with this (append the extra guard-documentation sentence):

```python
        # Bulk fetch AFs/policies only when detail=True AND there are neighbors.
        # Without this guard, both endpoints cause 60s+ timeouts even at limit=1
        # (unindexed global scans on the Nautobot CMS plugin). HQV-PE1-NEW has
        # 0 BGP groups so these fetches serve no purpose in the default path.
        #
        # CQP-04: Per-neighbor AF/policy fallback is gated by a triple guard:
        #   (a) bulk returned no results for this neighbor   [not fam_list / not pol_list]
        #   (b) the bulk fetch itself did not error            [not *_bulk_failed]
        #   (c) the bulk results contain usable neighbor_id keys [af_keyed_usable / pol_keyed_usable]
        # When all three hold AND bulk IS keyed, the fallback fires (per-neighbor fetch).
        # When af_keyed_usable is False (bulk has no matching neighbor_id keys),
        # the fallback is suppressed — avoids per-neighbor calls on unkeyed test data.
        # This matches Phase 35 VRRP graceful-degradation guard pattern.
        af_by_nbr: dict = {}
```

Also add a trailing comment to the triple-guard block at L733-747 for clarity. Find this line:

```python
                    # Fallback per-neighbor only when bulk side produced no usable data and didn't fail.
                    if not fam_list and not af_bulk_failed and af_keyed_usable:
```

Append this note on the same comment line or as a trailing `# CQP-04 triple guard` comment:

```python
                    # Fallback per-neighbor only when bulk side produced no usable data and didn't fail.
                    # Triple guard: (a) no bulk data for this neighbor, (b) no bulk failure, (c) keyed usable
                    if not fam_list and not af_bulk_failed and af_keyed_usable:
```

Do the same for the policy guard at L741:

```python
                    if not pol_list and not pol_bulk_failed and pol_keyed_usable:
```

Add trailing comment:

```python
                    # Triple guard: (a) no bulk data for this neighbor, (b) no bulk failure, (c) keyed usable
                    if not pol_list and not pol_bulk_failed and pol_keyed_usable:
```

**Summary of changes:** 3 comment additions only. Zero functional code changes. The triple-guard pattern is already correct and already prevents unnecessary per-neighbor calls.

</action>

<acceptance_criteria>

- [ ] `nautobot_mcp/cms/routing.py` contains the string `CQP-04` in the `get_device_bgp_summary` function (grep-verifiable)
- [ ] `nautobot_mcp/cms/routing.py` contains the string `triple guard` in the `get_device_bgp_summary` function (grep-verifiable)
- [ ] `nautobot_mcp/cms/routing.py` contains the string `af_keyed_usable` in the `get_device_bgp_summary` function (already present — verifies guard variable still exists)
- [ ] `nautobot_mcp/cms/routing.py` contains the string `pol_keyed_usable` in the `get_device_bgp_summary` function (already present — verifies guard variable still exists)
- [ ] The triple-guard conditions `not fam_list and not af_bulk_failed and af_keyed_usable` and `not pol_list and not pol_bulk_failed and pol_keyed_usable` are unchanged (grep L734 and L741 in file)
- [ ] `nautobot_mcp/cms/routing.py` has no new `cms_list` calls added in `get_device_bgp_summary` — function still calls `list_bgp_address_families` and `list_bgp_policy_associations` at L689 and L699 only

</acceptance_criteria>

<verify>

```bash
uv run pytest tests/test_cms_routing_n1.py -v -k bgp
```

All 4 BGP tests (B1–B4) must pass. The guard pattern was already correct — Plan 02 only adds documentation comments. Tests should pass without any mock changes.

</verify>
