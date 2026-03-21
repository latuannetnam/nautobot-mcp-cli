"""CMS firewall domain CRUD operations.

Provides domain-specific CRUD functions for all Juniper firewall models:
- Firewall filters (full CRUD, device-scoped)
- Firewall policers (full CRUD, device-scoped)
- Firewall terms (list/get — read-only)
- Firewall match conditions (list/get — read-only)
- Firewall match condition to prefix list (list/get — read-only)
- Firewall filter actions (list/get — read-only)
- Firewall policer actions (list/get — read-only)
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
from nautobot_mcp.models.cms.firewalls import (
    FirewallFilterActionSummary,
    FirewallFilterSummary,
    FirewallMatchConditionSummary,
    FirewallMatchConditionToPrefixListSummary,
    FirewallPolicerActionSummary,
    FirewallPolicerSummary,
    FirewallTermSummary,
)

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


# ---------------------------------------------------------------------------
# Firewall Filters (full CRUD, device-scoped)
# ---------------------------------------------------------------------------


def list_firewall_filters(
    client: NautobotClient,
    device: str,
    family: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[FirewallFilterSummary]:
    """List firewall filters for a device. Populates term_count per filter.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        family: Optional address family filter (inet, inet6, vpls, etc.).
        limit: Maximum number of results (0 = all).

    Returns:
        ListResponse[FirewallFilterSummary] with term_count populated.
    """
    try:
        device_id = resolve_device_id(client, device)
        extra: dict = {"device": device_id}
        if family:
            extra["family"] = family
        filters = cms_list(client, "juniper_firewall_filters", FirewallFilterSummary, limit=0, **extra)

        if filters.results:
            try:
                all_terms = cms_list(
                    client,
                    "juniper_firewall_terms",
                    FirewallTermSummary,
                    limit=0,
                    device=device_id,
                )
                term_count_by_filter: dict[str, int] = {}
                for term in all_terms.results:
                    term_count_by_filter[term.filter_id] = term_count_by_filter.get(term.filter_id, 0) + 1
                for f in filters.results:
                    f.term_count = term_count_by_filter.get(f.id, 0)
            except Exception:
                pass

        all_results = filters.results
        limited = all_results[:limit] if limit > 0 else all_results
        return ListResponse(count=len(all_results), results=limited)
    except Exception as e:
        client._handle_api_error(e, "list", "FirewallFilter")
        raise


def get_firewall_filter(client: NautobotClient, id: str) -> FirewallFilterSummary:
    """Get a firewall filter with inlined term summaries.

    Args:
        client: NautobotClient instance.
        id: Firewall filter UUID.

    Returns:
        FirewallFilterSummary with term_count set and 'terms' extra attribute.
    """
    try:
        fw_filter = cms_get(client, "juniper_firewall_filters", FirewallFilterSummary, id=id)

        terms = cms_list(
            client,
            "juniper_firewall_terms",
            FirewallTermSummary,
            limit=0,
            filter=id,
        )
        fw_filter.term_count = len(terms.results)

        # Populate match_count and action_count for each term
        for term in terms.results:
            try:
                mc = cms_list(
                    client,
                    "juniper_firewall_match_conditions",
                    FirewallMatchConditionSummary,
                    limit=0,
                    term=term.id,
                )
                term.match_count = len(mc.results)
            except Exception:
                pass
            try:
                actions = cms_list(
                    client,
                    "juniper_firewall_actions",
                    FirewallFilterActionSummary,
                    limit=0,
                    term=term.id,
                )
                term.action_count = len(actions.results)
            except Exception:
                pass

        object.__setattr__(fw_filter, "terms", terms.results)
        return fw_filter
    except Exception as e:
        client._handle_api_error(e, "get", "FirewallFilter")
        raise


def create_firewall_filter(
    client: NautobotClient,
    device: str,
    name: str,
    family: str = "inet",
    **kwargs,
) -> FirewallFilterSummary:
    """Create a Juniper firewall filter.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        name: Filter name.
        family: Address family (inet, inet6, vpls, etc.). Default: inet.
        **kwargs: Additional fields (description, etc.).

    Returns:
        FirewallFilterSummary of the created filter.
    """
    try:
        device_id = resolve_device_id(client, device)
        return cms_create(
            client,
            "juniper_firewall_filters",
            FirewallFilterSummary,
            device=device_id,
            name=name,
            family=family,
            **kwargs,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "FirewallFilter")
        raise


def update_firewall_filter(client: NautobotClient, id: str, **updates) -> FirewallFilterSummary:
    """Update a Juniper firewall filter.

    Args:
        client: NautobotClient instance.
        id: Filter UUID.
        **updates: Fields to update (name, description, family, etc.).

    Returns:
        Updated FirewallFilterSummary.
    """
    try:
        return cms_update(client, "juniper_firewall_filters", FirewallFilterSummary, id=id, **updates)
    except Exception as e:
        client._handle_api_error(e, "update", "FirewallFilter")
        raise


def delete_firewall_filter(client: NautobotClient, id: str) -> dict:
    """Delete a Juniper firewall filter.

    Args:
        client: NautobotClient instance.
        id: Filter UUID.

    Returns:
        Dict with success status.
    """
    try:
        return cms_delete(client, "juniper_firewall_filters", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "FirewallFilter")
        raise


# ---------------------------------------------------------------------------
# Firewall Policers (full CRUD, device-scoped)
# ---------------------------------------------------------------------------


def list_firewall_policers(
    client: NautobotClient,
    device: str,
    limit: int = 0,
) -> ListResponse[FirewallPolicerSummary]:
    """List firewall policers for a device. Populates action_count per policer.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        limit: Maximum number of results (0 = all).

    Returns:
        ListResponse[FirewallPolicerSummary] with action_count populated.
    """
    try:
        device_id = resolve_device_id(client, device)
        policers = cms_list(client, "juniper_firewall_policers", FirewallPolicerSummary, limit=0, device=device_id)

        if policers.results:
            try:
                all_actions = cms_list(
                    client,
                    "juniper_firewall_policer_actions",
                    FirewallPolicerActionSummary,
                    limit=0,
                    device=device_id,
                )
                action_count_by_policer: dict[str, int] = {}
                for action in all_actions.results:
                    action_count_by_policer[action.policer_id] = (
                        action_count_by_policer.get(action.policer_id, 0) + 1
                    )
                for p in policers.results:
                    p.action_count = action_count_by_policer.get(p.id, 0)
            except Exception:
                pass

        all_results = policers.results
        limited = all_results[:limit] if limit > 0 else all_results
        return ListResponse(count=len(all_results), results=limited)
    except Exception as e:
        client._handle_api_error(e, "list", "FirewallPolicer")
        raise


def get_firewall_policer(client: NautobotClient, id: str) -> FirewallPolicerSummary:
    """Get a firewall policer with inlined actions.

    Args:
        client: NautobotClient instance.
        id: Policer UUID.

    Returns:
        FirewallPolicerSummary with action_count set and 'actions' extra attribute.
    """
    try:
        policer = cms_get(client, "juniper_firewall_policers", FirewallPolicerSummary, id=id)
        actions = cms_list(
            client,
            "juniper_firewall_policer_actions",
            FirewallPolicerActionSummary,
            limit=0,
            policer=id,
        )
        policer.action_count = len(actions.results)
        object.__setattr__(policer, "actions", actions.results)
        return policer
    except Exception as e:
        client._handle_api_error(e, "get", "FirewallPolicer")
        raise


def create_firewall_policer(
    client: NautobotClient,
    device: str,
    name: str,
    **kwargs,
) -> FirewallPolicerSummary:
    """Create a Juniper firewall policer.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        name: Policer name.
        **kwargs: Additional fields (bandwidth_limit, bandwidth_unit, burst_limit, etc.).

    Returns:
        FirewallPolicerSummary of the created policer.
    """
    try:
        device_id = resolve_device_id(client, device)
        return cms_create(
            client,
            "juniper_firewall_policers",
            FirewallPolicerSummary,
            device=device_id,
            name=name,
            **kwargs,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "FirewallPolicer")
        raise


def update_firewall_policer(client: NautobotClient, id: str, **updates) -> FirewallPolicerSummary:
    """Update a Juniper firewall policer.

    Args:
        client: NautobotClient instance.
        id: Policer UUID.
        **updates: Fields to update.

    Returns:
        Updated FirewallPolicerSummary.
    """
    try:
        return cms_update(client, "juniper_firewall_policers", FirewallPolicerSummary, id=id, **updates)
    except Exception as e:
        client._handle_api_error(e, "update", "FirewallPolicer")
        raise


def delete_firewall_policer(client: NautobotClient, id: str) -> dict:
    """Delete a Juniper firewall policer.

    Args:
        client: NautobotClient instance.
        id: Policer UUID.

    Returns:
        Dict with success status.
    """
    try:
        return cms_delete(client, "juniper_firewall_policers", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "FirewallPolicer")
        raise


# ---------------------------------------------------------------------------
# Firewall Terms (list/get — read-only)
# ---------------------------------------------------------------------------


def list_firewall_terms(
    client: NautobotClient,
    filter_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[FirewallTermSummary]:
    """List firewall terms, optionally filtered by parent filter.

    Args:
        client: NautobotClient instance.
        filter_id: Filter by parent firewall filter UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[FirewallTermSummary] with match_count and action_count populated.
    """
    try:
        extra: dict = {}
        if filter_id:
            extra["filter"] = filter_id
        terms = cms_list(client, "juniper_firewall_terms", FirewallTermSummary, limit=0, **extra)

        if terms.results:
            try:
                term_ids = [t.id for t in terms.results]
                all_mc = cms_list(
                    client,
                    "juniper_firewall_match_conditions",
                    FirewallMatchConditionSummary,
                    limit=0,
                    **({} if not filter_id else {"filter": filter_id}),
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
                    client,
                    "juniper_firewall_actions",
                    FirewallFilterActionSummary,
                    limit=0,
                    **({} if not filter_id else {"filter": filter_id}),
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
        client._handle_api_error(e, "list", "FirewallTerm")
        raise


def get_firewall_term(client: NautobotClient, id: str) -> FirewallTermSummary:
    """Get a firewall term with inlined match conditions and actions.

    Args:
        client: NautobotClient instance.
        id: Term UUID.

    Returns:
        FirewallTermSummary with 'match_conditions' and 'actions' extra attributes.
    """
    try:
        term = cms_get(client, "juniper_firewall_terms", FirewallTermSummary, id=id)

        try:
            mc = cms_list(
                client,
                "juniper_firewall_match_conditions",
                FirewallMatchConditionSummary,
                limit=0,
                term=id,
            )
            term.match_count = len(mc.results)
            object.__setattr__(term, "match_conditions", mc.results)
        except Exception:
            object.__setattr__(term, "match_conditions", [])

        try:
            actions = cms_list(
                client,
                "juniper_firewall_actions",
                FirewallFilterActionSummary,
                limit=0,
                term=id,
            )
            term.action_count = len(actions.results)
            object.__setattr__(term, "actions", actions.results)
        except Exception:
            object.__setattr__(term, "actions", [])

        return term
    except Exception as e:
        client._handle_api_error(e, "get", "FirewallTerm")
        raise


# ---------------------------------------------------------------------------
# Firewall Match Conditions (list/get — read-only)
# ---------------------------------------------------------------------------


def list_firewall_match_conditions(
    client: NautobotClient,
    term_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[FirewallMatchConditionSummary]:
    """List firewall match conditions, optionally by parent term.

    Args:
        client: NautobotClient instance.
        term_id: Filter by parent firewall term UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[FirewallMatchConditionSummary].
    """
    try:
        extra: dict = {}
        if term_id:
            extra["term"] = term_id
        return cms_list(
            client, "juniper_firewall_match_conditions", FirewallMatchConditionSummary, limit=limit, **extra
        )
    except Exception as e:
        client._handle_api_error(e, "list", "FirewallMatchCondition")
        raise


def get_firewall_match_condition(client: NautobotClient, id: str) -> FirewallMatchConditionSummary:
    """Get a single firewall match condition by UUID."""
    try:
        return cms_get(client, "juniper_firewall_match_conditions", FirewallMatchConditionSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "FirewallMatchCondition")
        raise


# ---------------------------------------------------------------------------
# Firewall Match Condition → Prefix List (list/get — read-only)
# ---------------------------------------------------------------------------


def list_firewall_match_condition_prefix_lists(
    client: NautobotClient,
    match_condition_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[FirewallMatchConditionToPrefixListSummary]:
    """List firewall match condition to prefix list associations.

    Args:
        client: NautobotClient instance.
        match_condition_id: Filter by parent match condition UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[FirewallMatchConditionToPrefixListSummary].
    """
    try:
        extra: dict = {}
        if match_condition_id:
            extra["match_condition"] = match_condition_id
        return cms_list(
            client,
            "juniper_firewall_match_condition_prefix_lists",
            FirewallMatchConditionToPrefixListSummary,
            limit=limit,
            **extra,
        )
    except Exception as e:
        client._handle_api_error(e, "list", "FirewallMatchConditionPrefixList")
        raise


def get_firewall_match_condition_prefix_list(
    client: NautobotClient, id: str
) -> FirewallMatchConditionToPrefixListSummary:
    """Get a single firewall match condition to prefix list association by UUID."""
    try:
        return cms_get(
            client,
            "juniper_firewall_match_condition_prefix_lists",
            FirewallMatchConditionToPrefixListSummary,
            id=id,
        )
    except Exception as e:
        client._handle_api_error(e, "get", "FirewallMatchConditionPrefixList")
        raise


# ---------------------------------------------------------------------------
# Firewall Filter Actions (list/get — read-only)
# ---------------------------------------------------------------------------


def list_firewall_filter_actions(
    client: NautobotClient,
    term_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[FirewallFilterActionSummary]:
    """List firewall filter actions, optionally by parent term.

    Args:
        client: NautobotClient instance.
        term_id: Filter by parent firewall term UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[FirewallFilterActionSummary].
    """
    try:
        extra: dict = {}
        if term_id:
            extra["term"] = term_id
        return cms_list(client, "juniper_firewall_actions", FirewallFilterActionSummary, limit=limit, **extra)
    except Exception as e:
        client._handle_api_error(e, "list", "FirewallFilterAction")
        raise


def get_firewall_filter_action(client: NautobotClient, id: str) -> FirewallFilterActionSummary:
    """Get a single firewall filter action by UUID."""
    try:
        return cms_get(client, "juniper_firewall_actions", FirewallFilterActionSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "FirewallFilterAction")
        raise


# ---------------------------------------------------------------------------
# Firewall Policer Actions (list/get — read-only)
# ---------------------------------------------------------------------------


def list_firewall_policer_actions(
    client: NautobotClient,
    policer_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[FirewallPolicerActionSummary]:
    """List firewall policer actions, optionally by parent policer.

    Args:
        client: NautobotClient instance.
        policer_id: Filter by parent policer UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[FirewallPolicerActionSummary].
    """
    try:
        extra: dict = {}
        if policer_id:
            extra["policer"] = policer_id
        return cms_list(
            client, "juniper_firewall_policer_actions", FirewallPolicerActionSummary, limit=limit, **extra
        )
    except Exception as e:
        client._handle_api_error(e, "list", "FirewallPolicerAction")
        raise


def get_firewall_policer_action(client: NautobotClient, id: str) -> FirewallPolicerActionSummary:
    """Get a single firewall policer action by UUID."""
    try:
        return cms_get(client, "juniper_firewall_policer_actions", FirewallPolicerActionSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "FirewallPolicerAction")
        raise
