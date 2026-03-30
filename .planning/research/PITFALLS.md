# Pitfalls Research: CMS Pagination Fix (v1.8)

## Pitfall 1: Setting `endpoint.page_size` — Does Nothing

**Warning sign:** Code sets `endpoint.page_size = 200` or `endpoint._page_size = 200` before calling `.all()`.

**Why it's wrong:** pynautobot's `Endpoint` has no `page_size` attribute. It is never read during pagination. Only `Request(limit=N)` controls page size.

**Prevention:** Unit test verifies `.all()` is called with `limit=200` (not `limit=0`).

## Pitfall 2: Global `api.max_workers` or `api.threading` Mutation — Thread Hazard

**Warning sign:** Code sets `endpoint.api.max_workers = 8` or `client.api.threading = True` to speed up pagination.

**Why it's wrong:** `Endpoint` objects share the same `api` reference. Mutating it globally affects ALL endpoints and ALL concurrent operations. In the MCP server (multi-request), this causes race conditions.

**Prevention:** Pass `limit` per-call; never mutate `api` attributes.

## Pitfall 3: Overriding `limit > 0` — Caller Intent Violated

**Warning sign:** Code changes `limit` when `limit > 0` (e.g., `cms_list(limit=50)` → sends `limit=200`).

**Why it's wrong:** Caller explicitly requested 50 records. Overriding it violates the contract and may cause unexpected data volumes.

**Prevention:** Only override when `limit == 0`. `limit > 0` passes through unchanged.

## Pitfall 4: Setting `limit` Too High — Server Rejects 400/422

**Warning sign:** Code uses `_CMS_BULK_LIMIT = 1000` or higher.

**Why it's wrong:** CMS plugin may cap page size at a lower value (e.g., 200). Server returns 400/422 → operation fails.

**Prevention:** Use `_CMS_BULK_LIMIT = 200`. If server rejects, pynautobot raises `NautobotValidationError` — acceptable failure mode, logged. Future improvement: retry with half.

## Pitfall 5: Bypassing pynautobot with Direct HTTP — Loses Retries + Error Translation

**Warning sign:** `cms_list()` uses `client.api.http_session.get()` directly instead of `endpoint.all()`.

**Why it's wrong:** Loses pynautobot's retry logic (3 retries on 500/502/503/504) and error translation. More fragile.

**Prevention:** Always use `endpoint.all(limit=N)` or `endpoint.filter(limit=N, **filters)`.

## Pitfall 6: New List Function Bypasses `cms_list()` — Silent Regression

**Warning sign:** Someone adds `endpoint.all()` or `endpoint.filter()` directly in a new CMS function instead of calling `cms_list()`.

**Prevention:** Add a lint rule or code comment: "Always use `cms_list()` for CMS list operations." Review in code review.

## Pitfall 7: Changing `_CMS_BULK_LIMIT` Without Evidence

**Warning sign:** Someone raises `_CMS_BULK_LIMIT` to 1000 without testing against prod CMS plugin.

**Prevention:** Document: "Align with Nautobot's de facto cap of 1000 and CMS plugin limits. Test live before changing."

**Researched:** 2026-03-29

## Pitfall 1: pynautobot Record vs raw dict

**Problem:** Direct HTTP returns raw dicts. Code that uses `ip.id`, `ip.address`, `ip.status.display` expects pynautobot `Record` objects with lazy attribute access.

**Prevention:** Use `endpoint.return_obj(raw_dict, api, endpoint)` to wrap raw dicts back into Record objects — same pattern already used in `list_interfaces()`.

## Pitfall 2: Direct HTTP pagination not triggered

**Problem:** `http_session.get()` with DRF comma-separated `id__in` returns one page of results. If 700 IPs exceed Nautobot's page size, only first page is returned.

**Prevention:** Check `data.get("next")` after HTTP call. If present, follow pagination links and collect all pages in a loop. Same pattern as `list_interfaces()`.

## Pitfall 3: M2M endpoint comma-separated support

**Problem:** `ip_address_to_interface` is a custom join table. DRF may or may not support comma-separated format for `interface` param.

**Verification needed:** Test against actual Nautobot server. If comma-separated doesn't work for M2M endpoint, fall back to `.filter(interface=chunk)` with a smaller chunk size (e.g., 100 instead of 500) to stay under URI limit.

**Risk:** Medium — but this is testable in unit tests with a mock.

## Pitfall 4: Bridge guard breaks existing callers

**Problem:** The bridge currently accepts `params={"id__in": [uuid1, uuid2]}` with small lists and it works. Our guard must not break callers who pass 2-3 UUIDs.

**Prevention:** Only raise for lists > 500 items. Lists ≤ 500 continue using existing path (converted to comma-separated).

## Pitfall 5: Empty lists after conversion

**Problem:** If device has no IPs, `ip_ids` is empty. Direct HTTP call with `id__in=` (empty) could fail or return unexpected results.

**Prevention:** Check `if not ip_ids: return early` before making HTTP calls in both Pass 2 and Pass 3.

## Pitfall 6: VLANs 500 — server-side, not fixable here

**Problem:** `/api/ipam/vlans/count/?location=HQV` returns 500 from Nautobot server. We can't fix server code.

**Mitigation:** Catch 500 specifically in `count()` method in `client.py`. On 500, return `None` (not an error) so the operation can continue without the VLAN count. Document this as a known Nautobot server issue.

## Pitfall 7: Regression testing without live server

**Problem:** Unit tests mock pynautobot. Direct HTTP calls bypass pynautobot's `.filter()`, so existing mocks won't cover the new code paths.

**Prevention:** Add unit tests that mock `http_session.get()` directly. Mock the JSON response and verify correct URL/params are built.

## Pitfall 8: 414 still possible for intermediate chunk sizes

**Problem:** Even with comma-separated format, 500 UUIDs at ~36 chars each = ~18 KB. Some proxies/servers have limits below 8 KB. 500 is not guaranteed safe everywhere.

**Conservative approach:** Lower chunk size from 500 to 200 for the comma-separated path. ~7 KB per request — safely under 8 KB on all standard servers.

**Risk:** More HTTP round-trips for very large devices. Benefit: fewer 414 edge cases.

**Decision needed:** Use 500 with comma-separated (risky on some configs) or 200 (safer but more round-trips)?

## Pitfall 9: Bridge param guard — dict vs list confusion

**Problem:** `params={"tag": ["foo", "bar"]}` is a valid list param that DRF handles fine as `?tag=foo&tag=bar`. The guard should NOT reject this — only reject `__in` filters with > 500 items.

**Prevention:** Apply size limit only to params ending with `__in` (or `__id__in`). Other list params are fine as-is.

## Watch out for

1. Testing M2M comma-separated approach against real Nautobot
2. Handling pagination on direct HTTP calls
3. Not breaking existing small-list callers in the bridge guard
4. Catching 500 on VLANs count gracefully
5. Unit testing the new direct HTTP paths with mocked http_session
