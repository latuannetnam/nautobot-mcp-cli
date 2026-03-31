---
plan: 01
wave: 1
depends_on: []
requirements_addressed: [CQP-03]
files_modified:
  - nautobot_mcp/cms/routing.py
autonomous: true
---

<objective>

Remove the per-route nexthop fallback loop (L96-123) in `list_static_routes()` in `nautobot_mcp/cms/routing.py`. After the bulk nexthop/qualified-nexthop fetches at L79-92, a for-loop at L96-123 fires `cms_list(route=route.id)` for every route not already in the bulk maps — this is the N+1. Delete it entirely. Inline `route.nexthops` assignment into the existing `if routes.results:` block.

**Target:** `get_device_routing_table` makes ≤3 HTTP calls regardless of route count:
1. `cms_list("juniper_static_routes", device=device_id, limit=0)` — routes list
2. `cms_list("juniper_static_route_nexthops", device=device_id, limit=0)` — all nexthops
3. `cms_list("juniper_static_route_qualified_nexthops", device=device_id, limit=0)` — all qualified nexthops

</objective>

<read_first>

- `nautobot_mcp/cms/routing.py` — L40-129 (`list_static_routes`). This is the file being modified.
- `tests/test_cms_interfaces_n1.py` L1-80 — Phase 35 monkey-patch pattern for unit tests.
- `tests/test_cms_firewalls_n1.py` L1-61 — Phase 36 helper pattern (`_mock_list_response`, `_mock_filter`).

</read_first>

<action>

**File:** `nautobot_mcp/cms/routing.py`

**Step 1 — Delete the backward-compatible fallback for-loop (L94-123)**

Delete exactly these lines (the entire `for route in routes.results:` block):

```
            # Backward-compatible fallback: if bulk map has no entry for a route,
            # query that route directly (preserves old test behavior/mocks)
            for route in routes.results:
                if route.id not in nh_by_route:
                    try:
                        per_route_nhs = cms_list(
                            client,
                            "juniper_static_route_nexthops",
                            StaticRouteNexthopSummary,
                            limit=0,
                            route=route.id,
                        )
                        nh_by_route[route.id] = per_route_nhs.results
                    except Exception:
                        nh_by_route[route.id] = []
                if route.id not in qnh_by_route:
                    try:
                        per_route_qnhs = cms_list(
                            client,
                            "juniper_static_route_qualified_nexthops",
                            StaticRouteNexthopSummary,
                            limit=0,
                            route=route.id,
                        )
                        qnh_by_route[route.id] = per_route_qnhs.results
                    except Exception:
                        qnh_by_route[route.id] = []

                route.nexthops = nh_by_route.get(route.id, [])
                route.qualified_nexthops = qnh_by_route.get(route.id, [])
```

In the file at the time of this plan, that block spans from the line containing `# Backward-compatible fallback:` through the line `route.qualified_nexthops = qnh_by_route.get(route.id, [])` — ending at L123.

**Step 2 — Add inline nexthop assignment inside the existing `if routes.results:` block**

After the two `except Exception: pass` blocks (after L92), add:

```python
            # Inline nexthops into each route from the bulk maps (no per-route HTTP calls)
            for route in routes.results:
                route.nexthops = nh_by_route.get(route.id, [])
                route.qualified_nexthops = qnh_by_route.get(route.id, [])
```

This replaces the per-route fallback loop's inline assignment. It stays inside the `if routes.results:` block (which begins at L75), so indentation is 12 spaces (3 levels × 4 spaces).

**Resulting structure after both changes (L65-129):**

```python
def list_static_routes(...):
    try:
        device_id = resolve_device_id(...)
        filters = {"device": device_id}
        if routing_instance:
            filters["routing_instance__name"] = routing_instance

        routes = cms_list(client, "juniper_static_routes", StaticRouteSummary,
                          limit=limit, offset=offset, **filters)

        if routes.results:
            nh_by_route: dict = {}
            qnh_by_route: dict = {}
            try:
                all_nhs = cms_list(client, "juniper_static_route_nexthops",
                                   StaticRouteNexthopSummary, limit=0, device=device_id)
                for nh in all_nhs.results:
                    nh_by_route.setdefault(nh.route_id, []).append(nh)
            except Exception:
                pass
            try:
                all_qnhs = cms_list(client, "juniper_static_route_qualified_nexthops",
                                    StaticRouteQualifiedNexthopSummary, limit=0, device=device_id)
                for q in all_qnhs.results:
                    qnh_by_route.setdefault(q.route_id, []).append(q)
            except Exception:
                pass

            # Inline nexthops into each route from the bulk maps (no per-route HTTP calls)
            for route in routes.results:
                route.nexthops = nh_by_route.get(route.id, [])
                route.qualified_nexthops = qnh_by_route.get(route.id, [])

        return ListResponse(count=len(routes.results), results=routes.results)
    except Exception as e:
        client._handle_api_error(e, "list", "StaticRoute")
        raise
```

**No other changes.** The `except Exception: pass` blocks at L84-85 and L91-92 already provide silent graceful degradation when bulk fetches fail — routes return with `nexthops = []` automatically. No `WarningCollector` needed for nexthop enrichment (non-critical data, matching Phase 35 VRRP pattern).

</action>

<acceptance_criteria>

- [ ] `nautobot_mcp/cms/routing.py` contains no `cms_list` call with a `route=` keyword argument anywhere in `list_static_routes()` — verify with `grep -n "route=" nautobot_mcp/cms/routing.py` and check no match falls within the `list_static_routes` function body (L46-129)
- [ ] `nautobot_mcp/cms/routing.py` contains exactly one `for route in routes.results:` loop inside `list_static_routes()` — the inline-assignment loop; no fallback loop
- [ ] The inline assignment block contains: `route.nexthops = nh_by_route.get(route.id, [])` and `route.qualified_nexthops = qnh_by_route.get(route.id, [])`
- [ ] The phrase `Backward-compatible fallback` does NOT appear in `list_static_routes()` (grep-verifiable)
- [ ] `list_static_routes()` still has 3 distinct `cms_list` calls: `juniper_static_routes`, `juniper_static_route_nexthops`, `juniper_static_route_qualified_nexthops`
- [ ] The `if routes.results:` block contains no `try:`/`except:` inside the `for route in routes.results:` loop (graceful degradation already handled by the outer try/except at L79-85 and L86-92)

</acceptance_criteria>

<verify>

```bash
uv run pytest tests/test_cms_routing_n1.py -v -k routing
```

All 5 routing tests (R1–R5) must pass. If existing unit tests fail because they mock nexthop data only in per-route responses, update those mocks to include data in the bulk responses (bulk fetches use `device=device_id`, so add nexthops to the bulk mock).

</verify>
