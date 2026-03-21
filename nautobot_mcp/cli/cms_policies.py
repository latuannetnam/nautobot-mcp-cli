"""CLI commands for Juniper CMS policy operations.

Provides commands under: nautobot-mcp cms policies
"""

from __future__ import annotations

import json as json_mod
from typing import Optional

import typer
from tabulate import tabulate

from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cms import policies as cms_policies

policies_app = typer.Typer(help="Juniper policy statement, prefix list, community, and AS path management.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STATEMENT_COLUMNS = ["name", "description", "term_count"]
PREFIX_LIST_COLUMNS = ["name", "description", "prefix_count"]
COMMUNITY_COLUMNS = ["name", "members", "description"]
AS_PATH_COLUMNS = ["name", "regex", "description"]
PREFIX_COLUMNS = ["prefix", "prefix_list_name"]
TERM_COLUMNS = ["name", "order", "action", "match_count", "action_count", "statement_name"]
MC_COLUMNS = ["id", "match_type", "prefix_name", "community_name", "as_path_name"]
ACTION_COLUMNS = ["id", "action_type", "local_preference", "metric", "term_name"]


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
# POLICY STATEMENTS
# ===========================================================================


@policies_app.command("list-statements")
def list_statements(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List policy statements for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_policies.list_policy_statements(client, device=device, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), STATEMENT_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("get-statement")
def get_statement(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Statement UUID"),
) -> None:
    """Get a policy statement with inlined term summaries."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_policies.get_policy_statement(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False))
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("create-statement")
def create_statement(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    name: str = typer.Option(..., help="Statement name"),
    description: Optional[str] = typer.Option(None, help="Statement description"),
) -> None:
    """Create a Juniper policy statement."""
    try:
        client = get_client_from_ctx(ctx)
        kwargs = {}
        if description:
            kwargs["description"] = description
        result = cms_policies.create_policy_statement(client, device=device, name=name, **kwargs)
        typer.echo(f"Created policy statement: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("update-statement")
def update_statement(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Statement UUID"),
    name: Optional[str] = typer.Option(None, help="New name"),
    description: Optional[str] = typer.Option(None, help="New description"),
) -> None:
    """Update a Juniper policy statement."""
    try:
        client = get_client_from_ctx(ctx)
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        result = cms_policies.update_policy_statement(client, id=id, **updates)
        typer.echo(f"Updated policy statement: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("delete-statement")
def delete_statement(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Statement UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a Juniper policy statement."""
    try:
        if not yes:
            typer.confirm(f"Delete policy statement {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_policies.delete_policy_statement(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# POLICY PREFIX LISTS
# ===========================================================================


@policies_app.command("list-prefix-lists")
def list_prefix_lists(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List policy prefix lists for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_policies.list_policy_prefix_lists(client, device=device, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), PREFIX_LIST_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("get-prefix-list")
def get_prefix_list(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Prefix list UUID"),
) -> None:
    """Get a policy prefix list with inlined prefixes."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_policies.get_policy_prefix_list(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False))
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("create-prefix-list")
def create_prefix_list(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    name: str = typer.Option(..., help="Prefix list name"),
    description: Optional[str] = typer.Option(None, help="Prefix list description"),
) -> None:
    """Create a Juniper policy prefix list."""
    try:
        client = get_client_from_ctx(ctx)
        kwargs = {}
        if description:
            kwargs["description"] = description
        result = cms_policies.create_policy_prefix_list(client, device=device, name=name, **kwargs)
        typer.echo(f"Created policy prefix list: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("update-prefix-list")
def update_prefix_list(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Prefix list UUID"),
    name: Optional[str] = typer.Option(None, help="New name"),
    description: Optional[str] = typer.Option(None, help="New description"),
) -> None:
    """Update a Juniper policy prefix list."""
    try:
        client = get_client_from_ctx(ctx)
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        result = cms_policies.update_policy_prefix_list(client, id=id, **updates)
        typer.echo(f"Updated policy prefix list: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("delete-prefix-list")
def delete_prefix_list(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Prefix list UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a Juniper policy prefix list."""
    try:
        if not yes:
            typer.confirm(f"Delete policy prefix list {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_policies.delete_policy_prefix_list(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# POLICY COMMUNITIES
# ===========================================================================


@policies_app.command("list-communities")
def list_communities(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List policy communities for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_policies.list_policy_communities(client, device=device, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), COMMUNITY_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("get-community")
def get_community(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Community UUID"),
) -> None:
    """Get a single policy community by UUID."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_policies.get_policy_community(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False))
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("create-community")
def create_community(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    name: str = typer.Option(..., help="Community name"),
    members: str = typer.Option(..., help="Community value (e.g. '65000:100')"),
    description: Optional[str] = typer.Option(None, help="Community description"),
) -> None:
    """Create a Juniper policy community."""
    try:
        client = get_client_from_ctx(ctx)
        kwargs = {}
        if description:
            kwargs["description"] = description
        result = cms_policies.create_policy_community(client, device=device, name=name, members=members, **kwargs)
        typer.echo(f"Created policy community: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("update-community")
def update_community(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Community UUID"),
    name: Optional[str] = typer.Option(None, help="New name"),
    members: Optional[str] = typer.Option(None, help="New community value"),
    description: Optional[str] = typer.Option(None, help="New description"),
) -> None:
    """Update a Juniper policy community."""
    try:
        client = get_client_from_ctx(ctx)
        updates = {}
        if name is not None:
            updates["name"] = name
        if members is not None:
            updates["members"] = members
        if description is not None:
            updates["description"] = description
        result = cms_policies.update_policy_community(client, id=id, **updates)
        typer.echo(f"Updated policy community: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("delete-community")
def delete_community(
    ctx: typer.Context,
    id: str = typer.Option(..., help="Community UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a Juniper policy community."""
    try:
        if not yes:
            typer.confirm(f"Delete policy community {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_policies.delete_policy_community(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# POLICY AS PATHS
# ===========================================================================


@policies_app.command("list-as-paths")
def list_as_paths(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List policy AS paths for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_policies.list_policy_as_paths(client, device=device, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), AS_PATH_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("get-as-path")
def get_as_path(
    ctx: typer.Context,
    id: str = typer.Option(..., help="AS path UUID"),
) -> None:
    """Get a single policy AS path by UUID."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_policies.get_policy_as_path(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False))
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("create-as-path")
def create_as_path(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device name or UUID"),
    name: str = typer.Option(..., help="AS-path name"),
    regex: str = typer.Option(..., help="AS-path regular expression"),
    description: Optional[str] = typer.Option(None, help="AS-path description"),
) -> None:
    """Create a Juniper policy AS path."""
    try:
        client = get_client_from_ctx(ctx)
        kwargs = {}
        if description:
            kwargs["description"] = description
        result = cms_policies.create_policy_as_path(client, device=device, name=name, regex=regex, **kwargs)
        typer.echo(f"Created policy AS path: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("update-as-path")
def update_as_path(
    ctx: typer.Context,
    id: str = typer.Option(..., help="AS path UUID"),
    name: Optional[str] = typer.Option(None, help="New name"),
    regex: Optional[str] = typer.Option(None, help="New AS-path regex"),
    description: Optional[str] = typer.Option(None, help="New description"),
) -> None:
    """Update a Juniper policy AS path."""
    try:
        client = get_client_from_ctx(ctx)
        updates = {}
        if name is not None:
            updates["name"] = name
        if regex is not None:
            updates["regex"] = regex
        if description is not None:
            updates["description"] = description
        result = cms_policies.update_policy_as_path(client, id=id, **updates)
        typer.echo(f"Updated policy AS path: {result.name} (id: {result.id})")
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("delete-as-path")
def delete_as_path(
    ctx: typer.Context,
    id: str = typer.Option(..., help="AS path UUID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a Juniper policy AS path."""
    try:
        if not yes:
            typer.confirm(f"Delete policy AS path {id}?", abort=True)
        client = get_client_from_ctx(ctx)
        result = cms_policies.delete_policy_as_path(client, id=id)
        typer.echo(result.get("message", "Deleted."))
    except Exception as e:
        handle_cli_error(e)


# ===========================================================================
# READ-ONLY SUB-MODELS
# ===========================================================================


@policies_app.command("list-prefixes")
def list_prefixes(
    ctx: typer.Context,
    prefix_list_id: Optional[str] = typer.Option(None, "--prefix-list-id", help="Filter by parent prefix list UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List policy prefixes (read-only), optionally by parent prefix list."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_policies.list_policy_prefixes(client, prefix_list_id=prefix_list_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), PREFIX_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("list-terms")
def list_terms(
    ctx: typer.Context,
    statement_id: Optional[str] = typer.Option(None, "--statement-id", help="Filter by parent policy statement UUID"),
    limit: int = typer.Option(50, help="Max results (0=all)"),
) -> None:
    """List JPS terms (read-only), optionally by parent policy statement."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_policies.list_jps_terms(client, statement_id=statement_id, limit=limit)
        _output(result.model_dump(), ctx.obj.get("json", False), TERM_COLUMNS)
    except Exception as e:
        handle_cli_error(e)


@policies_app.command("get-term")
def get_term(
    ctx: typer.Context,
    id: str = typer.Option(..., help="JPS term UUID"),
) -> None:
    """Get a JPS term with inlined match conditions and actions."""
    try:
        client = get_client_from_ctx(ctx)
        result = cms_policies.get_jps_term(client, id=id)
        _output_single(result.model_dump(), ctx.obj.get("json", False))
    except Exception as e:
        handle_cli_error(e)
