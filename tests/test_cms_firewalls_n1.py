"""Tests for firewall_summary N+1 fix — bulk prefetch invariants.

Verifies:
- Exactly 2 bulk cms_list calls (bulk terms + bulk actions prefetch) (CQP-02)
- list_firewall_terms never called per-filter (CQP-02)
- list_firewall_policer_actions never called per-policer (CQP-02)
- Terms prefetch failure graceful degradation with WarningCollector (CQP-05)
- Actions prefetch failure graceful degradation with WarningCollector (CQP-05)
- Terms/actions correctly enriched from prefetch maps (CQP-02)
- detail=False path unaffected (no prefetch block entered) (CQP-02)
"""

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.cms.composites import FirewallSummaryResponse


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _mock_client():
    return MagicMock()


def _mock_list_response(*items):
    """Return a mock ListResponse with items as results."""
    resp = MagicMock()
    resp.results = list(items)
    resp.count = len(items)
    return resp


def _mock_filter(idx, term_count=0):
    """Return a mock FirewallFilterSummary with term_count."""
    f = MagicMock()
    f.id = idx if isinstance(idx, str) else f"filter-{idx}"
    f.model_dump = MagicMock(return_value={
        "id": f.id,
        "name": f.id,
        "term_count": term_count,
    })
    f.term_count = term_count
    return f


def _mock_policer(idx, action_count=0):
    """Return a mock FirewallPolicerSummary with action_count."""
    p = MagicMock()
    p.id = idx if isinstance(idx, str) else f"policer-{idx}"
    p.model_dump = MagicMock(return_value={
        "id": p.id,
        "name": p.id,
        "action_count": action_count,
    })
    p.action_count = action_count
    return p


# ---------------------------------------------------------------------------
# Test 1: Exactly 2 bulk cms_list calls (CQP-02)
# ---------------------------------------------------------------------------


def test_firewall_summary_bulk_prefetch_exactly_2_calls():
    """CQP-02: get_device_firewall_summary(detail=True) makes exactly 2 bulk cms_list calls.

    5 filters × 10 terms each = 50 total terms
    3 policers × 5 actions each = 15 total actions

    Expected call sequence:
    1. cms_list(juniper_firewall_terms, device=..., limit=0)  → all terms
    2. cms_list(juniper_firewall_policer_actions, device=..., limit=0)  → all actions

    list_firewall_filters and list_firewall_policers are patched as unit returns
    and do NOT go through cms_list in this test.
    """
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary

    client = _mock_client()

    # 5 filters × 10 terms each
    filters = [_mock_filter(i, term_count=10) for i in range(5)]
    # 3 policers × 5 actions each
    policers = [_mock_policer(i, action_count=5) for i in range(3)]

    # Build bulk term response
    terms = []
    for f_idx, f in enumerate(filters):
        for t_idx in range(10):
            t = MagicMock()
            t.id = f"term-{f_idx}-{t_idx}"
            t.filter_id = f.id
            t.model_dump = MagicMock(return_value={
                "id": f"term-{f_idx}-{t_idx}",
                "filter_id": f.id,
                "name": f"term-{f_idx}-{t_idx}",
            })
            terms.append(t)

    # Build bulk action response
    actions = []
    for p_idx, p in enumerate(policers):
        for a_idx in range(5):
            a = MagicMock()
            a.id = f"action-{p_idx}-{a_idx}"
            a.policer_id = p.id
            a.model_dump = MagicMock(return_value={
                "id": f"action-{p_idx}-{a_idx}",
                "policer_id": p.id,
            })
            actions.append(a)

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "firewall_terms" in endpoint:
            return ListResponse(count=50, results=terms)
        if "firewall_policer_actions" in endpoint:
            return ListResponse(count=15, results=actions)
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.firewalls.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=_mock_list_response(*filters)), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(*policers)), \
         patch("nautobot_mcp.cms.firewalls.cms_list", side_effect=cms_list_side_effect) as mock_cms:
        result, warnings = get_device_firewall_summary(client, device="edge-01", detail=True)

    # Assertions
    assert isinstance(result, FirewallSummaryResponse)
    assert result.device_name == "edge-01"
    assert result.total_filters == 5
    assert result.total_policers == 3

    # Exactly 2 cms_list calls: bulk terms + bulk actions
    assert mock_cms.call_count == 2

    # No per-filter or per-policer helper calls
    # (these are covered by dedicated tests below)


# ---------------------------------------------------------------------------
# Test 2: list_firewall_terms never called per-filter (CQP-02)
# ---------------------------------------------------------------------------


def test_firewall_summary_no_per_filter_terms_calls():
    """CQP-02: list_firewall_terms is never called per-filter in detail=True.

    The function should fetch all terms in one bulk cms_list call, then look up
    by filter_id. If list_firewall_terms is called, AssertionError is raised
    and the test fails — proving the N+1 is gone.
    """
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary
    from nautobot_mcp.cms import firewalls as fw_module

    client = _mock_client()

    # 3 filters, bulk terms response has 30 total (10 per filter)
    filters = [_mock_filter(i, term_count=10) for i in range(3)]
    policers = [_mock_policer(0, action_count=2)]

    terms = []
    for f in filters:
        for t_idx in range(10):
            t = MagicMock()
            t.id = f"term-{f.id}-{t_idx}"
            t.filter_id = f.id
            t.model_dump = MagicMock(return_value={"id": t.id, "filter_id": f.id})
            terms.append(t)

    actions = [MagicMock(id="action-0-0", policer_id="policer-0",
                         model_dump=MagicMock(return_value={"id": "action-0-0", "policer_id": "policer-0"})),
               MagicMock(id="action-0-1", policer_id="policer-0",
                         model_dump=MagicMock(return_value={"id": "action-0-1", "policer_id": "policer-0"}))]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "firewall_terms" in endpoint:
            return ListResponse(count=30, results=terms)
        if "firewall_policer_actions" in endpoint:
            return ListResponse(count=2, results=actions)
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    # Patch list_firewall_terms to raise if called (failsafe — proves N+1 is gone)
    with patch("nautobot_mcp.cms.firewalls.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=_mock_list_response(*filters)), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(*policers)), \
         patch("nautobot_mcp.cms.firewalls.cms_list", side_effect=cms_list_side_effect), \
         patch.object(fw_module, "list_firewall_terms",
                      side_effect=AssertionError("N+1! list_firewall_terms called per-filter")):
        result, warnings = get_device_firewall_summary(client, device="edge-01", detail=True)

    # If we reach here, list_firewall_terms was NOT called (N+1 eliminated)
    assert isinstance(result, FirewallSummaryResponse)
    assert result.total_filters == 3
    assert result.total_policers == 1


# ---------------------------------------------------------------------------
# Test 3: list_firewall_policer_actions never called per-policer (CQP-02)
# ---------------------------------------------------------------------------


def test_firewall_summary_no_per_policer_actions_calls():
    """CQP-02: list_firewall_policer_actions is never called per-policer in detail=True.

    The function should fetch all actions in one bulk cms_list call, then look up
    by policer_id. If list_firewall_policer_actions is called, AssertionError is
    raised and the test fails — proving the N+1 is gone.
    """
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary
    from nautobot_mcp.cms import firewalls as fw_module

    client = _mock_client()

    filters = [_mock_filter(0, term_count=2)]
    # 4 policers, bulk actions response has 20 total (5 per policer)
    policers = [_mock_policer(i, action_count=5) for i in range(4)]

    terms = [MagicMock(id="term-0-0", filter_id="filter-0",
                       model_dump=MagicMock(return_value={"id": "term-0-0", "filter_id": "filter-0"})),
             MagicMock(id="term-0-1", filter_id="filter-0",
                       model_dump=MagicMock(return_value={"id": "term-0-1", "filter_id": "filter-0"}))]

    actions = []
    for p in policers:
        for a_idx in range(5):
            a = MagicMock()
            a.id = f"action-{p.id}-{a_idx}"
            a.policer_id = p.id
            a.model_dump = MagicMock(return_value={"id": a.id, "policer_id": p.id})
            actions.append(a)

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "firewall_terms" in endpoint:
            return ListResponse(count=2, results=terms)
        if "firewall_policer_actions" in endpoint:
            return ListResponse(count=20, results=actions)
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    # Patch list_firewall_policer_actions to raise if called (failsafe — proves N+1 is gone)
    with patch("nautobot_mcp.cms.firewalls.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=_mock_list_response(*filters)), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(*policers)), \
         patch("nautobot_mcp.cms.firewalls.cms_list", side_effect=cms_list_side_effect), \
         patch.object(fw_module, "list_firewall_policer_actions",
                      side_effect=AssertionError("N+1! list_firewall_policer_actions called per-policer")):
        result, warnings = get_device_firewall_summary(client, device="edge-01", detail=True)

    # If we reach here, list_firewall_policer_actions was NOT called (N+1 eliminated)
    assert isinstance(result, FirewallSummaryResponse)
    assert result.total_filters == 1
    assert result.total_policers == 4


# ---------------------------------------------------------------------------
# Test 4: Terms prefetch failure → graceful degradation (CQP-05)
# ---------------------------------------------------------------------------


def test_firewall_summary_terms_prefetch_failure_graceful():
    """CQP-05: Bulk terms prefetch failure → WarningCollector warning, empty terms.

    Terms are non-critical enrichment in detail mode. Failure adds warning and
    returns [] per filter. The response is still valid.
    """
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary

    client = _mock_client()

    filters = [_mock_filter(0, term_count=5), _mock_filter(1, term_count=3)]
    policers = [_mock_policer(0, action_count=2)]

    actions = [MagicMock(id="action-0-0", policer_id="policer-0",
                         model_dump=MagicMock(return_value={"id": "action-0-0", "policer_id": "policer-0"})),
               MagicMock(id="action-0-1", policer_id="policer-0",
                         model_dump=MagicMock(return_value={"id": "action-0-1", "policer_id": "policer-0"}))]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "firewall_terms" in endpoint:
            raise RuntimeError("Terms endpoint 503")
        if "firewall_policer_actions" in endpoint:
            return ListResponse(count=2, results=actions)
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.firewalls.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=_mock_list_response(*filters)), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(*policers)), \
         patch("nautobot_mcp.cms.firewalls.cms_list", side_effect=cms_list_side_effect):
        result, warnings = get_device_firewall_summary(client, device="edge-01", detail=True)

    # Response is valid despite terms failure
    assert isinstance(result, FirewallSummaryResponse)
    assert result.device_name == "edge-01"
    assert result.total_filters == 2
    assert result.total_policers == 1

    # All filters should have empty terms (graceful degradation)
    for f in result.filters:
        assert f["terms"] == []

    # Warning recorded (CQP-05)
    assert len(warnings) == 1
    assert warnings[0]["operation"] == "bulk_terms_fetch"
    assert "Terms endpoint 503" in warnings[0]["error"]


# ---------------------------------------------------------------------------
# Test 5: Actions prefetch failure → graceful degradation (CQP-05)
# ---------------------------------------------------------------------------


def test_firewall_summary_actions_prefetch_failure_graceful():
    """CQP-05: Bulk actions prefetch failure → WarningCollector warning, empty actions.

    Actions are non-critical enrichment in detail mode. Failure adds warning and
    returns [] per policer. The response is still valid.
    """
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary

    client = _mock_client()

    filters = [_mock_filter(0, term_count=2)]
    policers = [_mock_policer(0, action_count=4), _mock_policer(1, action_count=2)]

    terms = [MagicMock(id="term-0-0", filter_id="filter-0",
                       model_dump=MagicMock(return_value={"id": "term-0-0", "filter_id": "filter-0"})),
             MagicMock(id="term-0-1", filter_id="filter-0",
                       model_dump=MagicMock(return_value={"id": "term-0-1", "filter_id": "filter-0"}))]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "firewall_terms" in endpoint:
            return ListResponse(count=2, results=terms)
        if "firewall_policer_actions" in endpoint:
            raise RuntimeError("Actions endpoint timeout")
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.firewalls.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=_mock_list_response(*filters)), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(*policers)), \
         patch("nautobot_mcp.cms.firewalls.cms_list", side_effect=cms_list_side_effect):
        result, warnings = get_device_firewall_summary(client, device="edge-01", detail=True)

    # Response is valid despite actions failure
    assert isinstance(result, FirewallSummaryResponse)
    assert result.device_name == "edge-01"
    assert result.total_filters == 1
    assert result.total_policers == 2

    # All policers should have empty actions (graceful degradation)
    for p in result.policers:
        assert p["actions"] == []

    # Warning recorded (CQP-05)
    assert len(warnings) == 1
    assert warnings[0]["operation"] == "bulk_actions_fetch"
    assert "Actions endpoint timeout" in warnings[0]["error"]


# ---------------------------------------------------------------------------
# Test 6: Terms correctly enriched from prefetched map (CQP-02)
# ---------------------------------------------------------------------------


def test_firewall_summary_terms_enriched_from_prefetch_map():
    """Terms are correctly resolved from the prefetched terms_by_filter map.

    filter-A has 3 terms, filter-B has 0 terms. Verify correct term_count and
    inlined terms list in the response.
    """
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary

    client = _mock_client()

    filter_a = _mock_filter("filter-A", term_count=3)
    filter_b = _mock_filter("filter-B", term_count=0)
    filters = [filter_a, filter_b]

    policers = [_mock_policer("policer-X", action_count=1)]
    actions = [MagicMock(id="action-X-0", policer_id="policer-X",
                         model_dump=MagicMock(return_value={"id": "action-X-0", "policer_id": "policer-X"}))]

    # 3 terms all belonging to filter-A
    terms = []
    for t_idx in range(3):
        t = MagicMock()
        t.id = f"term-A-{t_idx}"
        t.filter_id = "filter-A"
        t.model_dump = MagicMock(return_value={"id": t.id, "filter_id": "filter-A"})
        terms.append(t)

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "firewall_terms" in endpoint:
            return ListResponse(count=3, results=terms)
        if "firewall_policer_actions" in endpoint:
            return ListResponse(count=1, results=actions)
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.firewalls.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=_mock_list_response(*filters)), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(*policers)), \
         patch("nautobot_mcp.cms.firewalls.cms_list", side_effect=cms_list_side_effect):
        result, warnings = get_device_firewall_summary(client, device="edge-01", detail=True)

    assert len(warnings) == 0

    filter_ids = {f["id"] for f in result.filters}
    assert "filter-A" in filter_ids
    assert "filter-B" in filter_ids

    filter_a_result = next(f for f in result.filters if f["id"] == "filter-A")
    assert filter_a_result["term_count"] == 3
    assert len(filter_a_result["terms"]) == 3

    filter_b_result = next(f for f in result.filters if f["id"] == "filter-B")
    assert filter_b_result["term_count"] == 0
    assert filter_b_result["terms"] == []


# ---------------------------------------------------------------------------
# Test 7: Actions correctly enriched from prefetched map (CQP-02)
# ---------------------------------------------------------------------------


def test_firewall_summary_actions_enriched_from_prefetch_map():
    """Actions are correctly resolved from the prefetched actions_by_policer map.

    policer-X has 2 actions, policer-Y has 0 actions. Verify correct action_count
    and inlined actions list in the response.
    """
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary

    client = _mock_client()

    filters = [_mock_filter("filter-1", term_count=1)]
    policer_x = _mock_policer("policer-X", action_count=2)
    policer_y = _mock_policer("policer-Y", action_count=0)
    policers = [policer_x, policer_y]

    terms = [MagicMock(id="term-1-0", filter_id="filter-1",
                       model_dump=MagicMock(return_value={"id": "term-1-0", "filter_id": "filter-1"}))]

    # 2 actions both belonging to policer-X
    actions = []
    for a_idx in range(2):
        a = MagicMock()
        a.id = f"action-X-{a_idx}"
        a.policer_id = "policer-X"
        a.model_dump = MagicMock(return_value={"id": a.id, "policer_id": "policer-X"})
        actions.append(a)

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "firewall_terms" in endpoint:
            return ListResponse(count=1, results=terms)
        if "firewall_policer_actions" in endpoint:
            return ListResponse(count=2, results=actions)
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.firewalls.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=_mock_list_response(*filters)), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(*policers)), \
         patch("nautobot_mcp.cms.firewalls.cms_list", side_effect=cms_list_side_effect):
        result, warnings = get_device_firewall_summary(client, device="edge-01", detail=True)

    assert len(warnings) == 0

    policer_ids = {p["id"] for p in result.policers}
    assert "policer-X" in policer_ids
    assert "policer-Y" in policer_ids

    policer_x_result = next(p for p in result.policers if p["id"] == "policer-X")
    assert policer_x_result["action_count"] == 2
    assert len(policer_x_result["actions"]) == 2

    policer_y_result = next(p for p in result.policers if p["id"] == "policer-Y")
    assert policer_y_result["action_count"] == 0
    assert policer_y_result["actions"] == []


# ---------------------------------------------------------------------------
# Test 8: detail=False path unaffected (CQP-02)
# ---------------------------------------------------------------------------


def test_firewall_summary_detail_false_unaffected():
    """CQP-02: get_device_firewall_summary(detail=False) makes no cms_list calls.

    The prefetch block is inside `if detail:` — in detail=False mode, only
    list_firewall_filters and list_firewall_policers are called. cms_list
    should never be invoked.
    """
    from nautobot_mcp.cms.firewalls import get_device_firewall_summary

    client = _mock_client()

    filters = [_mock_filter("filter-1", term_count=0)]
    policers = [_mock_policer("policer-1", action_count=0)]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        raise AssertionError("N+1! cms_list called in detail=False path")

    with patch("nautobot_mcp.cms.firewalls.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_filters", return_value=_mock_list_response(*filters)), \
         patch("nautobot_mcp.cms.firewalls.list_firewall_policers", return_value=_mock_list_response(*policers)), \
         patch("nautobot_mcp.cms.firewalls.cms_list", side_effect=cms_list_side_effect) as mock_cms:
        result, warnings = get_device_firewall_summary(client, device="edge-01", detail=False)

    # Response is valid — built from co-primary filter/policer list calls
    assert isinstance(result, FirewallSummaryResponse)
    assert result.device_name == "edge-01"
    assert result.total_filters == 1
    assert result.total_policers == 1

    # No cms_list calls in detail=False mode
    mock_cms.assert_not_called()
