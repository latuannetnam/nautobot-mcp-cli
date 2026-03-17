"""CLI commands for interface operations."""

from __future__ import annotations

from typing import Optional

import typer

from nautobot_mcp import interfaces
from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cli.formatters import INTERFACE_COLUMNS, output, output_single

interfaces_app = typer.Typer(help="Interface operations")


@interfaces_app.command("list")
def interfaces_list(
    ctx: typer.Context,
    device: Optional[str] = typer.Option(None, help="Filter by device name"),
    device_id: Optional[str] = typer.Option(None, help="Filter by device UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List interfaces with optional device filtering."""
    try:
        client = get_client_from_ctx(ctx)
        result = interfaces.list_interfaces(
            client, device_name=device, device_id=device_id, limit=limit,
        )
        output(result.model_dump(), ctx.obj.get("json", False), INTERFACE_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_app.command("get")
def interfaces_get(
    ctx: typer.Context,
    id: Optional[str] = typer.Option(None, help="Interface UUID"),
    device_name: Optional[str] = typer.Option(None, "--device", help="Device name"),
    name: Optional[str] = typer.Option(None, help="Interface name"),
) -> None:
    """Get a single interface by ID or device+name."""
    try:
        client = get_client_from_ctx(ctx)
        result = interfaces.get_interface(
            client, id=id, device_name=device_name, name=name,
        )
        output_single(result.model_dump(), ctx.obj.get("json", False), INTERFACE_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_app.command("create")
def interfaces_create(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name"),
    name: str = typer.Option(..., help="Interface name"),
    type: str = typer.Option("1000base-t", "--type", help="Interface type"),
) -> None:
    """Create a new interface on a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = interfaces.create_interface(
            client, device=device, name=name, type=type,
        )
        output_single(result.model_dump(), ctx.obj.get("json", False), INTERFACE_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_app.command("update")
def interfaces_update(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Interface UUID"),
    name: Optional[str] = typer.Option(None, help="New name"),
    description: Optional[str] = typer.Option(None, help="New description"),
) -> None:
    """Update an existing interface."""
    try:
        client = get_client_from_ctx(ctx)
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        result = interfaces.update_interface(client, id=id, **updates)
        output_single(result.model_dump(), ctx.obj.get("json", False), INTERFACE_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@interfaces_app.command("assign-ip")
def interfaces_assign_ip(
    ctx: typer.Context,
    interface_id: str = typer.Option(..., help="Interface UUID"),
    ip_address_id: str = typer.Option(..., help="IP address UUID"),
) -> None:
    """Assign an IP address to an interface."""
    try:
        client = get_client_from_ctx(ctx)
        result = interfaces.assign_ip_to_interface(
            client, interface_id=interface_id, ip_address_id=ip_address_id,
        )
        if ctx.obj.get("json", False):
            from nautobot_mcp.cli.formatters import format_json
            print(format_json(result))
        else:
            typer.echo(f"IP assigned: interface={result['interface']}, ip={result['ip_address']}")
    except Exception as e:
        handle_cli_error(e)
