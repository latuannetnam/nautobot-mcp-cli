"""Tests for interface_detail N+1 fix — bulk prefetch invariants.

Verifies:
- Exactly 3 bulk cms_list calls (CQP-01)
- list_interface_families never called per-unit (CQP-01)
- list_vrrp_groups never called per-family (CQP-01)
- Family prefetch failure hard-fails (D-03)
- VRRP prefetch failure graceful degradation (D-04 / CQP-05)
"""

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.cms.composites import InterfaceDetailResponse


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


# 3 units × 2 families (6 total), no VRRP — for multi-unit scenarios
_UNITS = [
    MagicMock(id=f"unit-{i}", model_dump=MagicMock(return_value={"id": f"unit-{i}", "interface_name": f"ge-0/0/{i}"}))
    for i in range(3)
]

_FAMILIES = [
    MagicMock(id=f"fam-{i}", unit_id=f"unit-{i // 2}", model_dump=MagicMock(return_value={"id": f"fam-{i}", "family_type": "inet"}))
    for i in range(6)
]


# ---------------------------------------------------------------------------
# Test 1: Exactly 3 bulk cms_list calls (CQP-01)
# ---------------------------------------------------------------------------


def test_interface_detail_bulk_prefetch_exactly_3_calls():
    """CQP-01: get_interface_detail makes exactly 3 bulk cms_list calls regardless of unit count.

    3 units × 2 families each. Expected call sequence:
    1. list_interface_units(device=..., limit=0)  → units  (patched separately)
    2. cms_list(juniper_interface_families, ...)  → all families
    3. cms_list(juniper_interface_vrrp_groups, ...)  → all VRRP groups
    """
    client = _mock_client()
    units = _UNITS
    families = _FAMILIES

    # cms_list handles families + VRRP only; units come from list_interface_units
    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "interface_families" in endpoint:
            return ListResponse(count=6, results=families)
        if "vrrp_groups" in endpoint:
            return ListResponse(count=0, results=[])
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    # Import and patch inside the with block so module refs are live at patch time
    with patch("nautobot_mcp.cms.interfaces.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(*units)), \
         patch("nautobot_mcp.cms.interfaces.cms_list", side_effect=cms_list_side_effect) as mock_cms, \
         patch("nautobot_mcp.cms.interfaces.list_interface_families") as mock_fams, \
         patch("nautobot_mcp.cms.interfaces.list_vrrp_groups") as mock_vrrp:
        from nautobot_mcp.cms.interfaces import get_interface_detail
        result, warnings = get_interface_detail(client, device="edge-01")

        # Assertions
        assert isinstance(result, InterfaceDetailResponse)
        assert result.device_name == "edge-01"
        assert result.total_units == 3
        assert len(result.units) == 3

        # 2 cms_list calls: families + VRRP (units handled by list_interface_units)
        assert mock_cms.call_count == 2

        # 0 calls to per-unit/per-family functions (N+1 eliminated)
        mock_fams.assert_not_called()
        mock_vrrp.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: list_interface_families never called per-unit (CQP-01)
# ---------------------------------------------------------------------------


def test_interface_detail_no_per_unit_family_calls():
    """CQP-01: list_interface_families is never called per-unit in get_interface_detail.

    The function should fetch all families in one bulk call, then look up by unit_id.
    If list_interface_families is called, this test fails — proving the N+1 is gone.
    """
    from nautobot_mcp.cms.interfaces import get_interface_detail
    from nautobot_mcp.cms import interfaces as if_module

    client = _mock_client()
    units = _UNITS[:2]
    families = _FAMILIES[:4]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "interface_families" in endpoint:
            return ListResponse(count=4, results=families)
        return ListResponse(count=0, results=[])

    # Patch list_interface_families to raise if called (failsafe — proves N+1 is gone)
    with patch("nautobot_mcp.cms.interfaces.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(*units)), \
         patch("nautobot_mcp.cms.interfaces.cms_list", side_effect=cms_list_side_effect), \
         patch.object(if_module, "list_interface_families", side_effect=AssertionError("N+1! list_interface_families called per-unit")):
        result, warnings = get_interface_detail(client, device="edge-01")

    # If we reach here, list_interface_families was NOT called (test passes)
    assert isinstance(result, InterfaceDetailResponse)
    assert result.total_units == 2


# ---------------------------------------------------------------------------
# Test 3: list_vrrp_groups never called per-family (CQP-01)
# ---------------------------------------------------------------------------


def test_interface_detail_no_per_family_vrrp_calls():
    """CQP-01: list_vrrp_groups is never called per-family in get_interface_detail.

    VRRP groups come from the prefetched vrrp_by_family map. No per-family HTTP calls.
    """
    from nautobot_mcp.cms.interfaces import get_interface_detail
    from nautobot_mcp.cms import interfaces as if_module

    client = _mock_client()
    units = _UNITS[:1]
    families = _FAMILIES[:2]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "interface_families" in endpoint:
            return ListResponse(count=2, results=families)
        return ListResponse(count=0, results=[])

    with patch("nautobot_mcp.cms.interfaces.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(*units)), \
         patch("nautobot_mcp.cms.interfaces.cms_list", side_effect=cms_list_side_effect), \
         patch.object(if_module, "list_vrrp_groups", side_effect=AssertionError("N+1! list_vrrp_groups called per-family")):
        result, warnings = get_interface_detail(client, device="edge-01")

    assert isinstance(result, InterfaceDetailResponse)
    assert result.total_units == 1
    # If we reach here, list_vrrp_groups was NOT called (test passes)


# ---------------------------------------------------------------------------
# Test 4: Family prefetch failure → hard-fail (D-03)
# ---------------------------------------------------------------------------


def test_interface_detail_family_prefetch_failure_hard_fail():
    """D-03: Bulk family prefetch failure propagates as exception (hard-fail).

    Family data is critical for detail=True enrichment. No WarningCollector degradation.
    """
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()
    unit = _UNITS[0]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "interface_families" in endpoint:
            raise RuntimeError("Family endpoint 503")
        # VRRP never reached
        return ListResponse(count=0, results=[])

    with patch("nautobot_mcp.cms.interfaces.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(unit)), \
         patch("nautobot_mcp.cms.interfaces.cms_list", side_effect=cms_list_side_effect):
        with pytest.raises(RuntimeError, match="Family endpoint 503"):
            get_interface_detail(client, device="edge-01")

    # No units processed — result never constructed


# ---------------------------------------------------------------------------
# Test 5: VRRP prefetch failure → graceful degradation with WarningCollector (D-04 / CQP-05)
# ---------------------------------------------------------------------------


def test_interface_detail_vrrp_prefetch_failure_graceful():
    """D-04 / CQP-05: Bulk VRRP prefetch failure → WarningCollector warning, empty vrrp_groups.

    VRRP is non-critical enrichment. Failure adds warning and returns [] per family.
    The response is still valid — just with vrrp_group_count=0 everywhere.
    """
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()
    unit = _UNITS[0]
    fam = _FAMILIES[0]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "interface_families" in endpoint:
            return ListResponse(count=1, results=[fam])
        if "vrrp_groups" in endpoint:
            raise RuntimeError("VRRP endpoint timeout")
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.interfaces.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(unit)), \
         patch("nautobot_mcp.cms.interfaces.cms_list", side_effect=cms_list_side_effect):
        result, warnings = get_interface_detail(client, device="edge-01")

    # Response is valid despite VRRP failure
    assert isinstance(result, InterfaceDetailResponse)
    assert result.device_name == "edge-01"
    assert result.total_units == 1
    assert result.units[0]["families"][0]["vrrp_group_count"] == 0
    assert result.units[0]["families"][0]["vrrp_groups"] == []

    # Warning recorded (CQP-05)
    assert len(warnings) == 1
    assert warnings[0]["operation"] == "bulk_vrrp_fetch"
    assert "VRRP endpoint timeout" in warnings[0]["error"]


# ---------------------------------------------------------------------------
# Test 6: VRRP data from prefetched map (detail mode) — CQP-01
# ---------------------------------------------------------------------------


def test_interface_detail_vrrp_enriched_from_prefetch_map():
    """VRRP groups are correctly resolved from the prefetched vrrp_by_family map.

    One family has 2 VRRP groups, another has 0. Verify correct counts.
    """
    from nautobot_mcp.cms.interfaces import get_interface_detail

    client = _mock_client()
    unit = _UNITS[0]
    fam_with_vrrp = MagicMock(id="fam-vrrp", unit_id="unit-0", model_dump=MagicMock(return_value={"id": "fam-vrrp", "family_type": "inet"}))
    fam_no_vrrp = MagicMock(id="fam-novrrp", unit_id="unit-0", model_dump=MagicMock(return_value={"id": "fam-novrrp", "family_type": "inet6"}))

    vrrp_1 = MagicMock(id="vrrp-1", model_dump=MagicMock(return_value={"id": "vrrp-1", "group_number": 1}))
    vrrp_2 = MagicMock(id="vrrp-2", model_dump=MagicMock(return_value={"id": "vrrp-2", "group_number": 2}))

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "interface_families" in endpoint:
            return ListResponse(count=2, results=[fam_with_vrrp, fam_no_vrrp])
        if "vrrp_groups" in endpoint:
            # Both VRRP groups belong to fam_with_vrrp (family_id = fam_with_vrrp.id)
            vrrp_1.family_id = fam_with_vrrp.id
            vrrp_2.family_id = fam_with_vrrp.id
            return ListResponse(count=2, results=[vrrp_1, vrrp_2])
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.interfaces.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(unit)), \
         patch("nautobot_mcp.cms.interfaces.cms_list", side_effect=cms_list_side_effect):
        result, warnings = get_interface_detail(client, device="edge-01")

    assert len(warnings) == 0

    # fam_with_vrrp should have 2 VRRP groups
    fam_ids = {f["id"]: f for f in result.units[0]["families"]}
    assert fam_ids["fam-vrrp"]["vrrp_group_count"] == 2
    assert len(fam_ids["fam-vrrp"]["vrrp_groups"]) == 2

    # fam_no_vrrp should have 0 VRRP groups
    assert fam_ids["fam-novrrp"]["vrrp_group_count"] == 0
    assert fam_ids["fam-novrrp"]["vrrp_groups"] == []


# ---------------------------------------------------------------------------
# Test 7: Summary mode (detail=False) also benefits from VRRP prefetch — CQP-01
# ---------------------------------------------------------------------------


def test_interface_detail_summary_mode_no_vrrp_calls():
    """get_interface_detail(detail=False) also uses prefetched VRRP map, no per-family calls.

    Even in summary mode, VRRP count is computed from the prefetched map, not via HTTP.
    """
    from nautobot_mcp.cms.interfaces import get_interface_detail
    from nautobot_mcp.cms import interfaces as if_module

    client = _mock_client()
    unit = _UNITS[0]
    fam = _FAMILIES[0]
    vrrp = MagicMock(id="vrrp-1", model_dump=MagicMock(return_value={"id": "vrrp-1", "group_number": 1}))
    vrrp.family_id = fam.id

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "interface_families" in endpoint:
            return ListResponse(count=1, results=[fam])
        if "vrrp_groups" in endpoint:
            return ListResponse(count=1, results=[vrrp])
        raise ValueError(f"Unexpected endpoint: {endpoint}")

    with patch("nautobot_mcp.cms.interfaces.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(unit)), \
         patch("nautobot_mcp.cms.interfaces.cms_list", side_effect=cms_list_side_effect), \
         patch.object(if_module, "list_vrrp_groups", side_effect=AssertionError("N+1! list_vrrp_groups called in summary mode")):
        result, warnings = get_interface_detail(client, device="edge-01", detail=False)

    # Summary mode: families stripped, but VRRP count present
    assert isinstance(result, InterfaceDetailResponse)
    assert result.units[0]["families"] == []  # stripped
    assert result.units[0]["vrrp_group_count"] == 1  # from prefetched map
    assert len(warnings) == 0


# ---------------------------------------------------------------------------
# Test 8: list_interface_families NOT called in summary mode either (CQP-01)
# ---------------------------------------------------------------------------


def test_interface_detail_summary_mode_no_family_calls():
    """get_interface_detail(detail=False) also uses bulk family prefetch, no per-unit calls."""
    from nautobot_mcp.cms.interfaces import get_interface_detail
    from nautobot_mcp.cms import interfaces as if_module

    client = _mock_client()
    unit = _UNITS[0]
    fam = _FAMILIES[0]

    def cms_list_side_effect(client, endpoint, model, device=None, limit=0, **kwargs):
        if "interface_families" in endpoint:
            return ListResponse(count=1, results=[fam])
        return ListResponse(count=0, results=[])

    with patch("nautobot_mcp.cms.interfaces.resolve_device_id", return_value="device-uuid-1"), \
         patch("nautobot_mcp.cms.interfaces.list_interface_units", return_value=_mock_list_response(unit)), \
         patch("nautobot_mcp.cms.interfaces.cms_list", side_effect=cms_list_side_effect), \
         patch.object(if_module, "list_interface_families", side_effect=AssertionError("N+1! list_interface_families called per-unit in summary mode")):
        result, warnings = get_interface_detail(client, device="edge-01", detail=False)

    assert isinstance(result, InterfaceDetailResponse)
    assert result.units[0]["family_count"] == 1
