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
) -> ListResponse[StaticRouteSummary]:
    """List Juniper static routes for a device, with inlined next-hops.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        routing_instance: Optional routing instance name filter.
        limit: Maximum number of results (0 = all).

    Returns:
        ListResponse[StaticRouteSummary] with nexthops inlined.
    """
    try:
        device_id = resolve_device_id(client, device)
        filters: dict = {"device": device_id}
        if routing_instance:
            filters["routing_instance__name"] = routing_instance

        routes = cms_list(client, "juniper_static_routes", StaticRouteSummary, limit=0, **filters)

        # Batch-fetch nexthops and qualified nexthops for the device
        nhs = cms_list(client, "juniper_static_route_nexthops", StaticRouteNexthopSummary, limit=0, device=device_id)
        qnhs = cms_list(
            client,
            "juniper_static_route_qualified_nexthops",
            StaticRouteQualifiedNexthopSummary,
            limit=0,
            device=device_id,
        )

        # Build lookup by route_id
        nh_by_route: dict[str, list[StaticRouteNexthopSummary]] = {}
        for nh in nhs.results:
            nh_by_route.setdefault(nh.route_id, []).append(nh)

        qnh_by_route: dict[str, list[StaticRouteQualifiedNexthopSummary]] = {}
        for qnh in qnhs.results:
            qnh_by_route.setdefault(qnh.route_id, []).append(qnh)

        # Inline nexthops into route objects
        for route in routes.results:
            route.nexthops = nh_by_route.get(route.id, [])
            route.qualified_nexthops = qnh_by_route.get(route.id, [])

        # Apply limit after inlining
        all_results = routes.results
        limited = all_results[:limit] if limit > 0 else all_results
        return ListResponse(count=len(all_results), results=limited)
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
        # Fetch nexthops for this specific route
        nhs = cms_list(client, "juniper_static_route_nexthops", StaticRouteNexthopSummary, limit=0, route=id)
        qnhs = cms_list(
            client,
            "juniper_static_route_qualified_nexthops",
            StaticRouteQualifiedNexthopSummary,
            limit=0,
            route=id,
        )
        route.nexthops = nhs.results
        route.qualified_nexthops = qnhs.results
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
    device: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[StaticRouteNexthopSummary]:
    """List static route nexthops.

    Args:
        client: NautobotClient instance.
        route_id: Filter by parent route UUID.
        device: Filter by device name or UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[StaticRouteNexthopSummary].
    """
    try:
        filters: dict = {}
        if route_id:
            filters["route"] = route_id
        if device:
            filters["device"] = resolve_device_id(client, device)
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
    device: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[StaticRouteQualifiedNexthopSummary]:
    """List static route qualified nexthops.

    Args:
        client: NautobotClient instance.
        route_id: Filter by parent route UUID.
        device: Filter by device name or UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[StaticRouteQualifiedNexthopSummary].
    """
    try:
        filters: dict = {}
        if route_id:
            filters["route"] = route_id
        if device:
            filters["device"] = resolve_device_id(client, device)
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
) -> ListResponse[BGPGroupSummary]:
    """List BGP groups for a device.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        routing_instance: Optional routing instance name filter.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[BGPGroupSummary].
    """
    try:
        device_id = resolve_device_id(client, device)
        filters: dict = {"device": device_id}
        if routing_instance:
            filters["routing_instance__name"] = routing_instance
        return cms_list(client, "juniper_bgp_groups", BGPGroupSummary, limit=limit, **filters)
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

    Returns:
        ListResponse[BGPNeighborSummary].
    """
    try:
        if group_id:
            return cms_list(client, "juniper_bgp_neighbors", BGPNeighborSummary, limit=limit, group=group_id)

        if device:
            device_id = resolve_device_id(client, device)
            # Fetch all groups for the device to get their IDs
            groups = cms_list(client, "juniper_bgp_groups", BGPGroupSummary, limit=0, device=device_id)
            if not groups.results:
                return ListResponse(count=0, results=[])

            # Collect all neighbors across all groups
            all_neighbors: list[BGPNeighborSummary] = []
            for grp in groups.results:
                nbrs = cms_list(
                    client, "juniper_bgp_neighbors", BGPNeighborSummary, limit=0, group=grp.id
                )
                all_neighbors.extend(nbrs.results)

            limited = all_neighbors[:limit] if limit > 0 else all_neighbors
            return ListResponse(count=len(all_neighbors), results=limited)

        # No filter — list all (not recommended for large datasets)
        return cms_list(client, "juniper_bgp_neighbors", BGPNeighborSummary, limit=limit)
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


def get_device_bgp_summary(
    client: "NautobotClient",
    device: str,
    detail: bool = False,
) -> BGPSummaryResponse:
    """Get a composite BGP summary for a device.

    Aggregates BGP groups and neighbors into a single device-scoped response.
    In detail mode, each neighbor includes its address families and policy
    associations inline.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        detail: If True, fetch address families and policy associations per neighbor.

    Returns:
        BGPSummaryResponse with groups, neighbors, and counts.
    """
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
        for grp in groups:
            grp_dict = grp.model_dump()
            neighbors_for_group = nbr_by_group.get(grp.id, [])

            if detail and neighbors_for_group:
                # Enrich each neighbor with address families and policy associations
                enriched_neighbors = []
                for nbr in neighbors_for_group:
                    nbr_dict = nbr.model_dump()
                    afs = list_bgp_address_families(client, neighbor_id=nbr.id, limit=0)
                    pols = list_bgp_policy_associations(client, neighbor_id=nbr.id, limit=0)
                    nbr_dict["address_families"] = [af.model_dump() for af in afs.results]
                    nbr_dict["policy_associations"] = [p.model_dump() for p in pols.results]
                    nbr_dict["address_family_count"] = afs.count
                    nbr_dict["policy_association_count"] = pols.count
                    enriched_neighbors.append(nbr_dict)
                grp_dict["neighbors"] = enriched_neighbors
            else:
                grp_dict["neighbors"] = [nbr.model_dump() for nbr in neighbors_for_group]

            grp_dict["neighbor_count"] = len(neighbors_for_group)
            group_dicts.append(grp_dict)

        return BGPSummaryResponse(
            device_name=device,
            groups=group_dicts,
            total_groups=len(groups),
            total_neighbors=len(all_neighbors),
        )
    except Exception as e:
        client._handle_api_error(e, "get_bgp_summary", "BGPSummary")
        raise


def get_device_routing_table(
    client: "NautobotClient",
    device: str,
    detail: bool = False,
) -> RoutingTableResponse:
    """Get a composite routing table summary for a device.

    Aggregates static routes for a device. In detail mode, each route
    includes all its next-hops inline.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        detail: If True, the response already has nexthops inlined via
            list_static_routes(); if False, nexthop lists are cleared to
            return a lightweight summary.

    Returns:
        RoutingTableResponse with routes and counts.
    """
    try:
        # list_static_routes always fetches nexthops (inlined by default)
        routes_resp = list_static_routes(client, device=device, limit=0)
        routes = routes_resp.results

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

        return RoutingTableResponse(
            device_name=device,
            routes=route_dicts,
            total_routes=len(routes),
        )
    except Exception as e:
        client._handle_api_error(e, "get_routing_table", "RoutingTable")
        raise

