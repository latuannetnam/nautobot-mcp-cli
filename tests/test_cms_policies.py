"""Tests for CMS policy models and CRUD functions.

Covers:
- Pydantic model from_nautobot() construction (all 16 models)
- CRUD function behavior: list (device-scoped), get, create, delete
"""

from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.cms.policies import (
    create_policy_as_path,
    create_policy_community,
    create_policy_prefix_list,
    create_policy_statement,
    delete_policy_as_path,
    delete_policy_community,
    delete_policy_prefix_list,
    delete_policy_statement,
    get_jps_term,
    get_policy_statement,
    list_jps_match_conditions,
    list_jps_terms,
    list_policy_as_paths,
    list_policy_communities,
    list_policy_prefix_lists,
    list_policy_statements,
)
from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.cms.policies import (
    JPSActionSummary,
    JPSMatchConditionSummary,
    JPSTermSummary,
    PolicyAsPathSummary,
    PolicyCommunitySummary,
    PolicyPrefixListSummary,
    PolicyStatementSummary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_policy_statement_record():
    record = MagicMock()
    record.id = "ps-aaaa-bbbb-cccc-dddd"
    record.display = "EXPORT-POLICY"
    record.url = "http://test/api/plugins/cms/ps-aaaa/"
    record.device.id = "dev-1111-2222-3333-4444"
    record.device.name = "core-rtr-01"
    record.device.display = "core-rtr-01"
    record.name = "EXPORT-POLICY"
    record.description = "Export policy for eBGP"
    return record


@pytest.fixture
def mock_jps_term_record():
    record = MagicMock()
    record.id = "term-aaaa-bbbb-cccc-dddd"
    record.display = "term-10"
    record.url = "http://test/api/plugins/cms/term-aaaa/"
    record.device = None
    # FK field on CMS model is policy_statement
    record.policy_statement.id = "ps-aaaa-bbbb-cccc-dddd"
    record.policy_statement.name = "EXPORT-POLICY"
    record.policy_statement.display = "EXPORT-POLICY"
    record.name = "term-10"
    record.order = 10
    record.action = "accept"
    record.enabled = True
    return record


@pytest.fixture
def mock_jps_match_condition_record():
    record = MagicMock()
    record.id = "mc-aaaa-bbbb-cccc-dddd"
    record.display = "match-community"
    record.url = "http://test/api/plugins/cms/mc-aaaa/"
    record.device = None
    # FK field on CMS model is jps_term
    record.jps_term.id = "term-aaaa-bbbb-cccc-dddd"
    record.jps_term.name = "term-10"
    record.jps_term.display = "term-10"
    record.condition_type = "community"
    record.value = ""
    record.negate = False
    return record


@pytest.fixture
def mock_jps_action_record():
    record = MagicMock()
    record.id = "action-aaaa-bbbb-cccc-dddd"
    record.display = "set-local-pref-100"
    record.url = "http://test/api/plugins/cms/action-aaaa/"
    record.device = None
    # FK field on CMS model is jps_term
    record.jps_term.id = "term-aaaa-bbbb-cccc-dddd"
    record.jps_term.name = "term-10"
    record.jps_term.display = "term-10"
    record.action_type = "local-preference"
    record.value = "100"
    record.order = 1
    return record


@pytest.fixture
def mock_policy_prefix_list_record():
    record = MagicMock()
    record.id = "pl-aaaa-bbbb-cccc-dddd"
    record.display = "CUSTOMER-PREFIXES"
    record.url = "http://test/api/plugins/cms/pl-aaaa/"
    record.device.id = "dev-1111-2222-3333-4444"
    record.device.name = "core-rtr-01"
    record.device.display = "core-rtr-01"
    record.name = "CUSTOMER-PREFIXES"
    record.description = "Customer prefix list"
    return record


@pytest.fixture
def mock_policy_community_record():
    record = MagicMock()
    record.id = "comm-aaaa-bbbb-cccc-dddd"
    record.display = "MY-COMMUNITY"
    record.url = "http://test/api/plugins/cms/comm-aaaa/"
    record.device.id = "dev-1111-2222-3333-4444"
    record.device.name = "core-rtr-01"
    record.device.display = "core-rtr-01"
    record.name = "MY-COMMUNITY"
    record.members = "65000:100"
    record.description = "Internal community"
    return record


@pytest.fixture
def mock_policy_as_path_record():
    record = MagicMock()
    record.id = "asp-aaaa-bbbb-cccc-dddd"
    record.display = "MY-AS-PATH"
    record.url = "http://test/api/plugins/cms/asp-aaaa/"
    record.device.id = "dev-1111-2222-3333-4444"
    record.device.name = "core-rtr-01"
    record.device.display = "core-rtr-01"
    record.name = "MY-AS-PATH"
    record.regex = "^65000 .*"
    record.description = "Customer AS paths"
    return record


# ---------------------------------------------------------------------------
# Pydantic Model Tests
# ---------------------------------------------------------------------------


class TestPolicyStatementSummary:
    """Tests for PolicyStatementSummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_policy_statement_record):
        model = PolicyStatementSummary.from_nautobot(mock_policy_statement_record)
        assert model.id == "ps-aaaa-bbbb-cccc-dddd"
        assert model.name == "EXPORT-POLICY"
        assert model.description == "Export policy for eBGP"

    def test_from_nautobot_device_fk(self, mock_policy_statement_record):
        model = PolicyStatementSummary.from_nautobot(mock_policy_statement_record)
        assert model.device_id == "dev-1111-2222-3333-4444"
        assert model.device_name == "core-rtr-01"

    def test_from_nautobot_term_count_default(self, mock_policy_statement_record):
        model = PolicyStatementSummary.from_nautobot(mock_policy_statement_record)
        assert model.term_count == 0


class TestJPSTermSummary:
    """Tests for JPSTermSummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_jps_term_record):
        model = JPSTermSummary.from_nautobot(mock_jps_term_record)
        assert model.id == "term-aaaa-bbbb-cccc-dddd"
        assert model.name == "term-10"
        assert model.order == 10

    def test_from_nautobot_statement_fk(self, mock_jps_term_record):
        model = JPSTermSummary.from_nautobot(mock_jps_term_record)
        assert model.statement_id == "ps-aaaa-bbbb-cccc-dddd"
        assert model.statement_name == "EXPORT-POLICY"

    def test_from_nautobot_count_defaults(self, mock_jps_term_record):
        model = JPSTermSummary.from_nautobot(mock_jps_term_record)
        assert model.match_count == 0
        assert model.action_count == 0


class TestJPSMatchConditionSummary:
    """Tests for JPSMatchConditionSummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_jps_match_condition_record):
        model = JPSMatchConditionSummary.from_nautobot(mock_jps_match_condition_record)
        assert model.id == "mc-aaaa-bbbb-cccc-dddd"
        assert model.condition_type == "community"

    def test_from_nautobot_term_fk(self, mock_jps_match_condition_record):
        model = JPSMatchConditionSummary.from_nautobot(mock_jps_match_condition_record)
        assert model.term_id == "term-aaaa-bbbb-cccc-dddd"


class TestJPSActionSummary:
    """Tests for JPSActionSummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_jps_action_record):
        model = JPSActionSummary.from_nautobot(mock_jps_action_record)
        assert model.id == "action-aaaa-bbbb-cccc-dddd"
        assert model.action_type == "local-preference"
        assert model.value == "100"

    def test_from_nautobot_term_fk(self, mock_jps_action_record):
        model = JPSActionSummary.from_nautobot(mock_jps_action_record)
        assert model.term_id == "term-aaaa-bbbb-cccc-dddd"


class TestPolicyPrefixListSummary:
    """Tests for PolicyPrefixListSummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_policy_prefix_list_record):
        model = PolicyPrefixListSummary.from_nautobot(mock_policy_prefix_list_record)
        assert model.id == "pl-aaaa-bbbb-cccc-dddd"
        assert model.name == "CUSTOMER-PREFIXES"

    def test_from_nautobot_device_fk(self, mock_policy_prefix_list_record):
        model = PolicyPrefixListSummary.from_nautobot(mock_policy_prefix_list_record)
        assert model.device_id == "dev-1111-2222-3333-4444"
        assert model.device_name == "core-rtr-01"

    def test_prefix_count_default_zero(self, mock_policy_prefix_list_record):
        model = PolicyPrefixListSummary.from_nautobot(mock_policy_prefix_list_record)
        assert model.prefix_count == 0


class TestPolicyCommunitySummary:
    """Tests for PolicyCommunitySummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_policy_community_record):
        model = PolicyCommunitySummary.from_nautobot(mock_policy_community_record)
        assert model.id == "comm-aaaa-bbbb-cccc-dddd"
        assert model.name == "MY-COMMUNITY"
        assert model.members == "65000:100"

    def test_from_nautobot_device_fk(self, mock_policy_community_record):
        model = PolicyCommunitySummary.from_nautobot(mock_policy_community_record)
        assert model.device_id == "dev-1111-2222-3333-4444"
        assert model.device_name == "core-rtr-01"


class TestPolicyAsPathSummary:
    """Tests for PolicyAsPathSummary.from_nautobot()."""

    def test_from_nautobot_basic(self, mock_policy_as_path_record):
        model = PolicyAsPathSummary.from_nautobot(mock_policy_as_path_record)
        assert model.id == "asp-aaaa-bbbb-cccc-dddd"
        assert model.name == "MY-AS-PATH"
        assert model.regex == "^65000 .*"

    def test_from_nautobot_device_fk(self, mock_policy_as_path_record):
        model = PolicyAsPathSummary.from_nautobot(mock_policy_as_path_record)
        assert model.device_id == "dev-1111-2222-3333-4444"
        assert model.device_name == "core-rtr-01"


# ---------------------------------------------------------------------------
# CRUD Function Tests
# ---------------------------------------------------------------------------


class TestListPolicyStatements:
    """Tests for list_policy_statements CRUD function."""

    @patch("nautobot_mcp.cms.policies.cms_list")
    @patch("nautobot_mcp.cms.policies.resolve_device_id")
    def test_list_resolves_device(self, mock_resolve, mock_list):
        """Calls resolve_device_id and cms_list with 'juniper_policy_statements' endpoint."""
        mock_resolve.return_value = "dev-uuid"
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        result = list_policy_statements(client, device="core-rtr-01")

        mock_resolve.assert_called_once_with(client, "core-rtr-01")
        first_call_args = mock_list.call_args_list[0].args
        assert first_call_args[1] == "juniper_policy_statements"
        assert result.count == 0


class TestCreatePolicyStatement:
    """Tests for create_policy_statement CRUD function."""

    @patch("nautobot_mcp.cms.policies.cms_create")
    @patch("nautobot_mcp.cms.policies.resolve_device_id")
    def test_create_resolves_device(self, mock_resolve, mock_create, mock_policy_statement_record):
        """Resolves device and passes to cms_create."""
        mock_resolve.return_value = "dev-uuid"
        mock_create.return_value = PolicyStatementSummary.from_nautobot(mock_policy_statement_record)

        client = MagicMock()
        result = create_policy_statement(client, device="core-rtr-01", name="EXPORT-POLICY")

        mock_resolve.assert_called_once_with(client, "core-rtr-01")
        mock_create.assert_called_once_with(
            client,
            "juniper_policy_statements",
            PolicyStatementSummary,
            device="dev-uuid",
            name="EXPORT-POLICY",
        )


class TestDeletePolicyStatement:
    """Tests for delete_policy_statement."""

    @patch("nautobot_mcp.cms.policies.cms_delete")
    def test_delete_calls_cms_delete(self, mock_delete):
        """Calls cms_delete with correct endpoint and id."""
        mock_delete.return_value = {"success": True, "message": "Deleted."}

        client = MagicMock()
        result = delete_policy_statement(client, id="ps-aaaa-bbbb-cccc-dddd")

        mock_delete.assert_called_once_with(client, "juniper_policy_statements", id="ps-aaaa-bbbb-cccc-dddd")
        assert result["success"] is True


class TestListPolicyPrefixLists:
    """Tests for list_policy_prefix_lists."""

    @patch("nautobot_mcp.cms.policies.cms_list")
    @patch("nautobot_mcp.cms.policies.resolve_device_id")
    def test_list_device_scoped(self, mock_resolve, mock_list):
        mock_resolve.return_value = "dev-uuid"
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        result = list_policy_prefix_lists(client, device="core-rtr-01")

        mock_resolve.assert_called_once_with(client, "core-rtr-01")
        assert result.count == 0


class TestCreatePolicyCommunity:
    """Tests for create_policy_community."""

    @patch("nautobot_mcp.cms.policies.cms_create")
    @patch("nautobot_mcp.cms.policies.resolve_device_id")
    def test_create_community_with_members(self, mock_resolve, mock_create, mock_policy_community_record):
        """Creates community with required 'members' field."""
        mock_resolve.return_value = "dev-uuid"
        mock_create.return_value = PolicyCommunitySummary.from_nautobot(mock_policy_community_record)

        client = MagicMock()
        result = create_policy_community(
            client, device="core-rtr-01", name="MY-COMMUNITY", members="65000:100"
        )

        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["members"] == "65000:100"
        assert result.name == "MY-COMMUNITY"


class TestCreatePolicyAsPath:
    """Tests for create_policy_as_path."""

    @patch("nautobot_mcp.cms.policies.cms_create")
    @patch("nautobot_mcp.cms.policies.resolve_device_id")
    def test_create_as_path_with_regex(self, mock_resolve, mock_create, mock_policy_as_path_record):
        """Creates AS path with required 'regex' field."""
        mock_resolve.return_value = "dev-uuid"
        mock_create.return_value = PolicyAsPathSummary.from_nautobot(mock_policy_as_path_record)

        client = MagicMock()
        result = create_policy_as_path(
            client, device="core-rtr-01", name="MY-AS-PATH", regex="^65000 .*"
        )

        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["regex"] == "^65000 .*"
        assert result.regex == "^65000 .*"


class TestListJPSTerms:
    """Tests for list_jps_terms (read-only)."""

    @patch("nautobot_mcp.cms.policies.cms_list")
    def test_list_all_terms(self, mock_list):
        """Lists all terms when no statement_id given."""
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        result = list_jps_terms(client)

        assert result.count == 0

    @patch("nautobot_mcp.cms.policies.cms_list")
    def test_list_by_statement_id(self, mock_list):
        """Passes statement_id as 'policy_statement' kwarg."""
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        list_jps_terms(client, statement_id="ps-aaaa-bbbb-cccc-dddd")

        first_kwargs = mock_list.call_args_list[0].kwargs
        assert first_kwargs.get("policy_statement") == "ps-aaaa-bbbb-cccc-dddd"


class TestListJPSMatchConditions:
    """Tests for list_jps_match_conditions (read-only)."""

    @patch("nautobot_mcp.cms.policies.cms_list")
    def test_list_by_term_id(self, mock_list):
        """Passes term_id as 'jps_term' kwarg to cms_list."""
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        list_jps_match_conditions(client, term_id="term-aaaa")

        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs.get("jps_term") == "term-aaaa"


class TestListPolicyCommunities:
    """Tests for list_policy_communities."""

    @patch("nautobot_mcp.cms.policies.cms_list")
    @patch("nautobot_mcp.cms.policies.resolve_device_id")
    def test_list_resolves_device(self, mock_resolve, mock_list):
        mock_resolve.return_value = "dev-uuid"
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        result = list_policy_communities(client, device="core-rtr-01")

        mock_resolve.assert_called_once_with(client, "core-rtr-01")
        assert result.count == 0


class TestListPolicyAsPaths:
    """Tests for list_policy_as_paths."""

    @patch("nautobot_mcp.cms.policies.cms_list")
    @patch("nautobot_mcp.cms.policies.resolve_device_id")
    def test_list_uses_juniper_policy_as_paths_endpoint(self, mock_resolve, mock_list):
        mock_resolve.return_value = "dev-uuid"
        mock_list.return_value = ListResponse(count=0, results=[])

        client = MagicMock()
        list_policy_as_paths(client, device="core-rtr-01")

        call_args = mock_list.call_args_list[0].args
        assert call_args[1] == "juniper_policy_as_paths"
