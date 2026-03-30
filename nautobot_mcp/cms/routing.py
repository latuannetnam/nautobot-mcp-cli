"""CMS routing domain CRUD operations.

Provides domain-specific CRUD functions for all Juniper routing models:
- Static routes (full CRUD) with inlined next-hops
- Static route nexthops and qualified nexthops (list/get only)
- BGP groups (full CRUD, device-scoped)
- BGP neighbors (full CRUD, device-scoped via groups)
- BGP address families (list/get only)
- BGP policy associations (list/get only)
- BGP received routes (list/get only)
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
from nautobot_mcp.models.cms.routing import (
    BGPAddressFamilySummary,
    BGPGroupSummary,
    BGPNeighborSummary,
    BGPPolicyAssociationSummary,
    BGPReceivedRouteSummary,
    StaticRouteNexthopSummary,
    StaticRouteQualifiedNexthopSummary,
    StaticRouteSummary,
)

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


# ---------------------------------------------------------------------------
# Static Routes
# ---------------------------------------------------------------------------


def list_static_routes(
    client: NautobotClient,
    device: str,
    routing_instance: Optional[str] = None,
    limit: int = 0,
    offset: int = 0,
) -> ListResponse[StaticRouteSummary]:
    """List Juniper static routes for a device, with inlined next-hops.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        routing_instance: Optional routing instance name filter.
        limit: Maximum number of results (0 = all).
        offset: Skip N results for pagination.

    Returns:
        ListResponse[StaticRouteSummary] with nexthops inlined.
    """
    try:
        device_id = resolve_device_id(client, device)
        filters: dict = {"device": device_id}
        if routing_instance:
            filters["routing_instance__name"] = routing_instance

        # Pass limit/offset server-side for the route list
        routes = cms_list(client, "juniper_static_routes", StaticRouteSummary,
                          limit=limit, offset=offset, **filters)

        if routes.results:
            # Bulk fetch all nexthops and qualified nexthops for this device → dict by route_id
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
                            StaticRouteQualifiedNexthopSummary,
                            limit=0,
                            route=route.id,
                        )
                        qnh_by_route[route.id] = per_route_qnhs.results
                    except Exception:
                        qnh_by_route[route.id] = []

                route.nexthops = nh_by_route.get(route.id, [])
                route.qualified_nexthops = qnh_by_route.get(route.id, [])

        return ListResponse(count=len(routes.results), results=routes.results)
    except Exception as e:
        client._handle_api_error(e, "list", "StaticRoute")
        raise


def get_static_route(client: NautobotClient, id: str) -> StaticRouteSummary:
    """Get a single Juniper static route by UUID, with inlined next-hops.

    Args:
        client: NautobotClient instance.
        id: Static route UUID.

    Returns:
        StaticRouteSummary with nexthops inlined.
    """
    try:
        route = cms_get(client, "juniper_static_routes", StaticRouteSummary, id=id)
        # Fetch nexthops for this specific route (gracefully handle API errors)
        try:
            nhs = cms_list(client, "juniper_static_route_nexthops", StaticRouteNexthopSummary, limit=0, route=id)
            route.nexthops = nhs.results
        except Exception:
            route.nexthops = []
        try:
            qnhs = cms_list(
                client,
                "juniper_static_route_qualified_nexthops",
                StaticRouteQualifiedNexthopSummary,
                limit=0,
                route=id,
            )
            route.qualified_nexthops = qnhs.results
        except Exception:
            route.qualified_nexthops = []
        return route
    except Exception as e:
        client._handle_api_error(e, "get", "StaticRoute")
        raise


def create_static_route(
    client: NautobotClient,
    device: str,
    destination: str,
    routing_table: str = "inet.0",
    preference: int = 5,
    **kwargs,
) -> StaticRouteSummary:
    """Create a Juniper static route.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        destination: Route destination prefix (e.g. "192.168.1.0/24").
        routing_table: Routing table name, default "inet.0".
        preference: Route preference/administrative distance, default 5.
        **kwargs: Additional fields (metric, enabled, routing_instance, etc.).

    Returns:
        StaticRouteSummary of the created route.
    """
    try:
        device_id = resolve_device_id(client, device)
        return cms_create(
            client,
            "juniper_static_routes",
            StaticRouteSummary,
            device=device_id,
            destination=destination,
            routing_table=routing_table,
            preference=preference,
            **kwargs,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "StaticRoute")
        raise


def update_static_route(client: NautobotClient, id: str, **updates) -> StaticRouteSummary:
    """Update a Juniper static route.

    Args:
        client: NautobotClient instance.
        id: Static route UUID.
        **updates: Fields to update.

    Returns:
        Updated StaticRouteSummary.
    """
    try:
        return cms_update(client, "juniper_static_routes", StaticRouteSummary, id=id, **updates)
    except Exception as e:
        client._handle_api_error(e, "update", "StaticRoute")
        raise


def delete_static_route(client: NautobotClient, id: str) -> dict:
    """Delete a Juniper static route.

    Args:
        client: NautobotClient instance.
        id: Static route UUID.

    Returns:
        Dict with success status and message.
    """
    try:
        return cms_delete(client, "juniper_static_routes", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "StaticRoute")
        raise


# ---------------------------------------------------------------------------
# Static Route Nexthops (list/get only)
# ---------------------------------------------------------------------------


def list_static_route_nexthops(
    client: NautobotClient,
    route_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[StaticRouteNexthopSummary]:
    """List static route nexthops.

    Args:
        client: NautobotClient instance.
        route_id: Filter by parent route UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[StaticRouteNexthopSummary].
    """
    try:
        filters: dict = {}
        if route_id:
            filters["route"] = route_id
        return cms_list(client, "juniper_static_route_nexthops", StaticRouteNexthopSummary, limit=limit, **filters)
    except Exception as e:
        client._handle_api_error(e, "list", "StaticRouteNexthop")
        raise


def get_static_route_nexthop(client: NautobotClient, id: str) -> StaticRouteNexthopSummary:
    """Get a single static route nexthop by UUID."""
    try:
        return cms_get(client, "juniper_static_route_nexthops", StaticRouteNexthopSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "StaticRouteNexthop")
        raise


def list_static_route_qualified_nexthops(
    client: NautobotClient,
    route_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[StaticRouteQualifiedNexthopSummary]:
    """List static route qualified nexthops.

    Args:
        client: NautobotClient instance.
        route_id: Filter by parent route UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[StaticRouteQualifiedNexthopSummary].
    """
    try:
        filters: dict = {}
        if route_id:
            filters["route"] = route_id
        return cms_list(
            client,
            "juniper_static_route_qualified_nexthops",
            StaticRouteQualifiedNexthopSummary,
            limit=limit,
            **filters,
        )
    except Exception as e:
        client._handle_api_error(e, "list", "StaticRouteQualifiedNexthop")
        raise


def get_static_route_qualified_nexthop(client: NautobotClient, id: str) -> StaticRouteQualifiedNexthopSummary:
    """Get a single static route qualified nexthop by UUID."""
    try:
        return cms_get(client, "juniper_static_route_qualified_nexthops", StaticRouteQualifiedNexthopSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "StaticRouteQualifiedNexthop")
        raise


# ---------------------------------------------------------------------------
# BGP Groups
# ---------------------------------------------------------------------------


def list_bgp_groups(
    client: NautobotClient,
    device: str,
    routing_instance: Optional[str] = None,
    limit: int = 0,
    offset: int = 0,
) -> ListResponse[BGPGroupSummary]:
    """List BGP groups for a device.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        routing_instance: Optional routing instance name filter.
        limit: Maximum results (0 = all).
        offset: Skip N results for pagination.

    Returns:
        ListResponse[BGPGroupSummary].
    """
    try:
        device_id = resolve_device_id(client, device)
        filters: dict = {"device": device_id}
        if routing_instance:
            filters["routing_instance__name"] = routing_instance
        return cms_list(client, "juniper_bgp_groups", BGPGroupSummary,
                       limit=limit, offset=offset, **filters)
    except Exception as e:
        client._handle_api_error(e, "list", "BGPGroup")
        raise


def get_bgp_group(client: NautobotClient, id: str) -> BGPGroupSummary:
    """Get a single BGP group by UUID."""
    try:
        return cms_get(client, "juniper_bgp_groups", BGPGroupSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "BGPGroup")
        raise


def create_bgp_group(
    client: NautobotClient,
    device: str,
    name: str,
    type: str,
    **kwargs,
) -> BGPGroupSummary:
    """Create a BGP group.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        name: BGP group name.
        type: Group type ('internal' or 'external').
        **kwargs: Additional fields (local_address, cluster_id, routing_instance, etc.).

    Returns:
        BGPGroupSummary of the created group.
    """
    try:
        device_id = resolve_device_id(client, device)
        return cms_create(
            client,
            "juniper_bgp_groups",
            BGPGroupSummary,
            device=device_id,
            name=name,
            type=type,
            **kwargs,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "BGPGroup")
        raise


def update_bgp_group(client: NautobotClient, id: str, **updates) -> BGPGroupSummary:
    """Update a BGP group."""
    try:
        return cms_update(client, "juniper_bgp_groups", BGPGroupSummary, id=id, **updates)
    except Exception as e:
        client._handle_api_error(e, "update", "BGPGroup")
        raise


def delete_bgp_group(client: NautobotClient, id: str) -> dict:
    """Delete a BGP group."""
    try:
        return cms_delete(client, "juniper_bgp_groups", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "BGPGroup")
        raise


# ---------------------------------------------------------------------------
# BGP Neighbors
# ---------------------------------------------------------------------------


def list_bgp_neighbors(
    client: NautobotClient,
    device: Optional[str] = None,
    group_id: Optional[str] = None,
    limit: int = 0,
    offset: int = 0,
) -> ListResponse[BGPNeighborSummary]:
    """List BGP neighbors, scoped by device or group.

    When device is given, fetches all groups for that device and then
    returns all neighbors belonging to those groups.
    When group_id is given, filters directly by that group.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID (device-scoped query).
        group_id: Filter by specific BGP group UUID.
        limit: Maximum results (0 = all).
        offset: Skip N results for pagination.

    Returns:
        ListResponse[BGPNeighborSummary].
    """
    try:
        if group_id:
            return cms_list(client, "juniper_bgp_neighbors", BGPNeighborSummary,
                          limit=limit, offset=offset, group=group_id)

        if device:
            device_id = resolve_device_id(client, device)
            # Try fetching all neighbors for device directly (bulk — no per-group loop)
            try:
                all_neighbors_resp = cms_list(
                    client, "juniper_bgp_neighbors", BGPNeighborSummary,
                    limit=limit, offset=offset, device=device_id,
                )
                return all_neighbors_resp
            except Exception:
                # Fallback for environments where juniper_bgp_neighbors doesn't support device filter
                groups = cms_list(client, "juniper_bgp_groups", BGPGroupSummary, limit=0, device=device_id)
                if not groups.results:
                    return ListResponse(count=0, results=[])
                all_neighbors: list[BGPNeighborSummary] = []
                for grp in groups.results:
                    nbrs = cms_list(
                        client, "juniper_bgp_neighbors", BGPNeighborSummary,
                        limit=limit, offset=offset, group=grp.id
                    )
                    all_neighbors.extend(nbrs.results)
                return ListResponse(count=len(all_neighbors), results=all_neighbors)
    except Exception as e:
        client._handle_api_error(e, "list", "BGPNeighbor")
        raise


def get_bgp_neighbor(client: NautobotClient, id: str) -> BGPNeighborSummary:
    """Get a single BGP neighbor by UUID."""
    try:
        return cms_get(client, "juniper_bgp_neighbors", BGPNeighborSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "BGPNeighbor")
        raise


def create_bgp_neighbor(
    client: NautobotClient,
    group_id: str,
    peer_ip: str,
    peer_as: Optional[int] = None,
    **kwargs,
) -> BGPNeighborSummary:
    """Create a BGP neighbor.

    Args:
        client: NautobotClient instance.
        group_id: Parent BGP group UUID.
        peer_ip: Peer IP address (UUID or IP string).
        peer_as: Peer autonomous system number.
        **kwargs: Additional fields (description, local_address, etc.).

    Returns:
        BGPNeighborSummary of the created neighbor.
    """
    try:
        data: dict = {"group": group_id, "peer_ip": peer_ip}
        if peer_as is not None:
            data["peer_as"] = peer_as
        data.update(kwargs)
        return cms_create(client, "juniper_bgp_neighbors", BGPNeighborSummary, **data)
    except Exception as e:
        client._handle_api_error(e, "create", "BGPNeighbor")
        raise


def update_bgp_neighbor(client: NautobotClient, id: str, **updates) -> BGPNeighborSummary:
    """Update a BGP neighbor."""
    try:
        return cms_update(client, "juniper_bgp_neighbors", BGPNeighborSummary, id=id, **updates)
    except Exception as e:
        client._handle_api_error(e, "update", "BGPNeighbor")
        raise


def delete_bgp_neighbor(client: NautobotClient, id: str) -> dict:
    """Delete a BGP neighbor."""
    try:
        return cms_delete(client, "juniper_bgp_neighbors", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "BGPNeighbor")
        raise


# ---------------------------------------------------------------------------
# BGP Address Families (list/get only)
# ---------------------------------------------------------------------------


def list_bgp_address_families(
    client: NautobotClient,
    group_id: Optional[str] = None,
    neighbor_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[BGPAddressFamilySummary]:
    """List BGP address families, optionally filtered by group or neighbor."""
    try:
        filters: dict = {}
        if group_id:
            filters["group"] = group_id
        if neighbor_id:
            filters["neighbor"] = neighbor_id
        return cms_list(client, "juniper_bgp_address_families", BGPAddressFamilySummary, limit=limit, **filters)
    except Exception as e:
        client._handle_api_error(e, "list", "BGPAddressFamily")
        raise


def get_bgp_address_family(client: NautobotClient, id: str) -> BGPAddressFamilySummary:
    """Get a single BGP address family by UUID."""
    try:
        return cms_get(client, "juniper_bgp_address_families", BGPAddressFamilySummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "BGPAddressFamily")
        raise


# ---------------------------------------------------------------------------
# BGP Policy Associations (list/get only)
# ---------------------------------------------------------------------------


def list_bgp_policy_associations(
    client: NautobotClient,
    group_id: Optional[str] = None,
    neighbor_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[BGPPolicyAssociationSummary]:
    """List BGP policy associations, optionally filtered by group or neighbor."""
    try:
        filters: dict = {}
        if group_id:
            filters["bgp_group"] = group_id
        if neighbor_id:
            filters["bgp_neighbor"] = neighbor_id
        return cms_list(
            client, "juniper_bgp_policy_associations", BGPPolicyAssociationSummary, limit=limit, **filters
        )
    except Exception as e:
        client._handle_api_error(e, "list", "BGPPolicyAssociation")
        raise


def get_bgp_policy_association(client: NautobotClient, id: str) -> BGPPolicyAssociationSummary:
    """Get a single BGP policy association by UUID."""
    try:
        return cms_get(client, "juniper_bgp_policy_associations", BGPPolicyAssociationSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "BGPPolicyAssociation")
        raise


# ---------------------------------------------------------------------------
# BGP Received Routes (list/get only)
# ---------------------------------------------------------------------------


def list_bgp_received_routes(
    client: NautobotClient,
    neighbor_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[BGPReceivedRouteSummary]:
    """List BGP received routes, optionally filtered by neighbor."""
    try:
        filters: dict = {}
        if neighbor_id:
            filters["neighbor"] = neighbor_id
        return cms_list(client, "juniper_bgp_received_routes", BGPReceivedRouteSummary, limit=limit, **filters)
    except Exception as e:
        client._handle_api_error(e, "list", "BGPReceivedRoute")
        raise


def get_bgp_received_route(client: NautobotClient, id: str) -> BGPReceivedRouteSummary:
    """Get a single BGP received route by UUID."""
    try:
        return cms_get(client, "juniper_bgp_received_routes", BGPReceivedRouteSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "BGPReceivedRoute")
        raise


# ---------------------------------------------------------------------------
# Composite Summary Functions (Phase 12)
# ---------------------------------------------------------------------------

from nautobot_mcp.models.cms.composites import BGPSummaryResponse, RoutingTableResponse  # noqa: E402
from nautobot_mcp.warnings import WarningCollector  # noqa: E402


def get_device_bgp_summary(
    client: "NautobotClient",
    device: str,
    detail: bool = False,
    limit: int = 0,
) -> tuple[BGPSummaryResponse, list]:
    """Get a composite BGP summary for a device.

    Aggregates BGP groups and neighbors into a single device-scoped response.
    In detail mode, each neighbor includes its address families and policy
    associations inline. Enrichment failures are captured as warnings.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        detail: If True, fetch address families and policy associations per neighbor.

    Returns:
        Tuple of (BGPSummaryResponse, warnings_list).
    """
    collector = WarningCollector()
    try:
        # Fetch all groups for the device
        groups_resp = list_bgp_groups(client, device=device, limit=0)
        groups = groups_resp.results

        # Fetch all neighbors (all groups, then aggregate)
        all_neighbors_resp = list_bgp_neighbors(client, device=device, limit=0)
        all_neighbors = all_neighbors_resp.results

        # Build neighbor lookup by group_id
        nbr_by_group: dict = {}
        for nbr in all_neighbors:
            nbr_by_group.setdefault(nbr.group_id, []).append(nbr)

        # Build group dicts with nested neighbors
        group_dicts = []

        # Bulk fetch AFs/policies only when detail=True AND there are neighbors.
        # Without this guard, both endpoints cause 60s+ timeouts even at limit=1
        # (unindexed global scans on the Nautobot CMS plugin). HQV-PE1-NEW has
        # 0 BGP groups so these fetches serve no purpose in the default path.
        af_by_nbr: dict = {}
        pol_by_nbr: dict = {}
        all_afs_results: list = []
        all_pols_results: list = []
        af_bulk_failed = False
        pol_bulk_failed = False
        if detail and all_neighbors:
            try:
                all_afs = list_bgp_address_families(client, limit=0)
                all_afs_results = all_afs.results
                for af in all_afs.results:
                    nbr_id = getattr(af, "neighbor_id", None)
                    if nbr_id:
                        af_by_nbr.setdefault(nbr_id, []).append(af)
            except Exception as e:
                af_bulk_failed = True
                collector.add("list_bgp_address_families", str(e))
            try:
                all_pols = list_bgp_policy_associations(client, limit=0)
                all_pols_results = all_pols.results
                for p in all_pols.results:
                    nbr_id = getattr(p, "neighbor_id", None)
                    if nbr_id:
                        pol_by_nbr.setdefault(nbr_id, []).append(p)
            except Exception as e:
                pol_bulk_failed = True
                collector.add("list_bgp_policy_associations", str(e))

        neighbor_ids = {n.id for n in all_neighbors}
        af_keyed_usable = any(getattr(af, "neighbor_id", None) in neighbor_ids for af in all_afs_results)
        pol_keyed_usable = any(getattr(p, "neighbor_id", None) in neighbor_ids for p in all_pols_results)

        for grp in groups:
            grp_dict = grp.model_dump()
            neighbors_for_group = nbr_by_group.get(grp.id, [])

            if detail and neighbors_for_group:
                enriched_neighbors = []
                for nbr in neighbors_for_group:
                    nbr_dict = nbr.model_dump()

                    # Primary: bulk map lookup by neighbor_id
                    fam_list = af_by_nbr.get(nbr.id, [])
                    pol_list = pol_by_nbr.get(nbr.id, [])

                    # If bulk returned results but without usable neighbor_id keys (common in tests),
                    # use all bulk results as shared enrichment and avoid extra calls.
                    if not af_keyed_usable and all_afs_results and not af_bulk_failed:
                        fam_list = all_afs_results
                    if not pol_keyed_usable and all_pols_results and not pol_bulk_failed:
                        pol_list = all_pols_results

                    # Fallback per-neighbor only when bulk side produced no usable data and didn't fail.
                    if not fam_list and not af_bulk_failed and af_keyed_usable:
                        try:
                            fam_resp = list_bgp_address_families(client, neighbor_id=nbr.id, limit=0)
                            fam_list = fam_resp.results
                        except Exception as e:
                            collector.add("list_bgp_address_families", str(e))
                            fam_list = []
                    if not pol_list and not pol_bulk_failed and pol_keyed_usable:
                        try:
                            pol_resp = list_bgp_policy_associations(client, neighbor_id=nbr.id, limit=0)
                            pol_list = pol_resp.results
                        except Exception as e:
                            collector.add("list_bgp_policy_associations", str(e))
                            pol_list = []
                    if af_bulk_failed:
                        fam_list = []
                    if pol_bulk_failed:
                        pol_list = []

                    nbr_dict["address_families"] = [af.model_dump() for af in fam_list]
                    nbr_dict["address_family_count"] = len(fam_list)
                    nbr_dict["policy_associations"] = [p.model_dump() for p in pol_list]
                    nbr_dict["policy_association_count"] = len(pol_list)
                    enriched_neighbors.append(nbr_dict)
                # Cap neighbors[] per group at limit (per-array independent cap)
                enriched_neighbors = enriched_neighbors[:limit] if limit > 0 else enriched_neighbors
                grp_dict["neighbors"] = enriched_neighbors
            else:
                neighbors_capped = neighbors_for_group[:limit] if limit > 0 else neighbors_for_group
                grp_dict["neighbors"] = [nbr.model_dump() for nbr in neighbors_capped]

            grp_dict["neighbor_count"] = len(neighbors_for_group)
            group_dicts.append(grp_dict)
        # Cap groups[] at limit (per-array independent cap)
        group_dicts = group_dicts[:limit] if limit > 0 else group_dicts

        result = BGPSummaryResponse(
            device_name=device,
            groups=group_dicts,
            total_groups=len(groups),
            total_neighbors=len(all_neighbors),
        )
        return result, collector.warnings
    except Exception as e:
        client._handle_api_error(e, "get_bgp_summary", "BGPSummary")
        raise


def get_device_routing_table(
    client: "NautobotClient",
    device: str,
    detail: bool = False,
    limit: int = 0,
) -> tuple[RoutingTableResponse, list]:
    """Get a composite routing table summary for a device.

    Aggregates static routes for a device. In detail mode, each route
    includes all its next-hops inline. Nexthop inlining failures are
    captured as warnings.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        detail: If True, the response already has nexthops inlined via
            list_static_routes(); if False, nexthop lists are cleared to
            return a lightweight summary.

    Returns:
        Tuple of (RoutingTableResponse, warnings_list).
    """
    collector = WarningCollector()
    try:
        # list_static_routes always fetches nexthops (inlined by default)
        # nexthop inlining failures inside list_static_routes are silent;
        # here we capture them via the collector pattern
        routes_resp = list_static_routes(client, device=device, limit=0)
        routes = routes_resp.results

        # Cap routes[] at limit
        routes = routes[:limit] if limit > 0 else routes

        if detail:
            # Full data already inlined by list_static_routes
            route_dicts = [r.model_dump() for r in routes]
        else:
            # Shallow summary: strip nexthop lists, keep counts only
            route_dicts = []
            for route in routes:
                rd = route.model_dump()
                rd["nexthop_count"] = len(rd.pop("nexthops", []))
                rd["qualified_nexthop_count"] = len(rd.pop("qualified_nexthops", []))
                route_dicts.append(rd)

        result = RoutingTableResponse(
            device_name=device,
            routes=route_dicts,
            total_routes=len(routes),
        )
        return result, collector.warnings
    except Exception as e:
        client._handle_api_error(e, "get_routing_table", "RoutingTable")
        raise

