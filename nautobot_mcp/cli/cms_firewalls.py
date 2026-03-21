"""CLI commands for Juniper CMS firewall operations.

Provides commands under: nautobot-mcp cms firewalls
"""

from __future__ import annotations

import json as json_mod
from typing import Optional

import typer
from tabulate import tabulate

from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cms import firewalls as cms_firewalls

firewalls_app = typer.Typer(help="Juniper firewall filter and policer management.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FILTER_COLUMNS = ["name", "family", "description", "term_count"]
POLICER_COLUMNS = ["name", "description", "action_count"]
TERM_COLUMNS = ["name", "order", "match_count", "action_count", "filter_name"]
MC_COLUMNS = ["id", "source_addresses", "destination_addresses", "protocols", "term_name"]
ACTION_COLUMNS = ["id", "action_type", "policer_name", "term_name"]
POLICER_ACTION_COLUMNS = ["id", "action_type", "value", "policer_name"]


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


def _output_single(data: dict, json_mode: bool) -> None:
    if json_mode:
        typer.echo(json_mod.dumps(data, indent=2, default=str))
        return
    for k, v in data.items():
        if isinstance(v, list):
            typer.echo(f"{k}: [{len(v)} items]")
        else:
            typer.echo(f"{k}: {v}")


# ===========================================================================
# FIREWALL FILTERS
# ===========================================================================


@firewalls_app.command("list-filters")
def list_filters(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    family: Optional[str] = typer.Option(None, help="Address family filter (inet, inet6, vpls)"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
    detail: bool = typer.Option(False, "--detail", help="Show term names inline"),
) -> None:
    """List firewall filters for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_firewalls.list_firewall_filters(client, device=device, family=family, limit=limit)
        data = result.model_dump()
        if detail:
            cols = FILTER_COLUMNS
        else:
            cols = ["name", "family", "term_count"]
        _output(data, ctx.obj.get("json", False), cols)
    except Exception as e:
        handle_cli_error(e)


@firewalls_app.command("get-filter")
def get_filter(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Firewall filter UUID"),
) -> None:
    """Get a firewall filter with inlined term details."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_firewalls.get_firewall_filter(client, id=id)
        data = result.model_dump()
        _output_single(data, ctx.obj.get("json", False))
        terms = getattr(result, "terms", [])
        if terms:
            typer.echo("\nTerms:")
            term_rows = [[t.name, t.match_count, t.action_count] for t in terms]
            typer.echo(tabulate(term_rows, headers=["Name", "Matches", "Actions"], tablefmt="simple"))
    except Exception as e:
        handle_cli_error(e)


@firewalls_app.command("create-filter")
def create_filter(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    name: str = typer.Option(..., help="Filter name"),
    family: str = typer.Option("inet", help="Address family (inet, inet6, vpls)"),
    description: Optional[str] = typer.Option(None, help="Filter description"),
) -> None:
    """Create a Juniper firewall filter."""
    try:
        client = get_client_from_ctx(ctx)
        kwargs = {}
        if description:
            kwargs["description"] = description
        result = cms_firewalls.create_firewall_filter(client, device=device, name=name, family=family, **kwargs)
        typer.echo(f"Created firewall filter: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@firewalls_app.command("update-filter")
def update_filter(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Filter UUID"),
    name: Optional[str] = typer.Option(None, help="New name"),
    description: Optional[str] = typer.Option(None, help="New description"),
) -> None:
    """Update a Juniper firewall filter."""
    try:
        client = get_client_from_ctx(ctx)
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        result = cms_firewalls.update_firewall_filter(client, id=id, **updates)
        typer.echo(f"Updated firewall filter: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@firewalls_app.command("delete-filter")
def delete_filter(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Filter UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a Juniper firewall filter."""
    try:
        if not yes:
            typer.confirm(f"Delete firewall filter {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_firewalls.delete_firewall_filter(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# FIREWALL POLICERS
# ===========================================================================


@firewalls_app.command("list-policers")
def list_policers(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List firewall policers for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_firewalls.list_firewall_policers(client, device=device, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), POLICER_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@firewalls_app.command("get-policer")
def get_policer(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Policer UUID"),
) -> None:
    """Get a firewall policer with inlined actions."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_firewalls.get_firewall_policer(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False))
    except Exception as e:
        handle_cli_error(e)


@firewalls_app.command("create-policer")
def create_policer(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    name: str = typer.Option(..., help="Policer name"),
    description: Optional[str] = typer.Option(None, help="Policer description"),
) -> None:
    """Create a Juniper firewall policer."""
    try:
        client = get_client_from_ctx(ctx)
        kwargs = {}
        if description:
            kwargs["description"] = description
        result = cms_firewalls.create_firewall_policer(client, device=device, name=name, **kwargs)
        typer.echo(f"Created firewall policer: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@firewalls_app.command("update-policer")
def update_policer(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Policer UUID"),
    name: Optional[str] = typer.Option(None, help="New name"),
    description: Optional[str] = typer.Option(None, help="New description"),
) -> None:
    """Update a Juniper firewall policer."""
    try:
        client = get_client_from_ctx(ctx)
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        result = cms_firewalls.update_firewall_policer(client, id=id, **updates)
        typer.echo(f"Updated firewall policer: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@firewalls_app.command("delete-policer")
def delete_policer(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Policer UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a Juniper firewall policer."""
    try:
        if not yes:
            typer.confirm(f"Delete firewall policer {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_firewalls.delete_firewall_policer(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# READ-ONLY SUB-MODELS
# ===========================================================================


@firewalls_app.command("list-terms")
def list_terms(
    ctx: typer.Context,
    filter_id: Optional[str] = typer.Option(None, "--filter-id", help="Filter by parent firewall filter UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List firewall terms (read-only), optionally by parent filter."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_firewalls.list_firewall_terms(client, filter_id=filter_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), TERM_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@firewalls_app.command("get-term")
def get_term(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Term UUID"),
) -> None:
    """Get a firewall term with inlined match conditions and actions."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_firewalls.get_firewall_term(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False))
    except Exception as e:
        handle_cli_error(e)


@firewalls_app.command("list-match-conditions")
def list_match_conditions(
    ctx: typer.Context,
    term_id: Optional[str] = typer.Option(None, "--term-id", help="Filter by parent term UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List firewall match conditions (read-only)."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_firewalls.list_firewall_match_conditions(client, term_id=term_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), MC_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@firewalls_app.command("list-filter-actions")
def list_filter_actions(
    ctx: typer.Context,
    term_id: Optional[str] = typer.Option(None, "--term-id", help="Filter by parent term UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List firewall filter actions (read-only)."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_firewalls.list_firewall_filter_actions(client, term_id=term_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), ACTION_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@firewalls_app.command("list-policer-actions")
def list_policer_actions(
    ctx: typer.Context,
    policer_id: Optional[str] = typer.Option(None, "--policer-id", help="Filter by parent policer UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List firewall policer actions (read-only)."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_firewalls.list_firewall_policer_actions(client, policer_id=policer_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), POLICER_ACTION_COLUMNS)
    except Exception as e:
        handle_cli_error(e)
