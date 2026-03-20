"""CLI commands for IPAM operations: prefixes, addresses, VLANs."""

from __future__ import annotations

from typing import Optional

import typer

from nautobot_mcp import ipam
from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cli.formatters import (
    IP_COLUMNS,
    PREFIX_COLUMNS,
    VLAN_COLUMNS,
    output,
    output_single,
)

ipam_app = typer.Typer(help="IPAM operations (prefixes, addresses, VLANs)")

# --- Prefixes sub-app ---
prefixes_app = typer.Typer(help="IP prefix operations")
ipam_app.add_typer(prefixes_app, name="prefixes")


@prefixes_app.command("list")
def prefixes_list(
    ctx: typer.Context,
    namespace: Optional[str] = typer.Option(None, help="Filter by namespace"),
    location: Optional[str] = typer.Option(None, help="Filter by location"),
    tenant: Optional[str] = typer.Option(None, help="Filter by tenant"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List IP prefixes."""
    try:
        client = get_client_from_ctx(ctx)
        result = ipam.list_prefixes(
            client, namespace=namespace, location=location, tenant=tenant, limit=limit,
        )
        output(result.model_dump(), ctx.obj.get("json", False), PREFIX_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@prefixes_app.command("create")
def prefixes_create(
    ctx: typer.Context,
    prefix: str = typer.Option(..., help="CIDR prefix (e.g., 10.0.0.0/24)"),
    namespace: str = typer.Option("Global", help="Namespace name"),
    status: str = typer.Option("Active", help="Prefix status"),
) -> None:
    """Create a new IP prefix."""
    try:
        client = get_client_from_ctx(ctx)
        result = ipam.create_prefix(
            client, prefix=prefix, namespace=namespace, status=status,
        )
        output_single(result.model_dump(), ctx.obj.get("json", False), PREFIX_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


# --- Addresses sub-app ---
addresses_app = typer.Typer(help="IP address operations")
ipam_app.add_typer(addresses_app, name="addresses")


@addresses_app.command("list")
def addresses_list(
    ctx: typer.Context,
    device: Optional[str] = typer.Option(None, help="Filter by device"),
    interface: Optional[str] = typer.Option(None, help="Filter by interface"),
    prefix: Optional[str] = typer.Option(None, help="Filter by prefix"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List IP addresses."""
    try:
        client = get_client_from_ctx(ctx)
        result = ipam.list_ip_addresses(
            client, device=device, interface=interface, prefix=prefix, limit=limit,
        )
        output(result.model_dump(), ctx.obj.get("json", False), IP_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@addresses_app.command("create")
def addresses_create(
    ctx: typer.Context,
    address: str = typer.Option(..., help="IP with mask (e.g., 10.0.0.1/24)"),
    namespace: str = typer.Option("Global", help="Namespace name"),
    status: str = typer.Option("Active", help="Address status"),
) -> None:
    """Create a new IP address."""
    try:
        client = get_client_from_ctx(ctx)
        result = ipam.create_ip_address(
            client, address=address, namespace=namespace, status=status,
        )
        output_single(result.model_dump(), ctx.obj.get("json", False), IP_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@addresses_app.command("device-ips")
def addresses_device_ips(
    ctx: typer.Context,
    device: str = typer.Argument(help="Device name to query"),
) -> None:
    """Get all IPs assigned to a device's interfaces."""
    try:
        client = get_client_from_ctx(ctx)
        result = ipam.get_device_ips(client, device_name=device)
        data = result.model_dump()
        if ctx.obj.get("json", False):
            import json
            typer.echo(json.dumps(data, indent=2))
        else:
            typer.echo(f"Device: {data['device_name']} — {data['total_ips']} IPs")
            for entry in data["interface_ips"]:
                typer.echo(f"  {entry['interface_name']}: {entry['address']} ({entry['status']})")
            if data.get("unlinked_ips"):
                typer.echo(f"\n  Unlinked IPs: {len(data['unlinked_ips'])}")
                for ip in data["unlinked_ips"]:
                    typer.echo(f"    {ip['address']} ({ip['status']})")
    except Exception as e:
        handle_cli_error(e)


# --- VLANs sub-app ---
vlans_app = typer.Typer(help="VLAN operations")
ipam_app.add_typer(vlans_app, name="vlans")


@vlans_app.command("list")
def vlans_list(
    ctx: typer.Context,
    location: Optional[str] = typer.Option(None, help="Filter by location"),
    tenant: Optional[str] = typer.Option(None, help="Filter by tenant"),
    device: Optional[str] = typer.Option(None, help="Filter by device name"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List VLANs."""
    try:
        client = get_client_from_ctx(ctx)
        result = ipam.list_vlans(
            client, location=location, tenant=tenant,
            device=device, limit=limit,
        )
        output(result.model_dump(), ctx.obj.get("json", False), VLAN_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@vlans_app.command("create")
def vlans_create(
    ctx: typer.Context,
    vid: int = typer.Option(..., help="VLAN ID (1-4094)"),
    name: str = typer.Option(..., help="VLAN name"),
    status: str = typer.Option("Active", help="VLAN status"),
) -> None:
    """Create a new VLAN."""
    try:
        client = get_client_from_ctx(ctx)
        result = ipam.create_vlan(
            client, vid=vid, name=name, status=status,
        )
        output_single(result.model_dump(), ctx.obj.get("json", False), VLAN_COLUMNS)
    except Exception as e:
        handle_cli_error(e)
