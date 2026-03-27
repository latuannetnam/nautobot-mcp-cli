"""CLI commands for device operations."""

from __future__ import annotations

from typing import Optional

import typer

from nautobot_mcp import devices
from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cli.formatters import DEVICE_COLUMNS, output, output_single

devices_app = typer.Typer(help="Device operations")


@devices_app.command("list")
def devices_list(
    ctx: typer.Context,
    location: Optional[str] = typer.Option(None, help="Filter by location"),
    tenant: Optional[str] = typer.Option(None, help="Filter by tenant"),
    role: Optional[str] = typer.Option(None, help="Filter by device role"),
    platform: Optional[str] = typer.Option(None, help="Filter by platform"),
    q: Optional[str] = typer.Option(None, help="Search query"),
    limit: Optional[int] = typer.Option(None, help="Server-side max results (0=all, default=default_limit from config)"),
    offset: int = typer.Option(0, help="Skip N results for pagination"),
) -> None:
    """List devices with optional filtering."""
    try:
        client = get_client_from_ctx(ctx)
        settings = ctx.obj.get("settings")
        effective_limit = limit if limit is not None else (settings.default_limit if settings else 50)
        result = devices.list_devices(
            client, location=location, tenant=tenant, role=role,
            platform=platform, q=q, limit=effective_limit, offset=offset,
        )
        output(result.model_dump(), ctx.obj.get("json", False), DEVICE_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@devices_app.command("get")
def devices_get(
    ctx: typer.Context,
    name: Optional[str] = typer.Option(None, help="Device name"),
    id: Optional[str] = typer.Option(None, help="Device UUID"),
) -> None:
    """Get a single device by name or ID."""
    try:
        client = get_client_from_ctx(ctx)
        result = devices.get_device(client, name=name, id=id)
        output_single(result.model_dump(), ctx.obj.get("json", False), DEVICE_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@devices_app.command("create")
def devices_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Device hostname"),
    device_type: str = typer.Option(..., "--type", help="Device type name"),
    location: str = typer.Option(..., help="Location name"),
    role: str = typer.Option(..., help="Device role name"),
    status: str = typer.Option("Active", help="Device status"),
) -> None:
    """Create a new device."""
    try:
        client = get_client_from_ctx(ctx)
        result = devices.create_device(
            client, name=name, device_type=device_type,
            location=location, role=role, status=status,
        )
        output_single(result.model_dump(), ctx.obj.get("json", False), DEVICE_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@devices_app.command("update")
def devices_update(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Device UUID"),
    name: Optional[str] = typer.Option(None, help="New hostname"),
    status: Optional[str] = typer.Option(None, help="New status"),
    role: Optional[str] = typer.Option(None, help="New role"),
) -> None:
    """Update an existing device."""
    try:
        client = get_client_from_ctx(ctx)
        updates = {}
        if name is not None:
            updates["name"] = name
        if status is not None:
            updates["status"] = status
        if role is not None:
            updates["role"] = role
        result = devices.update_device(client, id=id, **updates)
        output_single(result.model_dump(), ctx.obj.get("json", False), DEVICE_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@devices_app.command("delete")
def devices_delete(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Device UUID"),
) -> None:
    """Delete a device."""
    try:
        client = get_client_from_ctx(ctx)
        devices.delete_device(client, id=id)
        typer.echo("Device deleted successfully.")
    except Exception as e:
        handle_cli_error(e)


@devices_app.command("summary")
def devices_summary(
    ctx: typer.Context,
    name: str = typer.Argument(help="Device name"),
    detail: bool = typer.Option(False, "--detail", help="Show full interface/IP breakdown"),
) -> None:
    """Get complete device overview with counts and stats."""
    try:
        client = get_client_from_ctx(ctx)
        result = devices.get_device_summary(client, name=name)
        data = result.model_dump()

        if ctx.obj.get("json", False):
            import json
            typer.echo(json.dumps(data, indent=2))
            return

        # Always show compact overview
        d = data["device"]
        typer.echo(f"Device: {d['name']} ({d['status']})")
        typer.echo(f"  Type: {d['device_type']['name']} | Location: {d['location']['name']}")
        if d.get("platform"):
            typer.echo(f"  Platform: {d['platform']}")
        if d.get("primary_ip"):
            typer.echo(f"  Primary IP: {d['primary_ip']}")
        typer.echo(f"\n  Interfaces: {data['interface_count']} (↑{data['enabled_count']} ↓{data['disabled_count']})")
        typer.echo(f"  IP Addresses: {data['ip_count']}")
        typer.echo(f"  VLANs: {data['vlan_count']}")

        if detail:
            typer.echo("\n  --- Interfaces ---")
            for iface in data["interfaces"]:
                status = "↑" if iface["enabled"] else "↓"
                desc = f" — {iface['description']}" if iface.get("description") else ""
                typer.echo(f"  {status} {iface['name']} ({iface['type']}){desc}")
            if data["interface_ips"]:
                typer.echo("\n  --- IP Assignments ---")
                for ip in data["interface_ips"]:
                    typer.echo(f"  {ip['interface_name']}: {ip['address']} ({ip['status']})")
            if data["vlans"]:
                typer.echo("\n  --- VLANs ---")
                for vlan in data["vlans"]:
                    typer.echo(f"  VLAN {vlan['vid']}: {vlan['name']} ({vlan['status']})")

    except Exception as e:
        handle_cli_error(e)
