"""CLI commands for Juniper CMS routing operations.

Provides commands under: nautobot-mcp cms routing
"""

from __future__ import annotations

import json as json_mod
from typing import Optional

import typer
from tabulate import tabulate

from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cms import routing as cms_routing

routing_app = typer.Typer(help="Juniper routing model operations")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STATIC_ROUTE_COLUMNS = ["destination", "routing_table", "preference", "enabled", "discarded", "routing_instance_name"]
BGP_GROUP_COLUMNS = ["name", "type", "local_address", "cluster_id", "enabled", "routing_instance_name"]
BGP_NEIGHBOR_COLUMNS = ["peer_ip", "peer_as", "group_name", "session_state", "received_prefix_count", "sent_prefix_count", "enabled"]
BGP_AF_COLUMNS = ["address_family", "sub_address_family", "enabled", "prefix_limit_max"]
BGP_PA_COLUMNS = ["policy_name", "policy_type", "order"]
BGP_RR_COLUMNS = ["prefix", "is_active", "as_path", "local_preference", "med", "next_hop"]


def _output(data: dict, json_mode: bool, columns: list) -> None:
    if json_mode:
        typer.echo(json_mod.dumps(data, indent=2, default=str))
        return
    results = data.get("results", [])
    if not results:
        typer.echo("No results found.")
        return
    rows = [[r.get(c, "") for c in columns] for r in results]
    typer.echo(tabulate(rows, headers=columns, tablefmt="simple"))


def _output_single(data: dict, json_mode: bool, columns: list, detail: bool = False) -> None:
    if json_mode:
        typer.echo(json_mod.dumps(data, indent=2, default=str))
        return
    rows = [[data.get(c, "") for c in columns]]
    typer.echo(tabulate(rows, headers=columns, tablefmt="simple"))
    if detail:
        # Show nexthops if present
        nexthops = data.get("nexthops", [])
        if nexthops:
            typer.echo("\nNext-hops:")
            nh_rows = [[nh.get("ip_address", ""), nh.get("nexthop_type", ""), nh.get("weight", 1), nh.get("via_interface_name", "")] for nh in nexthops]
            typer.echo(tabulate(nh_rows, headers=["IP", "Type", "Weight", "Via Interface"], tablefmt="simple"))
        qnexthops = data.get("qualified_nexthops", [])
        if qnexthops:
            typer.echo("\nQualified Next-hops:")
            qnh_rows = [[q.get("ip_address", ""), q.get("nexthop_type", ""), q.get("weight", 1), q.get("interface_name", "")] for q in qnexthops]
            typer.echo(tabulate(qnh_rows, headers=["IP", "Type", "Weight", "Interface"], tablefmt="simple"))
        communities = data.get("communities", "")
        if communities:
            typer.echo(f"\nCommunities: {communities}")


# ===========================================================================
# STATIC ROUTES
# ===========================================================================


@routing_app.command("list-static-routes")
def list_static_routes(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name"),
    routing_instance: Optional[str] = typer.Option(None, "--routing-instance", help="Filter by routing instance name"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
    detail: bool = typer.Option(False, "--detail", help="Show next-hop details inline"),
) -> None:
    """List Juniper static routes for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_routing.list_static_routes(client, device=device, routing_instance=routing_instance, limit=limit)
        data = result.model_dump()
        if detail:
            # Augment columns with nexthop count
            results = data.get("results", [])
            for r in results:
                r["nh_count"] = len(r.get("nexthops", [])) + len(r.get("qualified_nexthops", []))
            cols = STATIC_ROUTE_COLUMNS + ["nh_count"]
            _output(data, ctx.obj.get("json", False), cols)
        else:
            _output(data, ctx.obj.get("json", False), STATIC_ROUTE_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@routing_app.command("get-static-route")
def get_static_route(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Static route UUID"),
    detail: bool = typer.Option(False, "--detail", help="Show inlined next-hops"),
) -> None:
    """Get a single Juniper static route by UUID."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_routing.get_static_route(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False), STATIC_ROUTE_COLUMNS, detail=detail)
    except Exception as e:
        handle_cli_error(e)


@routing_app.command("create-static-route")
def create_static_route(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name"),
    destination: str = typer.Option(..., help="Route destination prefix (e.g. 192.168.1.0/24)"),
    routing_table: str = typer.Option("inet.0", "--routing-table", help="Routing table name"),
    preference: int = typer.Option(5, help="Administrative distance"),
) -> None:
    """Create a Juniper static route."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_routing.create_static_route(
            client, device=device, destination=destination,
            routing_table=routing_table, preference=preference,
        )
        _output_single(result.model_dump(), ctx.obj.get("json", False), STATIC_ROUTE_COLUMNS)
        typer.echo(f"Created static route: {result.destination} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@routing_app.command("delete-static-route")
def delete_static_route(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Static route UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a Juniper static route."""
    try:
        if not yes:
            typer.confirm(f"Delete static route {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_routing.delete_static_route(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# BGP GROUPS
# ===========================================================================


@routing_app.command("list-bgp-groups")
def list_bgp_groups(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name"),
    routing_instance: Optional[str] = typer.Option(None, "--routing-instance", help="Filter by routing instance"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List BGP groups for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_routing.list_bgp_groups(client, device=device, routing_instance=routing_instance, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), BGP_GROUP_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@routing_app.command("get-bgp-group")
def get_bgp_group(
    ctx: typer.Context,
    id: str = typer.Option(..., help="BGP group UUID"),
) -> None:
    """Get a single BGP group by UUID."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_routing.get_bgp_group(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False), BGP_GROUP_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@routing_app.command("create-bgp-group")
def create_bgp_group(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name"),
    name: str = typer.Option(..., help="BGP group name"),
    type: str = typer.Option(..., help="Group type: internal or external"),
    local_address: Optional[str] = typer.Option(None, "--local-address", help="Local address IP UUID"),
    cluster_id: Optional[str] = typer.Option(None, "--cluster-id", help="Cluster ID for route reflector"),
) -> None:
    """Create a BGP group."""
    try:
        client = get_client_from_ctx(ctx)
        kwargs = {}
        if local_address:
            kwargs["local_address"] = local_address
        if cluster_id:
            kwargs["cluster_id"] = cluster_id
        result = cms_routing.create_bgp_group(client, device=device, name=name, type=type, **kwargs)
        _output_single(result.model_dump(), ctx.obj.get("json", False), BGP_GROUP_COLUMNS)
        typer.echo(f"Created BGP group: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@routing_app.command("delete-bgp-group")
def delete_bgp_group(
    ctx: typer.Context,
    id: str = typer.Option(..., help="BGP group UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a BGP group."""
    try:
        if not yes:
            typer.confirm(f"Delete BGP group {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_routing.delete_bgp_group(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# BGP NEIGHBORS
# ===========================================================================


@routing_app.command("list-bgp-neighbors")
def list_bgp_neighbors(
    ctx: typer.Context,
    device: Optional[str] = typer.Option(None, help="Device name (device-scoped query)"),
    group_id: Optional[str] = typer.Option(None, "--group-id", help="Filter by BGP group UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List BGP neighbors for a device or group."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_routing.list_bgp_neighbors(client, device=device, group_id=group_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), BGP_NEIGHBOR_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@routing_app.command("get-bgp-neighbor")
def get_bgp_neighbor(
    ctx: typer.Context,
    id: str = typer.Option(..., help="BGP neighbor UUID"),
) -> None:
    """Get a single BGP neighbor by UUID."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_routing.get_bgp_neighbor(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False), BGP_NEIGHBOR_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@routing_app.command("create-bgp-neighbor")
def create_bgp_neighbor(
    ctx: typer.Context,
    group_id: str = typer.Option(..., "--group-id", help="Parent BGP group UUID"),
    peer_ip: str = typer.Option(..., "--peer-ip", help="Peer IP address UUID or string"),
    peer_as: Optional[int] = typer.Option(None, "--peer-as", help="Peer autonomous system number"),
    description: Optional[str] = typer.Option(None, help="Neighbor description"),
) -> None:
    """Create a BGP neighbor."""
    try:
        client = get_client_from_ctx(ctx)
        kwargs = {}
        if peer_as is not None:
            kwargs["peer_as"] = peer_as
        if description:
            kwargs["description"] = description
        result = cms_routing.create_bgp_neighbor(client, group_id=group_id, peer_ip=peer_ip, **kwargs)
        _output_single(result.model_dump(), ctx.obj.get("json", False), BGP_NEIGHBOR_COLUMNS)
        typer.echo(f"Created BGP neighbor: {result.peer_ip} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@routing_app.command("delete-bgp-neighbor")
def delete_bgp_neighbor(
    ctx: typer.Context,
    id: str = typer.Option(..., help="BGP neighbor UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a BGP neighbor."""
    try:
        if not yes:
            typer.confirm(f"Delete BGP neighbor {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_routing.delete_bgp_neighbor(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# READ-ONLY CHILD MODELS
# ===========================================================================


@routing_app.command("list-bgp-address-families")
def list_bgp_address_families(
    ctx: typer.Context,
    group_id: Optional[str] = typer.Option(None, "--group-id", help="Filter by BGP group UUID"),
    neighbor_id: Optional[str] = typer.Option(None, "--neighbor-id", help="Filter by BGP neighbor UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List BGP address families (read-only)."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_routing.list_bgp_address_families(client, group_id=group_id, neighbor_id=neighbor_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), BGP_AF_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@routing_app.command("list-bgp-policy-associations")
def list_bgp_policy_associations(
    ctx: typer.Context,
    group_id: Optional[str] = typer.Option(None, "--group-id", help="Filter by BGP group UUID"),
    neighbor_id: Optional[str] = typer.Option(None, "--neighbor-id", help="Filter by BGP neighbor UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List BGP policy associations (read-only)."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_routing.list_bgp_policy_associations(client, group_id=group_id, neighbor_id=neighbor_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), BGP_PA_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@routing_app.command("list-bgp-received-routes")
def list_bgp_received_routes(
    ctx: typer.Context,
    neighbor_id: str = typer.Option(..., "--neighbor-id", help="BGP neighbor UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List BGP received routes for a neighbor (read-only)."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_routing.list_bgp_received_routes(client, neighbor_id=neighbor_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), BGP_RR_COLUMNS)
    except Exception as e:
        handle_cli_error(e)
