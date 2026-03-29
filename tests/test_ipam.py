"""Unit tests for nautobot_mcp.ipam — bulk HTTP fetch operations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.ipam import _bulk_get_by_ids, get_device_ips
from nautobot_mcp.models.ipam import DeviceIPsResponse


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_mock_record(record_id: str, url: str) -> MagicMock:
    """Return a mock pynautobot Record with id and url attributes."""
    r = MagicMock()
    r.id = record_id
    r.url = url
    return r


def _make_mock_endpoint() -> MagicMock:
    """Return a mock pynautobot Endpoint with .url and .return_obj()."""
    ep = MagicMock()
    ep.url = "/api/ipam/ip_addresses/"
    ep.return_obj.side_effect = lambda d, api, e: _make_mock_record(d["id"], d.get("url", ""))
    return ep


def _make_mock_client(http_session_get: MagicMock) -> MagicMock:
    """Return a minimal mock NautobotClient with a pre-patched http_session."""
    client = MagicMock()
    client._profile.url = "http://localhost:8080"
    client.api.http_session.get = http_session_get
    return client


# ---------------------------------------------------------------------------
# TestBulkGetByIds
# ---------------------------------------------------------------------------

class TestBulkGetByIds:
    def test_empty_ids_returns_early(self):
        """Empty id list returns [] without any HTTP call."""
        http_mock = MagicMock()
        client = _make_mock_client(http_mock)
        endpoint = _make_mock_endpoint()

        result = _bulk_get_by_ids(client, endpoint, [], "id__in")

        assert result == []
        http_mock.assert_not_called()

    def test_single_page_fetches_all_results(self):
        """One HTTP call, comma-separated params, returns wrapped Records."""
        http_mock = MagicMock()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {"id": "uuid1", "url": "/api/ipam/ip_addresses/uuid1/"},
                {"id": "uuid2", "url": "/api/ipam/ip_addresses/uuid2/"},
            ],
            "next": None,
        }
        http_mock.return_value = mock_resp
        client = _make_mock_client(http_mock)
        endpoint = _make_mock_endpoint()

        result = _bulk_get_by_ids(client, endpoint, ["uuid1", "uuid2"], "id__in")

        assert len(result) == 2
        http_mock.assert_called_once()
        call_args = http_mock.call_args
        # params is a dict with comma-joined string value
        assert call_args.kwargs["params"] == {"id__in": "uuid1,uuid2"}

    def test_pagination_follows_next_link(self):
        """Pagination: two sequential calls, all results merged and wrapped."""
        page1 = MagicMock()
        page1.ok = True
        page1.raise_for_status = MagicMock()
        page1.json.return_value = {
            "results": [{"id": "uuid1", "url": "/api/ipam/ip_addresses/uuid1/"}],
            "next": "http://localhost:8080/api/ipam/ip_addresses/?page=2",
        }
        page2 = MagicMock()
        page2.ok = True
        page2.raise_for_status = MagicMock()
        page2.json.return_value = {
            "results": [{"id": "uuid2", "url": "/api/ipam/ip_addresses/uuid2/"}],
            "next": None,
        }
        http_mock = MagicMock()
        http_mock.side_effect = [page1, page2]
        client = _make_mock_client(http_mock)
        endpoint = _make_mock_endpoint()

        result = _bulk_get_by_ids(client, endpoint, ["uuid1"], "id__in")

        assert len(result) == 2
        assert http_mock.call_count == 2
        # Second call uses next_url directly with params=None
        second_call = http_mock.call_args_list[1]
        assert second_call.kwargs.get("params") is None

    def test_uses_comma_separated_format(self):
        """3 UUIDs produce a single comma-joined string param, not a list."""
        http_mock = MagicMock()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"results": [], "next": None}
        http_mock.return_value = mock_resp
        client = _make_mock_client(http_mock)
        endpoint = _make_mock_endpoint()

        _bulk_get_by_ids(client, endpoint, ["u1", "u2", "u3"], "id__in")

        params = http_mock.call_args.kwargs["params"]
        assert params == {"id__in": "u1,u2,u3"}
        assert isinstance(params["id__in"], str)  # not a list

    def test_raise_for_status_propagates_errors(self):
        """HTTP errors are raised via raise_for_status (→ NautobotAPIError)."""
        import requests

        http_mock = MagicMock()
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
        http_mock.return_value = mock_resp
        client = _make_mock_client(http_mock)
        endpoint = _make_mock_endpoint()

        with pytest.raises(requests.exceptions.HTTPError):
            _bulk_get_by_ids(client, endpoint, ["uuid1"], "id__in")


# ---------------------------------------------------------------------------
# TestGetDeviceIPs
# ---------------------------------------------------------------------------

class TestGetDeviceIPs:
    """Test get_device_ips() with mocked Pass 1 (interfaces), Pass 2 (M2M),
    and Pass 3 (IP detail).

    The key challenge: return_obj() wraps raw dicts into pynautobot Records.
    Nested attributes (m2m.ip_address.id, m2m.interface.id) must be proper
    string UUIDs so str(m.ip_address.id) produces the correct ID.
    """

    def _make_m2m_record(
        self,
        m2m_id: str,
        iface_id: str,
        ip_id: str,
    ) -> MagicMock:
        """Build a mock M2M record with properly structured nested objects."""
        ip_address = MagicMock()
        ip_address.id = ip_id  # string UUID
        interface = MagicMock()
        interface.id = iface_id  # string UUID
        record = MagicMock()
        record.id = m2m_id
        record.ip_address = ip_address
        record.interface = interface
        return record

    def _make_ip_record(
        self,
        ip_id: str,
        address: str,
        status_display: str = "Active",
    ) -> MagicMock:
        """Build a mock IP record with nested status object."""
        status = MagicMock()
        status.display = status_display
        record = MagicMock()
        record.id = ip_id
        record.address = address
        record.status = status
        return record

    def _mock_pass1(self, mock_client: MagicMock, ifaces: list[tuple[str, str]]) -> None:
        """Mock dcim.interfaces.filter returning interface records."""
        iface_records = []
        for iface_name, iface_id in ifaces:
            iface = MagicMock()
            iface.id = iface_id
            iface.name = iface_name
            iface_records.append(iface)
        mock_client.api.dcim.interfaces.filter.return_value = iter(iface_records)

    def _mock_pass2(self, mock_client: MagicMock, m2m_specs: list[tuple[str, str, str]]) -> None:
        """Mock http_session.get for ip_address_to_interface endpoint.

        m2m_specs: list of (m2m_id, iface_id, ip_id) tuples.
        return_obj is patched to return proper mock records (not raw dicts).
        """
        # Patch return_obj on the ip_address_to_interface endpoint
        mock_client.api.ipam.ip_address_to_interface.return_obj.side_effect = lambda d, api, e: (
            self._make_m2m_record(
                d.get("id", ""),
                d.get("interface", {}).get("id", ""),
                d.get("ip_address", {}).get("id", ""),
            )
        )

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {"id": m, "interface": {"id": i}, "ip_address": {"id": p}}
                for m, i, p in m2m_specs
            ],
            "next": None,
        }
        # Use side_effect for sequential calls (Pass 2 → Pass 3)
        mock_client.api.http_session.get.return_value = mock_resp

    def _mock_pass3(self, mock_client: MagicMock, ip_specs: list[tuple[str, str]]) -> None:
        """Mock http_session.get for ip_addresses endpoint (called after M2M).

        ip_specs: list of (ip_id, address) tuples.
        Appends a second response to http_session.get so it returns the Pass 3
        response on the second call.
        """
        # Patch return_obj on the ip_addresses endpoint
        mock_client.api.ipam.ip_addresses.return_obj.side_effect = lambda d, api, e: (
            self._make_ip_record(
                d.get("id", ""),
                d.get("address", ""),
                d.get("status", {}).get("display", "Unknown") if isinstance(d.get("status"), dict) else "Unknown",
            )
        )

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {"id": ip, "address": addr, "status": {"display": "Active"}}
                for ip, addr in ip_specs
            ],
            "next": None,
        }
        # Append to existing return_value (Pass 2 was set first)
        existing = mock_client.api.http_session.get.return_value
        mock_client.api.http_session.get.side_effect = [existing, mock_resp]

    def test_normal_device_with_ips(self):
        """Full pass: 2 interfaces → 3 M2M records → 3 IP records."""
        mock_client = MagicMock()
        mock_client._profile.url = "http://localhost:8080"

        # Pass 1: 2 interfaces
        self._mock_pass1(mock_client, [
            ("ge-0/0/0", "iface-uuid-1"),
            ("ge-0/0/1", "iface-uuid-2"),
        ])

        # Pass 2: 3 M2M records — (m2m_id, iface_id, ip_id)
        self._mock_pass2(mock_client, [
            ("m2m-1", "iface-uuid-1", "ip-uuid-1"),
            ("m2m-2", "iface-uuid-1", "ip-uuid-2"),
            ("m2m-3", "iface-uuid-2", "ip-uuid-3"),
        ])

        # Pass 3: 3 IP records — (ip_id, address)
        self._mock_pass3(mock_client, [
            ("ip-uuid-1", "10.0.0.1/24"),
            ("ip-uuid-2", "10.0.0.2/24"),
            ("ip-uuid-3", "10.0.0.3/24"),
        ])

        result = get_device_ips(mock_client, "HQV-PE1")

        assert result.total_ips == 3
        assert len(result.interface_ips) == 3
        assert result.unlinked_ips == []
        assert {e.address for e in result.interface_ips} == {"10.0.0.1/24", "10.0.0.2/24", "10.0.0.3/24"}

    def test_device_with_no_interfaces(self):
        """No interfaces → empty DeviceIPsResponse with total_ips=0."""
        mock_client = MagicMock()
        mock_client._profile.url = "http://localhost:8080"
        mock_client.api.dcim.interfaces.filter.return_value = iter([])

        result = get_device_ips(mock_client, "empty-device")

        assert isinstance(result, DeviceIPsResponse)
        assert result.total_ips == 0
        assert result.interface_ips == []
        assert result.unlinked_ips == []

    def test_device_with_no_ips(self):
        """Pass 2 returns empty M2M → early return, Pass 3 skipped."""
        mock_client = MagicMock()
        mock_client._profile.url = "http://localhost:8080"

        # Pass 1: 1 interface
        self._mock_pass1(mock_client, [("ge-0/0/0", "iface-uuid-1")])

        # Pass 2: empty M2M — list of tuples is empty
        self._mock_pass2(mock_client, [])

        result = get_device_ips(mock_client, "no-ips-device")

        assert isinstance(result, DeviceIPsResponse)
        assert result.total_ips == 0
        assert result.interface_ips == []
        assert result.unlinked_ips == []

    def test_device_with_more_than_500_ips(self):
        """501 interfaces → 1 bulk HTTP call to Pass 3 (no per-chunk calls)."""
        mock_client = MagicMock()
        mock_client._profile.url = "http://localhost:8080"

        # Pass 1: 501 interfaces
        iface_list = [(f"ge-0/0/{i}", f"iface-{i}") for i in range(501)]
        self._mock_pass1(mock_client, iface_list)

        # Pass 2: 501 M2M records (single page) — (m2m_id, iface_id, ip_id)
        m2m_specs = [
            (f"m2m-{i}", f"iface-{i}", f"ip-{i}")
            for i in range(501)
        ]
        self._mock_pass2(mock_client, m2m_specs)

        # Pass 3: 501 IP records (single page — no chunking fallback)
        ip_specs = [(f"ip-{i}", f"10.0.{i}.1/24") for i in range(501)]
        self._mock_pass3(mock_client, ip_specs)

        result = get_device_ips(mock_client, "large-device")

        # Verify only ONE HTTP call was made to ip_addresses (no per-chunk calls)
        ip_calls = [
            call for call in mock_client.api.http_session.get.call_args_list
            if "ip_addresses" in str(call)
        ]
        assert len(ip_calls) == 1, f"Expected 1 Pass 3 call, got {len(ip_calls)}"
        assert result.total_ips == 501

    def test_partial_failure_stale_ips_in_unlinked_ips(self):
        """M2M has 3 IPs, Pass 3 returns only 2 → 1 stale IP in unlinked_ips."""
        mock_client = MagicMock()
        mock_client._profile.url = "http://localhost:8080"

        # Pass 1: 1 interface
        self._mock_pass1(mock_client, [("ge-0/0/0", "iface-uuid-1")])

        # Pass 2: 3 M2M records (uuid1, uuid2, uuid3)
        self._mock_pass2(mock_client, [
            ("m2m-1", "iface-uuid-1", "uuid1"),
            ("m2m-2", "iface-uuid-1", "uuid2"),
            ("m2m-3", "iface-uuid-1", "uuid3"),
        ])

        # Pass 3: only uuid1 and uuid3 — uuid2 is missing (stale/deleted)
        self._mock_pass3(mock_client, [
            ("uuid1", "10.0.0.1/24"),
            ("uuid3", "10.0.0.3/24"),
        ])

        result = get_device_ips(mock_client, "stale-device")

        # uuid2 should be in unlinked_ips as a stub
        assert len(result.unlinked_ips) == 1
        assert result.unlinked_ips[0].id == "uuid2"
        assert result.unlinked_ips[0].address == "<deleted>"

        # Only uuid1 and uuid3 in interface_ips
        assert len(result.interface_ips) == 2
        assert {e.ip_id for e in result.interface_ips} == {"uuid1", "uuid3"}

    def test_http_error_propagates(self):
        """HTTPError from http_session.get raises NautobotAPIError."""
        import requests

        mock_client = MagicMock()
        mock_client._profile.url = "http://localhost:8080"

        # Pass 1: 1 interface
        self._mock_pass1(mock_client, [("ge-0/0/0", "iface-uuid-1")])

        # Pass 2: error on M2M request
        error_resp = MagicMock()
        error_resp.ok = False
        error_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
        mock_client.api.http_session.get.return_value = error_resp

        with pytest.raises(requests.exceptions.HTTPError):
            get_device_ips(mock_client, "error-device")
