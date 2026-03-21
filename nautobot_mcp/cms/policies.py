"""CMS policy domain CRUD operations.

Provides domain-specific CRUD functions for all Juniper policy models:
- Policy statements (full CRUD, device-scoped)
- Policy prefix lists (full CRUD, device-scoped)
- Policy communities (full CRUD, device-scoped)
- Policy AS paths (full CRUD, device-scoped)
- Policy prefixes (list/get — read-only)
- JPS terms (list/get — read-only)
- JPS match conditions and sub-associations (list/get — read-only)
- JPS actions and sub-associations (list/get — read-only)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nautobot_mcp.cms.client import (
    cms_create,
    cms_delete,
    cms_get,
    cms_list,
    cms_update,
    resolve_device_id,
)
from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.cms.policies import (
    JPSActionAsPathSummary,
    JPSActionCommunitySummary,
    JPSActionInstallNexthopSummary,
    JPSActionLoadBalanceSummary,
    JPSActionSummary,
    JPSMatchConditionAsPathSummary,
    JPSMatchConditionCommunitySummary,
    JPSMatchConditionPrefixListSummary,
    JPSMatchConditionRouteFilterSummary,
    JPSMatchConditionSummary,
    JPSTermSummary,
    PolicyAsPathSummary,
    PolicyCommunitySummary,
    PolicyPrefixListSummary,
    PolicyPrefixSummary,
    PolicyStatementSummary,
)

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


# ---------------------------------------------------------------------------
# Policy Statements (full CRUD, device-scoped)
# ---------------------------------------------------------------------------


def list_policy_statements(
    client: NautobotClient,
    device: str,
    limit: int = 0,
) -> ListResponse[PolicyStatementSummary]:
    """List policy statements for a device. Populates term_count per statement.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[PolicyStatementSummary] with term_count populated.
    """
    try:
        device_id = resolve_device_id(client, device)
        statements = cms_list(
            client, "juniper_policy_statements", PolicyStatementSummary, limit=0, device=device_id
        )

        if statements.results:
            for s in statements.results:
                try:
                    terms = cms_list(
                        client,
                        "jps_terms",
                        JPSTermSummary,
                        limit=0,
                        policy_statement=s.id,
                    )
                    s.term_count = len(terms.results)
                except Exception:
                    pass

        all_results = statements.results
        limited = all_results[:limit] if limit > 0 else all_results
        return ListResponse(count=len(all_results), results=limited)
    except Exception as e:
        client._handle_api_error(e, "list", "PolicyStatement")
        raise


def get_policy_statement(client: NautobotClient, id: str) -> PolicyStatementSummary:
    """Get a policy statement with inlined term summaries."""
    try:
        statement = cms_get(client, "juniper_policy_statements", PolicyStatementSummary, id=id)
        terms = cms_list(client, "jps_terms", JPSTermSummary, limit=0, policy_statement=id)
        statement.term_count = len(terms.results)

        for term in terms.results:
            try:
                mc = cms_list(client, "jps_match_conditions", JPSMatchConditionSummary, limit=0, jps_term=term.id)
                term.match_count = len(mc.results)
            except Exception:
                pass
            try:
                actions = cms_list(client, "jps_actions", JPSActionSummary, limit=0, jps_term=term.id)
                term.action_count = len(actions.results)
            except Exception:
                pass

        object.__setattr__(statement, "terms", terms.results)
        return statement
    except Exception as e:
        client._handle_api_error(e, "get", "PolicyStatement")
        raise


def create_policy_statement(
    client: NautobotClient,
    device: str,
    name: str,
    **kwargs,
) -> PolicyStatementSummary:
    """Create a Juniper policy statement."""
    try:
        device_id = resolve_device_id(client, device)
        return cms_create(
            client,
            "juniper_policy_statements",
            PolicyStatementSummary,
            device=device_id,
            name=name,
            **kwargs,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "PolicyStatement")
        raise


def update_policy_statement(client: NautobotClient, id: str, **updates) -> PolicyStatementSummary:
    """Update a Juniper policy statement."""
    try:
        return cms_update(client, "juniper_policy_statements", PolicyStatementSummary, id=id, **updates)
    except Exception as e:
        client._handle_api_error(e, "update", "PolicyStatement")
        raise


def delete_policy_statement(client: NautobotClient, id: str) -> dict:
    """Delete a Juniper policy statement."""
    try:
        return cms_delete(client, "juniper_policy_statements", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "PolicyStatement")
        raise


# ---------------------------------------------------------------------------
# Policy Prefix Lists (full CRUD, device-scoped)
# ---------------------------------------------------------------------------


def list_policy_prefix_lists(
    client: NautobotClient,
    device: str,
    limit: int = 0,
) -> ListResponse[PolicyPrefixListSummary]:
    """List policy prefix lists for a device. Populates prefix_count per list."""
    try:
        device_id = resolve_device_id(client, device)
        pls = cms_list(client, "juniper_policy_prefix_lists", PolicyPrefixListSummary, limit=0, device=device_id)

        if pls.results:
            for pl in pls.results:
                try:
                    prefixes = cms_list(
                        client, "juniper_policy_prefixes", PolicyPrefixSummary, limit=0, prefix_list=pl.id
                    )
                    pl.prefix_count = len(prefixes.results)
                except Exception:
                    pass

        all_results = pls.results
        limited = all_results[:limit] if limit > 0 else all_results
        return ListResponse(count=len(all_results), results=limited)
    except Exception as e:
        client._handle_api_error(e, "list", "PolicyPrefixList")
        raise


def get_policy_prefix_list(client: NautobotClient, id: str) -> PolicyPrefixListSummary:
    """Get a policy prefix list with inlined prefixes."""
    try:
        pl = cms_get(client, "juniper_policy_prefix_lists", PolicyPrefixListSummary, id=id)
        prefixes = cms_list(client, "juniper_policy_prefixes", PolicyPrefixSummary, limit=0, prefix_list=id)
        pl.prefix_count = len(prefixes.results)
        object.__setattr__(pl, "prefixes", prefixes.results)
        return pl
    except Exception as e:
        client._handle_api_error(e, "get", "PolicyPrefixList")
        raise


def create_policy_prefix_list(
    client: NautobotClient,
    device: str,
    name: str,
    **kwargs,
) -> PolicyPrefixListSummary:
    """Create a Juniper policy prefix list."""
    try:
        device_id = resolve_device_id(client, device)
        return cms_create(
            client,
            "juniper_policy_prefix_lists",
            PolicyPrefixListSummary,
            device=device_id,
            name=name,
            **kwargs,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "PolicyPrefixList")
        raise


def update_policy_prefix_list(client: NautobotClient, id: str, **updates) -> PolicyPrefixListSummary:
    """Update a Juniper policy prefix list."""
    try:
        return cms_update(client, "juniper_policy_prefix_lists", PolicyPrefixListSummary, id=id, **updates)
    except Exception as e:
        client._handle_api_error(e, "update", "PolicyPrefixList")
        raise


def delete_policy_prefix_list(client: NautobotClient, id: str) -> dict:
    """Delete a Juniper policy prefix list."""
    try:
        return cms_delete(client, "juniper_policy_prefix_lists", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "PolicyPrefixList")
        raise


# ---------------------------------------------------------------------------
# Policy Communities (full CRUD, device-scoped)
# ---------------------------------------------------------------------------


def list_policy_communities(
    client: NautobotClient,
    device: str,
    limit: int = 0,
) -> ListResponse[PolicyCommunitySummary]:
    """List policy communities for a device."""
    try:
        device_id = resolve_device_id(client, device)
        return cms_list(
            client, "juniper_policy_communities", PolicyCommunitySummary, limit=limit, device=device_id
        )
    except Exception as e:
        client._handle_api_error(e, "list", "PolicyCommunity")
        raise


def get_policy_community(client: NautobotClient, id: str) -> PolicyCommunitySummary:
    """Get a single policy community by UUID."""
    try:
        return cms_get(client, "juniper_policy_communities", PolicyCommunitySummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "PolicyCommunity")
        raise


def create_policy_community(
    client: NautobotClient,
    device: str,
    name: str,
    members: str,
    **kwargs,
) -> PolicyCommunitySummary:
    """Create a Juniper policy community.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        name: Community name.
        members: Community value string (e.g. '65000:100').
        **kwargs: Additional fields (description, etc.).
    """
    try:
        device_id = resolve_device_id(client, device)
        return cms_create(
            client,
            "juniper_policy_communities",
            PolicyCommunitySummary,
            device=device_id,
            name=name,
            members=members,
            **kwargs,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "PolicyCommunity")
        raise


def update_policy_community(client: NautobotClient, id: str, **updates) -> PolicyCommunitySummary:
    """Update a Juniper policy community."""
    try:
        return cms_update(client, "juniper_policy_communities", PolicyCommunitySummary, id=id, **updates)
    except Exception as e:
        client._handle_api_error(e, "update", "PolicyCommunity")
        raise


def delete_policy_community(client: NautobotClient, id: str) -> dict:
    """Delete a Juniper policy community."""
    try:
        return cms_delete(client, "juniper_policy_communities", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "PolicyCommunity")
        raise


# ---------------------------------------------------------------------------
# Policy AS Paths (full CRUD, device-scoped)
# ---------------------------------------------------------------------------


def list_policy_as_paths(
    client: NautobotClient,
    device: str,
    limit: int = 0,
) -> ListResponse[PolicyAsPathSummary]:
    """List policy AS paths for a device."""
    try:
        device_id = resolve_device_id(client, device)
        return cms_list(
            client, "juniper_policy_as_paths", PolicyAsPathSummary, limit=limit, device=device_id
        )
    except Exception as e:
        client._handle_api_error(e, "list", "PolicyAsPath")
        raise


def get_policy_as_path(client: NautobotClient, id: str) -> PolicyAsPathSummary:
    """Get a single policy AS path by UUID."""
    try:
        return cms_get(client, "juniper_policy_as_paths", PolicyAsPathSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "PolicyAsPath")
        raise


def create_policy_as_path(
    client: NautobotClient,
    device: str,
    name: str,
    regex: str,
    **kwargs,
) -> PolicyAsPathSummary:
    """Create a Juniper policy AS path.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        name: AS-path name.
        regex: AS-path regular expression.
        **kwargs: Additional fields (description, etc.).
    """
    try:
        device_id = resolve_device_id(client, device)
        return cms_create(
            client,
            "juniper_policy_as_paths",
            PolicyAsPathSummary,
            device=device_id,
            name=name,
            regex=regex,
            **kwargs,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "PolicyAsPath")
        raise


def update_policy_as_path(client: NautobotClient, id: str, **updates) -> PolicyAsPathSummary:
    """Update a Juniper policy AS path."""
    try:
        return cms_update(client, "juniper_policy_as_paths", PolicyAsPathSummary, id=id, **updates)
    except Exception as e:
        client._handle_api_error(e, "update", "PolicyAsPath")
        raise


def delete_policy_as_path(client: NautobotClient, id: str) -> dict:
    """Delete a Juniper policy AS path."""
    try:
        return cms_delete(client, "juniper_policy_as_paths", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "PolicyAsPath")
        raise


# ---------------------------------------------------------------------------
# Policy Prefixes (list/get — read-only, child of prefix list)
# ---------------------------------------------------------------------------


def list_policy_prefixes(
    client: NautobotClient,
    prefix_list_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[PolicyPrefixSummary]:
    """List policy prefixes, optionally filtered by parent prefix list."""
    try:
        extra: dict = {}
        if prefix_list_id:
            extra["prefix_list"] = prefix_list_id
        return cms_list(client, "juniper_policy_prefixes", PolicyPrefixSummary, limit=limit, **extra)
    except Exception as e:
        client._handle_api_error(e, "list", "PolicyPrefix")
        raise


def get_policy_prefix(client: NautobotClient, id: str) -> PolicyPrefixSummary:
    """Get a single policy prefix by UUID."""
    try:
        return cms_get(client, "juniper_policy_prefixes", PolicyPrefixSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "PolicyPrefix")
        raise


# ---------------------------------------------------------------------------
# JPS Terms (list/get — read-only, child of statement)
# ---------------------------------------------------------------------------


def list_jps_terms(
    client: NautobotClient,
    statement_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[JPSTermSummary]:
    """List JPS terms, optionally filtered by parent policy statement."""
    try:
        extra: dict = {}
        if statement_id:
            extra["policy_statement"] = statement_id
        terms = cms_list(client, "jps_terms", JPSTermSummary, limit=0, **extra)

        if terms.results:
            try:
                all_mc = cms_list(
                    client, "jps_match_conditions", JPSMatchConditionSummary, limit=0,
                    **({} if not statement_id else {"policy_statement": statement_id}),
                )
                mc_count: dict[str, int] = {}
                for mc in all_mc.results:
                    mc_count[mc.term_id] = mc_count.get(mc.term_id, 0) + 1
                for t in terms.results:
                    t.match_count = mc_count.get(t.id, 0)
            except Exception:
                pass
            try:
                all_actions = cms_list(
                    client, "jps_actions", JPSActionSummary, limit=0,
                    **({} if not statement_id else {"policy_statement": statement_id}),
                )
                ac_count: dict[str, int] = {}
                for a in all_actions.results:
                    ac_count[a.term_id] = ac_count.get(a.term_id, 0) + 1
                for t in terms.results:
                    t.action_count = ac_count.get(t.id, 0)
            except Exception:
                pass

        all_results = terms.results
        limited = all_results[:limit] if limit > 0 else all_results
        return ListResponse(count=len(all_results), results=limited)
    except Exception as e:
        client._handle_api_error(e, "list", "JPSTerm")
        raise


def get_jps_term(client: NautobotClient, id: str) -> JPSTermSummary:
    """Get a JPS term with inlined match conditions and actions."""
    try:
        term = cms_get(client, "jps_terms", JPSTermSummary, id=id)

        try:
            mc = cms_list(client, "jps_match_conditions", JPSMatchConditionSummary, limit=0, jps_term=id)
            term.match_count = len(mc.results)
            object.__setattr__(term, "match_conditions", mc.results)
        except Exception:
            object.__setattr__(term, "match_conditions", [])

        try:
            actions = cms_list(client, "jps_actions", JPSActionSummary, limit=0, jps_term=id)
            term.action_count = len(actions.results)
            object.__setattr__(term, "actions", actions.results)
        except Exception:
            object.__setattr__(term, "actions", [])

        return term
    except Exception as e:
        client._handle_api_error(e, "get", "JPSTerm")
        raise


# ---------------------------------------------------------------------------
# JPS Match Conditions (list/get — read-only)
# ---------------------------------------------------------------------------


def list_jps_match_conditions(
    client: NautobotClient,
    term_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[JPSMatchConditionSummary]:
    """List JPS match conditions, optionally filtered by parent term."""
    try:
        extra: dict = {}
        if term_id:
            extra["jps_term"] = term_id
        return cms_list(client, "jps_match_conditions", JPSMatchConditionSummary, limit=limit, **extra)
    except Exception as e:
        client._handle_api_error(e, "list", "JPSMatchCondition")
        raise


def get_jps_match_condition(client: NautobotClient, id: str) -> JPSMatchConditionSummary:
    """Get a single JPS match condition by UUID."""
    try:
        return cms_get(client, "jps_match_conditions", JPSMatchConditionSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "JPSMatchCondition")
        raise


# ---------------------------------------------------------------------------
# JPS Match Condition Route Filters (list/get — read-only)
# ---------------------------------------------------------------------------


def list_jps_match_condition_route_filters(
    client: NautobotClient,
    match_condition_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[JPSMatchConditionRouteFilterSummary]:
    """List JPS match condition route filters."""
    try:
        extra: dict = {}
        if match_condition_id:
            extra["jps_match_condition"] = match_condition_id
        return cms_list(
            client, "jps_match_condition_route_filters", JPSMatchConditionRouteFilterSummary, limit=limit, **extra
        )
    except Exception as e:
        client._handle_api_error(e, "list", "JPSMatchConditionRouteFilter")
        raise


def get_jps_match_condition_route_filter(
    client: NautobotClient, id: str
) -> JPSMatchConditionRouteFilterSummary:
    """Get a single JPS match condition route filter by UUID."""
    try:
        return cms_get(client, "jps_match_condition_route_filters", JPSMatchConditionRouteFilterSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "JPSMatchConditionRouteFilter")
        raise


# ---------------------------------------------------------------------------
# JPS Match Condition Prefix Lists (list/get — read-only)
# ---------------------------------------------------------------------------


def list_jps_match_condition_prefix_lists(
    client: NautobotClient,
    match_condition_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[JPSMatchConditionPrefixListSummary]:
    """List JPS match condition prefix list associations."""
    try:
        extra: dict = {}
        if match_condition_id:
            extra["jps_match_condition"] = match_condition_id
        return cms_list(
            client, "jps_match_condition_prefix_lists", JPSMatchConditionPrefixListSummary, limit=limit, **extra
        )
    except Exception as e:
        client._handle_api_error(e, "list", "JPSMatchConditionPrefixList")
        raise


def get_jps_match_condition_prefix_list(
    client: NautobotClient, id: str
) -> JPSMatchConditionPrefixListSummary:
    """Get a single JPS match condition prefix list association by UUID."""
    try:
        return cms_get(
            client, "jps_match_condition_prefix_lists", JPSMatchConditionPrefixListSummary, id=id
        )
    except Exception as e:
        client._handle_api_error(e, "get", "JPSMatchConditionPrefixList")
        raise


# ---------------------------------------------------------------------------
# JPS Match Condition Communities (list/get — read-only)
# ---------------------------------------------------------------------------


def list_jps_match_condition_communities(
    client: NautobotClient,
    match_condition_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[JPSMatchConditionCommunitySummary]:
    """List JPS match condition community associations."""
    try:
        extra: dict = {}
        if match_condition_id:
            extra["jps_match_condition"] = match_condition_id
        return cms_list(
            client, "jps_match_condition_communities", JPSMatchConditionCommunitySummary, limit=limit, **extra
        )
    except Exception as e:
        client._handle_api_error(e, "list", "JPSMatchConditionCommunity")
        raise


def get_jps_match_condition_community(
    client: NautobotClient, id: str
) -> JPSMatchConditionCommunitySummary:
    """Get a single JPS match condition community association by UUID."""
    try:
        return cms_get(client, "jps_match_condition_communities", JPSMatchConditionCommunitySummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "JPSMatchConditionCommunity")
        raise


# ---------------------------------------------------------------------------
# JPS Match Condition AS Paths (list/get — read-only)
# ---------------------------------------------------------------------------


def list_jps_match_condition_as_paths(
    client: NautobotClient,
    match_condition_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[JPSMatchConditionAsPathSummary]:
    """List JPS match condition AS path associations."""
    try:
        extra: dict = {}
        if match_condition_id:
            extra["jps_match_condition"] = match_condition_id
        return cms_list(
            client, "jps_match_condition_as_paths", JPSMatchConditionAsPathSummary, limit=limit, **extra
        )
    except Exception as e:
        client._handle_api_error(e, "list", "JPSMatchConditionAsPath")
        raise


def get_jps_match_condition_as_path(
    client: NautobotClient, id: str
) -> JPSMatchConditionAsPathSummary:
    """Get a single JPS match condition AS path association by UUID."""
    try:
        return cms_get(client, "jps_match_condition_as_paths", JPSMatchConditionAsPathSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "JPSMatchConditionAsPath")
        raise


# ---------------------------------------------------------------------------
# JPS Actions (list/get — read-only)
# ---------------------------------------------------------------------------


def list_jps_actions(
    client: NautobotClient,
    term_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[JPSActionSummary]:
    """List JPS actions, optionally filtered by parent term."""
    try:
        extra: dict = {}
        if term_id:
            extra["jps_term"] = term_id
        return cms_list(client, "jps_actions", JPSActionSummary, limit=limit, **extra)
    except Exception as e:
        client._handle_api_error(e, "list", "JPSAction")
        raise


def get_jps_action(client: NautobotClient, id: str) -> JPSActionSummary:
    """Get a single JPS action by UUID."""
    try:
        return cms_get(client, "jps_actions", JPSActionSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "JPSAction")
        raise


# ---------------------------------------------------------------------------
# JPS Action Communities (list/get — read-only)
# ---------------------------------------------------------------------------


def list_jps_action_communities(
    client: NautobotClient,
    action_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[JPSActionCommunitySummary]:
    """List JPS action community associations."""
    try:
        extra: dict = {}
        if action_id:
            extra["jps_action"] = action_id
        return cms_list(client, "jps_action_communities", JPSActionCommunitySummary, limit=limit, **extra)
    except Exception as e:
        client._handle_api_error(e, "list", "JPSActionCommunity")
        raise


def get_jps_action_community(client: NautobotClient, id: str) -> JPSActionCommunitySummary:
    """Get a single JPS action community association by UUID."""
    try:
        return cms_get(client, "jps_action_communities", JPSActionCommunitySummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "JPSActionCommunity")
        raise


# ---------------------------------------------------------------------------
# JPS Action AS Paths (list/get — read-only)
# ---------------------------------------------------------------------------


def list_jps_action_as_paths(
    client: NautobotClient,
    action_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[JPSActionAsPathSummary]:
    """List JPS action AS path associations."""
    try:
        extra: dict = {}
        if action_id:
            extra["jps_action"] = action_id
        return cms_list(client, "jps_action_as_paths", JPSActionAsPathSummary, limit=limit, **extra)
    except Exception as e:
        client._handle_api_error(e, "list", "JPSActionAsPath")
        raise


def get_jps_action_as_path(client: NautobotClient, id: str) -> JPSActionAsPathSummary:
    """Get a single JPS action AS path association by UUID."""
    try:
        return cms_get(client, "jps_action_as_paths", JPSActionAsPathSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "JPSActionAsPath")
        raise


# ---------------------------------------------------------------------------
# JPS Action Load Balances (list/get — read-only)
# ---------------------------------------------------------------------------


def list_jps_action_load_balances(
    client: NautobotClient,
    action_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[JPSActionLoadBalanceSummary]:
    """List JPS action load balance configurations."""
    try:
        extra: dict = {}
        if action_id:
            extra["jps_action"] = action_id
        return cms_list(client, "jps_action_load_balances", JPSActionLoadBalanceSummary, limit=limit, **extra)
    except Exception as e:
        client._handle_api_error(e, "list", "JPSActionLoadBalance")
        raise


def get_jps_action_load_balance(client: NautobotClient, id: str) -> JPSActionLoadBalanceSummary:
    """Get a single JPS action load balance by UUID."""
    try:
        return cms_get(client, "jps_action_load_balances", JPSActionLoadBalanceSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "JPSActionLoadBalance")
        raise


# ---------------------------------------------------------------------------
# JPS Action Install Nexthops (list/get — read-only)
# ---------------------------------------------------------------------------


def list_jps_action_install_nexthops(
    client: NautobotClient,
    action_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[JPSActionInstallNexthopSummary]:
    """List JPS action install nexthop configurations."""
    try:
        extra: dict = {}
        if action_id:
            extra["jps_action"] = action_id
        return cms_list(
            client, "jps_action_install_nexthops", JPSActionInstallNexthopSummary, limit=limit, **extra
        )
    except Exception as e:
        client._handle_api_error(e, "list", "JPSActionInstallNexthop")
        raise


def get_jps_action_install_nexthop(client: NautobotClient, id: str) -> JPSActionInstallNexthopSummary:
    """Get a single JPS action install nexthop by UUID."""
    try:
        return cms_get(client, "jps_action_install_nexthops", JPSActionInstallNexthopSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "JPSActionInstallNexthop")
        raise
