"""CLI commands for organization operations: tenants, locations."""

from __future__ import annotations

from typing import Optional

import typer

from nautobot_mcp import organization
from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cli.formatters import (
    LOCATION_COLUMNS,
    TENANT_COLUMNS,
    output,
    output_single,
)

org_app = typer.Typer(help="Organization operations (tenants, locations)")

# --- Tenants sub-app ---
tenants_app = typer.Typer(help="Tenant operations")
org_app.add_typer(tenants_app, name="tenants")


@tenants_app.command("list")
def tenants_list(
    ctx: typer.Context,
    q: Optional[str] = typer.Option(None, help="Search query"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List tenants."""
    try:
        client = get_client_from_ctx(ctx)
        result = organization.list_tenants(client, q=q, limit=limit)
        output(result.model_dump(), ctx.obj.get("json", False), TENANT_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@tenants_app.command("get")
def tenants_get(
    ctx: typer.Context,
    name: Optional[str] = typer.Option(None, help="Tenant name"),
    id: Optional[str] = typer.Option(None, help="Tenant UUID"),
) -> None:
    """Get a single tenant."""
    try:
        client = get_client_from_ctx(ctx)
        result = organization.get_tenant(client, name=name, id=id)
        output_single(result.model_dump(), ctx.obj.get("json", False), TENANT_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@tenants_app.command("create")
def tenants_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Tenant name"),
) -> None:
    """Create a new tenant."""
    try:
        client = get_client_from_ctx(ctx)
        result = organization.create_tenant(client, name=name)
        output_single(result.model_dump(), ctx.obj.get("json", False), TENANT_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@tenants_app.command("update")
def tenants_update(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Tenant UUID"),
    name: Optional[str] = typer.Option(None, help="New name"),
    description: Optional[str] = typer.Option(None, help="New description"),
) -> None:
    """Update an existing tenant."""
    try:
        client = get_client_from_ctx(ctx)
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        result = organization.update_tenant(client, id=id, **updates)
        output_single(result.model_dump(), ctx.obj.get("json", False), TENANT_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


# --- Locations sub-app ---
locations_app = typer.Typer(help="Location operations")
org_app.add_typer(locations_app, name="locations")


@locations_app.command("list")
def locations_list(
    ctx: typer.Context,
    location_type: Optional[str] = typer.Option(None, "--type", help="Filter by location type"),
    parent: Optional[str] = typer.Option(None, help="Filter by parent location"),
    tenant: Optional[str] = typer.Option(None, help="Filter by tenant"),
    q: Optional[str] = typer.Option(None, help="Search query"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List locations."""
    try:
        client = get_client_from_ctx(ctx)
        result = organization.list_locations(
            client, location_type=location_type, parent=parent,
            tenant=tenant, q=q, limit=limit,
        )
        output(result.model_dump(), ctx.obj.get("json", False), LOCATION_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@locations_app.command("get")
def locations_get(
    ctx: typer.Context,
    name: Optional[str] = typer.Option(None, help="Location name"),
    id: Optional[str] = typer.Option(None, help="Location UUID"),
) -> None:
    """Get a single location."""
    try:
        client = get_client_from_ctx(ctx)
        result = organization.get_location(client, name=name, id=id)
        output_single(result.model_dump(), ctx.obj.get("json", False), LOCATION_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@locations_app.command("create")
def locations_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Location name"),
    location_type: str = typer.Option(..., "--type", help="Location type name"),
    status: str = typer.Option("Active", help="Location status"),
) -> None:
    """Create a new location."""
    try:
        client = get_client_from_ctx(ctx)
        result = organization.create_location(
            client, name=name, location_type=location_type, status=status,
        )
        output_single(result.model_dump(), ctx.obj.get("json", False), LOCATION_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@locations_app.command("update")
def locations_update(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Location UUID"),
    name: Optional[str] = typer.Option(None, help="New name"),
    status: Optional[str] = typer.Option(None, help="New status"),
) -> None:
    """Update an existing location."""
    try:
        client = get_client_from_ctx(ctx)
        updates = {}
        if name is not None:
            updates["name"] = name
        if status is not None:
            updates["status"] = status
        result = organization.update_location(client, id=id, **updates)
        output_single(result.model_dump(), ctx.obj.get("json", False), LOCATION_COLUMNS)
    except Exception as e:
        handle_cli_error(e)
