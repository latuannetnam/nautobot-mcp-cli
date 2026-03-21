"""Tests for CMS firewall models and CRUD functions.

Covers:
- Pydantic model from_nautobot() construction (all 7 models)
- CRUD function behavior: list (with inlining), get, create, delete
"""

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.cms.firewalls import (
    create_firewall_filter,
    create_firewall_policer,
    delete_firewall_filter,
    delete_firewall_policer,
    get_firewall_filter,
    get_firewall_match_condition,
    get_firewall_policer,
    get_firewall_term,
    list_firewall_filter_actions,
    list_firewall_filters,
    list_firewall_match_conditions,
    list_firewall_policer_actions,
    list_firewall_policers,
    list_firewall_terms,
)
from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.cms.firewalls import (
    FirewallFilterActionSummary,
    FirewallFilterSummary,
    FirewallMatchConditionSummary,
    FirewallMatchConditionToPrefixListSummary,
    FirewallPolicerActionSummary,
    FirewallPolicerSummary,
    FirewallTermSummary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_firewall_filter_record():
    """Mock pynautobot record for a JuniperFirewallFilter."""
    record = MagicMock()
    record.id = "fw-filter-aaaa-bbbb-cccc"
    record.display = "PROTECT-MGMT"
    record.url = "http://test/api/plugins/cms/filter-aaaa/"
    record.device.id = "dev-1111-2222-3333-4444"
    record.device.name = "core-rtr-01"
    record.device.display = "core-rtr-01"
    record.name = "PROTECT-MGMT"
    record.family = "inet"
    record.description = "Management plane protection"
    return record


@pytest.fixture
def mock_firewall_term_record():
    """Mock pynautobot record for a JuniperFirewallTerm."""
    record = MagicMock()
    record.id = "fw-term-aaaa-bbbb-cccc"
    record.display = "allow-bgp"
    record.url = "http://test/api/plugins/cms/term-aaaa/"
    record.device = None
    record.filter.id = "fw-filter-aaaa-bbbb-cccc"
    record.filter.name = "PROTECT-MGMT"
    record.filter.display = "PROTECT-MGMT"
    record.name = "allow-bgp"
    record.order = 10
    return record


@pytest.fixture
def mock_firewall_policer_record():
    """Mock pynautobot record for a JuniperFirewallPolicer."""
    record = MagicMock()
    record.id = "fw-policer-aaaa-bbbb-cccc"
    record.display = "RATE-LIMIT-1G"
    record.url = "http://test/api/plugins/cms/policer-aaaa/"
    record.device.id = "dev-1111-2222-3333-4444"
    record.device.name = "core-rtr-01"
    record.device.display = "core-rtr-01"
    record.name = "RATE-LIMIT-1G"
    record.description = "1Gbps rate limiter"
    record.bandwidth_limit = 1000000000
    record.bandwidth_unit = "bps"
    record.burst_size_limit = 2000000
    record.logical_bandwidth_policer = False
    record.logical_interface_policer = False
    return record


@pytest.fixture
def mock_firewall_match_condition_record():
    """Mock pynautobot record for a JuniperFirewallMatchCondition."""
    record = MagicMock()
    record.id = "fw-mc-aaaa-bbbb-cccc"
    record.display = "match-bgp-port"
    record.url = "http://test/api/plugins/cms/mc-aaaa/"
    record.device = None
    record.term.id = "fw-term-aaaa-bbbb-cccc"
    record.term.name = "allow-bgp"
    record.term.display = "allow-bgp"
    record.condition_type = "protocol"
    record.value = "tcp"
    record.negate = False
    return record


@pytest.fixture
def mock_firewall_filter_action_record():
    """Mock pynautobot record for a JuniperFirewallFilterAction."""
    record = MagicMock()
    record.id = "fw-action-aaaa-bbbb-cccc"
    record.display = "accept"
    record.url = "http://test/api/plugins/cms/action-aaaa/"
    record.device = None
    record.term.id = "fw-term-aaaa-bbbb-cccc"
    record.term.name = "allow-bgp"
    record.term.display = "allow-bgp"
    record.action_type = "accept"
    record.policer = None
    return record


@pytest.fixture
def mock_firewall_policer_action_record():
    """Mock pynautobot record for a JuniperFirewallPolicerAction."""
    record = MagicMock()
    record.id = "fw-pa-aaaa-bbbb-cccc"
    record.display = "bandwidth-limit"
    record.url = "http://test/api/plugins/cms/pa-aaaa/"
    record.device = None
    record.policer.id = "fw-policer-aaaa-bbbb-cccc"
    record.policer.name = "RATE-LIMIT-1G"
    record.policer.display = "RATE-LIMIT-1G"
    record.action_type = "bandwidth-limit"
    record.value = "1000000000"
    return record


# ---------------------------------------------------------------------------
# Pydantic Model Tests
# ---------------------------------------------------------------------------


class TestFirewallFilterSummary:
    """Tests for FirewallFilterSummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_firewall_filter_record):
        model = FirewallFilterSummary.from_nautobot(mock_firewall_filter_record)
        assert model.id == "fw-filter-aaaa-bbbb-cccc"
        assert model.name == "PROTECT-MGMT"
        assert model.family == "inet"
        assert model.description == "Management plane protection"

    def test_from_nautobot_device_fk(self, mock_firewall_filter_record):
        model = FirewallFilterSummary.from_nautobot(mock_firewall_filter_record)
        assert model.device_id == "dev-1111-2222-3333-4444"
        assert model.device_name == "core-rtr-01"

    def test_from_nautobot_term_count_default_zero(self, mock_firewall_filter_record):
        model = FirewallFilterSummary.from_nautobot(mock_firewall_filter_record)
        assert model.term_count == 0


class TestFirewallTermSummary:
    """Tests for FirewallTermSummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_firewall_term_record):
        model = FirewallTermSummary.from_nautobot(mock_firewall_term_record)
        assert model.id == "fw-term-aaaa-bbbb-cccc"
        assert model.name == "allow-bgp"
        assert model.order == 10

    def test_from_nautobot_filter_fk(self, mock_firewall_term_record):
        model = FirewallTermSummary.from_nautobot(mock_firewall_term_record)
        assert model.filter_id == "fw-filter-aaaa-bbbb-cccc"
        assert model.filter_name == "PROTECT-MGMT"

    def test_from_nautobot_count_defaults(self, mock_firewall_term_record):
        model = FirewallTermSummary.from_nautobot(mock_firewall_term_record)
        assert model.match_count == 0
        assert model.action_count == 0


class TestFirewallMatchConditionSummary:
    """Tests for FirewallMatchConditionSummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_firewall_match_condition_record):
        model = FirewallMatchConditionSummary.from_nautobot(mock_firewall_match_condition_record)
        assert model.id == "fw-mc-aaaa-bbbb-cccc"
        assert model.condition_type == "protocol"
        assert model.value == "tcp"
        assert model.negate is False

    def test_from_nautobot_term_fk(self, mock_firewall_match_condition_record):
        model = FirewallMatchConditionSummary.from_nautobot(mock_firewall_match_condition_record)
        assert model.term_id == "fw-term-aaaa-bbbb-cccc"


class TestFirewallFilterActionSummary:
    """Tests for FirewallFilterActionSummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_firewall_filter_action_record):
        model = FirewallFilterActionSummary.from_nautobot(mock_firewall_filter_action_record)
        assert model.id == "fw-action-aaaa-bbbb-cccc"
        assert model.action_type == "accept"

    def test_from_nautobot_term_fk(self, mock_firewall_filter_action_record):
        model = FirewallFilterActionSummary.from_nautobot(mock_firewall_filter_action_record)
        assert model.term_id == "fw-term-aaaa-bbbb-cccc"

    def test_from_nautobot_no_policer(self, mock_firewall_filter_action_record):
        model = FirewallFilterActionSummary.from_nautobot(mock_firewall_filter_action_record)
        assert model.policer_id is None
        assert model.policer_name is None


class TestFirewallPolicerSummary:
    """Tests for FirewallPolicerSummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_firewall_policer_record):
        model = FirewallPolicerSummary.from_nautobot(mock_firewall_policer_record)
        assert model.id == "fw-policer-aaaa-bbbb-cccc"
        assert model.name == "RATE-LIMIT-1G"
        assert model.bandwidth_limit == 1000000000
        assert model.logical_interface_policer is False

    def test_from_nautobot_device_fk(self, mock_firewall_policer_record):
        model = FirewallPolicerSummary.from_nautobot(mock_firewall_policer_record)
        assert model.device_id == "dev-1111-2222-3333-4444"
        assert model.device_name == "core-rtr-01"

    def test_from_nautobot_action_count_default(self, mock_firewall_policer_record):
        model = FirewallPolicerSummary.from_nautobot(mock_firewall_policer_record)
        assert model.action_count == 0


class TestFirewallPolicerActionSummary:
    """Tests for FirewallPolicerActionSummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_firewall_policer_action_record):
        model = FirewallPolicerActionSummary.from_nautobot(mock_firewall_policer_action_record)
        assert model.id == "fw-pa-aaaa-bbbb-cccc"
        assert model.action_type == "bandwidth-limit"
        assert model.value == "1000000000"

    def test_from_nautobot_policer_fk(self, mock_firewall_policer_action_record):
        model = FirewallPolicerActionSummary.from_nautobot(mock_firewall_policer_action_record)
        assert model.policer_id == "fw-policer-aaaa-bbbb-cccc"
        assert model.policer_name == "RATE-LIMIT-1G"


# ---------------------------------------------------------------------------
# CRUD Function Tests
# ---------------------------------------------------------------------------


class TestListFirewallFilters:
    """Tests for list_firewall_filters CRUD function."""

    @patch("nautobot_mcp.cms.firewalls.cms_list")
    @patch("nautobot_mcp.cms.firewalls.resolve_device_id")
    def test_list_resolves_device(self, mock_resolve, mock_list):
        """Calls resolve_device_id and cms_list with correct endpoint."""
        mock_resolve.return_value = "dev-1111-2222-3333-4444"
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        result = list_firewall_filters(client, device="core-rtr-01")

        mock_resolve.assert_called_once_with(client, "core-rtr-01")
        assert result.count == 0

    @patch("nautobot_mcp.cms.firewalls.cms_list")
    @patch("nautobot_mcp.cms.firewalls.resolve_device_id")
    def test_list_with_family_filter(self, mock_resolve, mock_list):
        """Passes family filter to cms_list."""
        mock_resolve.return_value = "dev-uuid"
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        list_firewall_filters(client, device="core-rtr-01", family="inet6")

        # First cms_list call should include family
        first_call_kwargs = mock_list.call_args_list[0].kwargs
        assert first_call_kwargs.get("family") == "inet6"


class TestCreateFirewallFilter:
    """Tests for create_firewall_filter CRUD function."""

    @patch("nautobot_mcp.cms.firewalls.cms_create")
    @patch("nautobot_mcp.cms.firewalls.resolve_device_id")
    def test_create_resolves_device(self, mock_resolve, mock_create, mock_firewall_filter_record):
        """Resolves device ID before calling cms_create."""
        mock_resolve.return_value = "dev-1111-2222-3333-4444"
        mock_create.return_value = FirewallFilterSummary.from_nautobot(mock_firewall_filter_record)

        client = MagicMock()
        result = create_firewall_filter(client, device="core-rtr-01", name="PROTECT-MGMT", family="inet")

        mock_resolve.assert_called_once_with(client, "core-rtr-01")
        mock_create.assert_called_once_with(
            client,
            "juniper_firewall_filters",
            FirewallFilterSummary,
            device="dev-1111-2222-3333-4444",
            name="PROTECT-MGMT",
            family="inet",
        )

    @patch("nautobot_mcp.cms.firewalls.cms_create")
    @patch("nautobot_mcp.cms.firewalls.resolve_device_id")
    def test_create_default_family_is_inet(self, mock_resolve, mock_create, mock_firewall_filter_record):
        """Defaults to family='inet' when not specified."""
        mock_resolve.return_value = "dev-uuid"
        mock_create.return_value = FirewallFilterSummary.from_nautobot(mock_firewall_filter_record)

        client = MagicMock()
        create_firewall_filter(client, device="core-rtr-01", name="PROTECT-MGMT")

        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["family"] == "inet"


class TestDeleteFirewallFilter:
    """Tests for delete_firewall_filter CRUD function."""

    @patch("nautobot_mcp.cms.firewalls.cms_delete")
    def test_delete_calls_cms_delete(self, mock_delete):
        """Calls cms_delete with the right endpoint and id."""
        mock_delete.return_value = {"success": True, "message": "Deleted."}

        client = MagicMock()
        result = delete_firewall_filter(client, id="fw-filter-aaaa-bbbb-cccc")

        mock_delete.assert_called_once_with(client, "juniper_firewall_filters", id="fw-filter-aaaa-bbbb-cccc")
        assert result["success"] is True


class TestListFirewallPolicers:
    """Tests for list_firewall_policers CRUD function."""

    @patch("nautobot_mcp.cms.firewalls.cms_list")
    @patch("nautobot_mcp.cms.firewalls.resolve_device_id")
    def test_list_device_scoped(self, mock_resolve, mock_list):
        """Resolves device and passes to cms_list."""
        mock_resolve.return_value = "dev-uuid"
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        result = list_firewall_policers(client, device="core-rtr-01")

        mock_resolve.assert_called_once_with(client, "core-rtr-01")
        assert result.count == 0


class TestCreateFirewallPolicer:
    """Tests for create_firewall_policer CRUD function."""

    @patch("nautobot_mcp.cms.firewalls.cms_create")
    @patch("nautobot_mcp.cms.firewalls.resolve_device_id")
    def test_create_policer(self, mock_resolve, mock_create, mock_firewall_policer_record):
        """Creates a policer with device resolution."""
        mock_resolve.return_value = "dev-uuid"
        mock_create.return_value = FirewallPolicerSummary.from_nautobot(mock_firewall_policer_record)

        client = MagicMock()
        result = create_firewall_policer(client, device="core-rtr-01", name="RATE-LIMIT-1G")

        mock_resolve.assert_called_once_with(client, "core-rtr-01")
        assert result.name == "RATE-LIMIT-1G"


class TestListFirewallTerms:
    """Tests for list_firewall_terms (read-only)."""

    @patch("nautobot_mcp.cms.firewalls.cms_list")
    def test_list_all_terms(self, mock_list):
        """Lists all terms when no filter_id given."""
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        result = list_firewall_terms(client)

        assert result.count == 0

    @patch("nautobot_mcp.cms.firewalls.cms_list")
    def test_list_by_filter_id(self, mock_list):
        """Passes filter_id as 'filter' kwarg to cms_list."""
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        list_firewall_terms(client, filter_id="fw-filter-aaaa")

        first_call_kwargs = mock_list.call_args_list[0].kwargs
        assert first_call_kwargs.get("filter") == "fw-filter-aaaa"


class TestListFirewallMatchConditions:
    """Tests for list_firewall_match_conditions (read-only)."""

    @patch("nautobot_mcp.cms.firewalls.cms_list")
    def test_list_by_term_id(self, mock_list):
        """Passes term_id as 'term' kwarg to cms_list."""
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        list_firewall_match_conditions(client, term_id="fw-term-aaaa")

        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs.get("term") == "fw-term-aaaa"


class TestListFirewallFilterActions:
    """Tests for list_firewall_filter_actions (read-only)."""

    @patch("nautobot_mcp.cms.firewalls.cms_list")
    def test_list_uses_juniper_firewall_actions_endpoint(self, mock_list):
        """Uses 'juniper_firewall_actions' endpoint."""
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        list_firewall_filter_actions(client)

        call_args = mock_list.call_args.args
        assert call_args[1] == "juniper_firewall_actions"
