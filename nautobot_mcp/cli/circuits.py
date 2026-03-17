"""CLI commands for circuit operations."""

from __future__ import annotations

from typing import Optional

import typer

from nautobot_mcp import circuits
from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cli.formatters import CIRCUIT_COLUMNS, output, output_single

circuits_app = typer.Typer(help="Circuit operations")


@circuits_app.command("list")
def circuits_list(
    ctx: typer.Context,
    provider: Optional[str] = typer.Option(None, help="Filter by provider"),
    circuit_type: Optional[str] = typer.Option(None, "--type", help="Filter by circuit type"),
    location: Optional[str] = typer.Option(None, help="Filter by location"),
    q: Optional[str] = typer.Option(None, help="Search query"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List circuits."""
    try:
        client = get_client_from_ctx(ctx)
        result = circuits.list_circuits(
            client, provider=provider, circuit_type=circuit_type,
            location=location, q=q, limit=limit,
        )
        output(result.model_dump(), ctx.obj.get("json", False), CIRCUIT_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@circuits_app.command("get")
def circuits_get(
    ctx: typer.Context,
    cid: Optional[str] = typer.Option(None, help="Circuit ID string"),
    id: Optional[str] = typer.Option(None, help="Circuit UUID"),
) -> None:
    """Get a single circuit."""
    try:
        client = get_client_from_ctx(ctx)
        result = circuits.get_circuit(client, cid=cid, id=id)
        output_single(result.model_dump(), ctx.obj.get("json", False), CIRCUIT_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@circuits_app.command("create")
def circuits_create(
    ctx: typer.Context,
    cid: str = typer.Option(..., help="Circuit identifier"),
    provider: str = typer.Option(..., help="Provider name"),
    circuit_type: str = typer.Option(..., "--type", help="Circuit type name"),
    status: str = typer.Option("Active", help="Circuit status"),
) -> None:
    """Create a new circuit."""
    try:
        client = get_client_from_ctx(ctx)
        result = circuits.create_circuit(
            client, cid=cid, provider=provider, circuit_type=circuit_type,
            status=status,
        )
        output_single(result.model_dump(), ctx.obj.get("json", False), CIRCUIT_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@circuits_app.command("update")
def circuits_update(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Circuit UUID"),
    cid: Optional[str] = typer.Option(None, help="New circuit ID"),
    status: Optional[str] = typer.Option(None, help="New status"),
) -> None:
    """Update an existing circuit."""
    try:
        client = get_client_from_ctx(ctx)
        updates = {}
        if cid is not None:
            updates["cid"] = cid
        if status is not None:
            updates["status"] = status
        result = circuits.update_circuit(client, id=id, **updates)
        output_single(result.model_dump(), ctx.obj.get("json", False), CIRCUIT_COLUMNS)
    except Exception as e:
        handle_cli_error(e)
