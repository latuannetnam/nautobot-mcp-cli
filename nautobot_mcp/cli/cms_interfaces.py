"""CLI commands for Juniper CMS interface operations.

Provides commands under: nautobot-mcp cms interfaces
"""

from __future__ import annotations

import json as json_mod
from typing import Optional

import typer
from tabulate import tabulate

from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cms import arp
from nautobot_mcp.cms import interfaces as cms_interfaces

interfaces_cli_app = typer.Typer(help="Juniper interface model operations")


# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

UNIT_COLUMNS = ["interface_name", "unit_number", "vlan_mode", "encapsulation", "description", "family_count"]
FAMILY_COLUMNS = ["unit_display", "family_type", "mtu", "filter_count", "policer_count"]
FILTER_COLUMNS = ["family_id", "filter_name", "filter_type", "enabled"]
POLICER_COLUMNS = ["family_id", "policer_name", "policer_type", "enabled"]
VRRP_GROUP_COLUMNS = ["group_number", "virtual_address", "interface_address", "priority", "accept_data", "family_display"]
VRRP_TRACK_ROUTE_COLUMNS = ["vrrp_group_id", "route_address", "priority_cost", "routing_instance"]
VRRP_TRACK_IFACE_COLUMNS = ["vrrp_group_id", "tracked_interface_name", "priority_cost"]
ARP_COLUMNS = ["mac_address", "ip_address", "interface_name", "hostname", "device_name"]


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


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


def _output_single(data: dict, json_mode: bool, columns: list) -> None:
    if json_mode:
        typer.echo(json_mod.dumps(data, indent=2, default=str))
        return
    rows = [[data.get(c, "") for c in columns]]
    typer.echo(tabulate(rows, headers=columns, tablefmt="simple"))


# ===========================================================================
# INTERFACE UNITS
# ===========================================================================


@interfaces_cli_app.command("list-units")
def list_interface_units(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List Juniper interface units for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.list_interface_units(client, device=device, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), UNIT_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("get-unit")
def get_interface_unit(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Interface unit UUID"),
) -> None:
    """Get a single interface unit with inlined family details."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.get_interface_unit(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False), UNIT_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("create-unit")
def create_interface_unit(
    ctx: typer.Context,
    interface_id: str = typer.Option(..., "--interface-id", help="Parent interface UUID"),
    vlan_mode: Optional[str] = typer.Option(None, "--vlan-mode", help="VLAN mode (access, trunk, etc.)"),
    encapsulation: Optional[str] = typer.Option(None, "--encapsulation", help="Encapsulation type"),
    description: Optional[str] = typer.Option(None, help="Unit description"),
) -> None:
    """Create a Juniper interface unit."""
    try:
        client = get_client_from_ctx(ctx)
        kwargs = {}
        if vlan_mode:
            kwargs["vlan_mode"] = vlan_mode
        if encapsulation:
            kwargs["encapsulation"] = encapsulation
        if description:
            kwargs["description"] = description
        result = cms_interfaces.create_interface_unit(client, interface_id=interface_id, **kwargs)
        _output_single(result.model_dump(), ctx.obj.get("json", False), UNIT_COLUMNS)
        typer.echo(f"Created interface unit {result.unit_number} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("delete-unit")
def delete_interface_unit(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Interface unit UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a Juniper interface unit."""
    try:
        if not yes:
            typer.confirm(f"Delete interface unit {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.delete_interface_unit(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# INTERFACE FAMILIES
# ===========================================================================


@interfaces_cli_app.command("list-families")
def list_interface_families(
    ctx: typer.Context,
    unit_id: Optional[str] = typer.Option(None, "--unit-id", help="Filter by interface unit UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List interface families, optionally filtered by unit."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.list_interface_families(client, unit_id=unit_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), FAMILY_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("get-family")
def get_interface_family(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Interface family UUID"),
) -> None:
    """Get a single interface family by UUID."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.get_interface_family(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False), FAMILY_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("create-family")
def create_interface_family(
    ctx: typer.Context,
    unit_id: str = typer.Option(..., "--unit-id", help="Parent interface unit UUID"),
    family_type: str = typer.Option(..., "--family-type", help="Address family (inet, inet6, mpls, etc.)"),
) -> None:
    """Create a Juniper interface family."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.create_interface_family(client, unit_id=unit_id, family_type=family_type)
        _output_single(result.model_dump(), ctx.obj.get("json", False), FAMILY_COLUMNS)
        typer.echo(f"Created interface family {result.family_type} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("delete-family")
def delete_interface_family(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Interface family UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a Juniper interface family."""
    try:
        if not yes:
            typer.confirm(f"Delete interface family {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.delete_interface_family(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# FILTER ASSOCIATIONS (read-only list/get + create/delete)
# ===========================================================================


@interfaces_cli_app.command("list-filters")
def list_interface_family_filters(
    ctx: typer.Context,
    family_id: Optional[str] = typer.Option(None, "--family-id", help="Filter by interface family UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List interface family filter associations."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.list_interface_family_filters(client, family_id=family_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), FILTER_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("create-filter")
def create_interface_family_filter(
    ctx: typer.Context,
    family_id: str = typer.Option(..., "--family-id", help="Parent interface family UUID"),
    filter_id: str = typer.Option(..., "--filter-id", help="Filter UUID to associate"),
    filter_type: str = typer.Option(..., "--filter-type", help="Filter direction (input, output, etc.)"),
    enabled: bool = typer.Option(True, help="Enable the association"),
) -> None:
    """Create an interface family filter association."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.create_interface_family_filter(
            client, family_id=family_id, filter_id=filter_id,
            filter_type=filter_type, enabled=enabled,
        )
        _output_single(result.model_dump(), ctx.obj.get("json", False), FILTER_COLUMNS)
        typer.echo(f"Created filter association (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("delete-filter")
def delete_interface_family_filter(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Filter association UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete an interface family filter association."""
    try:
        if not yes:
            typer.confirm(f"Delete filter association {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.delete_interface_family_filter(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# POLICER ASSOCIATIONS (read-only list/get + create/delete)
# ===========================================================================


@interfaces_cli_app.command("list-policers")
def list_interface_family_policers(
    ctx: typer.Context,
    family_id: Optional[str] = typer.Option(None, "--family-id", help="Filter by interface family UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List interface family policer associations."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.list_interface_family_policers(client, family_id=family_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), POLICER_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("create-policer")
def create_interface_family_policer(
    ctx: typer.Context,
    family_id: str = typer.Option(..., "--family-id", help="Parent interface family UUID"),
    policer_id: str = typer.Option(..., "--policer-id", help="Policer UUID to associate"),
    policer_type: str = typer.Option(..., "--policer-type", help="Policer direction (input, output, etc.)"),
    enabled: bool = typer.Option(True, help="Enable the association"),
) -> None:
    """Create an interface family policer association."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.create_interface_family_policer(
            client, family_id=family_id, policer_id=policer_id,
            policer_type=policer_type, enabled=enabled,
        )
        _output_single(result.model_dump(), ctx.obj.get("json", False), POLICER_COLUMNS)
        typer.echo(f"Created policer association (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("delete-policer")
def delete_interface_family_policer(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Policer association UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete an interface family policer association."""
    try:
        if not yes:
            typer.confirm(f"Delete policer association {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.delete_interface_family_policer(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# VRRP GROUPS
# ===========================================================================


@interfaces_cli_app.command("list-vrrp-groups")
def list_vrrp_groups(
    ctx: typer.Context,
    device: Optional[str] = typer.Option(None, help="Device name (convenience: lists all VRRP groups for device)"),
    family_id: Optional[str] = typer.Option(None, "--family-id", help="Filter by interface family UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List VRRP groups, optionally scoped by device."""
    try:
        client = get_client_from_ctx(ctx)
        if device and not family_id:
            # Device-scoped: traverse units → families → VRRP groups
            from nautobot_mcp.models.base import ListResponse
            units = cms_interfaces.list_interface_units(client, device=device, limit=0)
            all_vrrp = []
            for unit in units.results:
                families = cms_interfaces.list_interface_families(client, unit_id=unit.id, limit=0)
                for fam in families.results:
                    vrrps = cms_interfaces.list_vrrp_groups(client, family_id=fam.id, limit=0)
                    all_vrrp.extend(vrrps.results)
            limited = all_vrrp[:limit] if limit > 0 else all_vrrp
            result = ListResponse(count=len(all_vrrp), results=limited)
            _output(result.model_dump(), ctx.obj.get("json", False), VRRP_GROUP_COLUMNS)
        else:
            result = cms_interfaces.list_vrrp_groups(client, family_id=family_id, limit=limit)
            _output(result.model_dump(), ctx.obj.get("json", False), VRRP_GROUP_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("get-vrrp-group")
def get_vrrp_group(
    ctx: typer.Context,
    id: str = typer.Option(..., help="VRRP group UUID"),
) -> None:
    """Get a single VRRP group by UUID."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.get_vrrp_group(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False), VRRP_GROUP_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("create-vrrp-group")
def create_vrrp_group(
    ctx: typer.Context,
    family_id: str = typer.Option(..., "--family-id", help="Parent interface family UUID"),
    group_number: int = typer.Option(..., "--group-number", help="VRRP group number (1-255)"),
    virtual_address_id: str = typer.Option(..., "--virtual-address-id", help="Virtual IP address UUID"),
    priority: int = typer.Option(100, help="VRRP priority (1-254)"),
) -> None:
    """Create a VRRP group."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.create_vrrp_group(
            client, family_id=family_id, group_number=group_number,
            virtual_address_id=virtual_address_id, priority=priority,
        )
        _output_single(result.model_dump(), ctx.obj.get("json", False), VRRP_GROUP_COLUMNS)
        typer.echo(f"Created VRRP group {result.group_number} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("delete-vrrp-group")
def delete_vrrp_group(
    ctx: typer.Context,
    id: str = typer.Option(..., help="VRRP group UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a VRRP group."""
    try:
        if not yes:
            typer.confirm(f"Delete VRRP group {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.delete_vrrp_group(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# VRRP TRACKING (read-only)
# ===========================================================================


@interfaces_cli_app.command("list-vrrp-track-routes")
def list_vrrp_track_routes(
    ctx: typer.Context,
    vrrp_group_id: Optional[str] = typer.Option(None, "--vrrp-group-id", help="Filter by VRRP group UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List VRRP tracked routes (read-only)."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.list_vrrp_track_routes(client, vrrp_group_id=vrrp_group_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), VRRP_TRACK_ROUTE_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("list-vrrp-track-interfaces")
def list_vrrp_track_interfaces(
    ctx: typer.Context,
    vrrp_group_id: Optional[str] = typer.Option(None, "--vrrp-group-id", help="Filter by VRRP group UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List VRRP tracked interfaces (read-only)."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_interfaces.list_vrrp_track_interfaces(client, vrrp_group_id=vrrp_group_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), VRRP_TRACK_IFACE_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# ARP (read-only)
# ===========================================================================


@interfaces_cli_app.command("list-arp-entries")
def list_arp_entries(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID (required)"),
    interface: Optional[str] = typer.Option(None, help="Filter by interface name or UUID"),
    mac_address: Optional[str] = typer.Option(None, "--mac-address", help="Filter by MAC address"),
    limit: int = typer.Option(0, help="Max results (0=all)"),
) -> None:
    """List ARP entries for a Juniper device (read-only)."""
    try:
        client = get_client_from_ctx(ctx)
        result = arp.list_arp_entries(
            client, device=device, interface=interface,
            mac_address=mac_address, limit=limit,
        )
        _output(result.model_dump(), ctx.obj.get("json", False), ARP_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_cli_app.command("get-arp-entry")
def get_arp_entry(
    ctx: typer.Context,
    id: str = typer.Option(..., help="ARP entry UUID"),
) -> None:
    """Get a single ARP entry by UUID."""
    try:
        client = get_client_from_ctx(ctx)
        result = arp.get_arp_entry(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False), ARP_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# COMPOSITE SUMMARY
# ===========================================================================


@interfaces_cli_app.command("detail")
def interface_detail(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    include_arp: bool = typer.Option(False, "--include-arp", help="Include ARP entries per interface"),
) -> None:
    """Get composite interface detail summary for a device (units, families, VRRP)."""
    try:
        client = get_client_from_ctx(ctx)
        result, _ = cms_interfaces.get_interface_detail(client, device=device, include_arp=include_arp)
        data = result.model_dump()
        if ctx.obj.get("json", False):
            import json as json_mod
            typer.echo(json_mod.dumps(data, indent=2, default=str))
        else:
            typer.echo(f"Device: {data['device_name']} — Total units: {data['total_units']}")
            for unit in data.get("units", []):
                typer.echo(f"  Unit {unit.get('unit_number', '-')}: {unit.get('interface_name', '-')} "
                           f"[{unit.get('family_count', 0)} families]")
                for fam in unit.get("families", []):
                    vrrp_count = fam.get("vrrp_group_count", 0)
                    typer.echo(f"    {fam.get('family_type', '-')} | VRRP groups: {vrrp_count}")
            if include_arp and data.get("arp_entries"):
                typer.echo(f"  ARP entries ({len(data['arp_entries'])})")
    except Exception as e:
        handle_cli_error(e)
