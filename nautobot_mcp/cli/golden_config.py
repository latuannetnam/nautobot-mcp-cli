"""CLI commands for Golden Config operations."""

from __future__ import annotations

from typing import Optional

import typer

from nautobot_mcp import golden_config as gc
from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cli.formatters import format_json, format_table

golden_config_app = typer.Typer(help="Golden Config plugin operations — configs, compliance, features, rules")

# Column definitions for table output
FEATURE_COLUMNS = ["name", "slug", "description"]
RULE_COLUMNS = ["feature", "platform", "config_ordered", "match_config"]
COMPLIANCE_COLUMNS = ["feature", "status", "ordered"]


@golden_config_app.command("intended-config")
def intended_config(
    ctx: typer.Context,
    device: str = typer.Argument(..., help="Device name or ID"),
) -> None:
    """Get the intended (golden) configuration for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = gc.get_intended_config(client, device)
        if ctx.obj.get("json", False):
            print(format_json(result.model_dump()))
        else:
            typer.echo(f"Device: {result.device}")
            typer.echo(f"Config length: {len(result.intended_config)} chars")
            typer.echo("---")
            typer.echo(result.intended_config[:2000] if result.intended_config else "(empty)")
            if len(result.intended_config) > 2000:
                typer.echo(f"\n... ({len(result.intended_config) - 2000} more chars, use --json for full)")
    except Exception as e:
        handle_cli_error(e)


@golden_config_app.command("backup-config")
def backup_config(
    ctx: typer.Context,
    device: str = typer.Argument(..., help="Device name or ID"),
) -> None:
    """Get the backup (actual) configuration for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = gc.get_backup_config(client, device)
        if ctx.obj.get("json", False):
            print(format_json(result.model_dump()))
        else:
            typer.echo(f"Device: {result.device}")
            typer.echo(f"Config length: {len(result.backup_config)} chars")
            typer.echo("---")
            typer.echo(result.backup_config[:2000] if result.backup_config else "(empty)")
            if len(result.backup_config) > 2000:
                typer.echo(f"\n... ({len(result.backup_config) - 2000} more chars, use --json for full)")
    except Exception as e:
        handle_cli_error(e)


@golden_config_app.command("list-features")
def list_features(ctx: typer.Context) -> None:
    """List compliance features."""
    try:
        client = get_client_from_ctx(ctx)
        result = gc.list_compliance_features(client)
        data = result.model_dump()
        if ctx.obj.get("json", False):
            print(format_json(data))
        else:
            results = data.get("results", [])
            if results:
                print(format_table(results, FEATURE_COLUMNS))
            else:
                typer.echo("No compliance features found.")
    except Exception as e:
        handle_cli_error(e)


@golden_config_app.command("create-feature")
def create_feature(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Feature name"),
    slug: str = typer.Argument(..., help="Feature slug"),
    description: str = typer.Option("", help="Feature description"),
) -> None:
    """Create a new compliance feature."""
    try:
        client = get_client_from_ctx(ctx)
        result = gc.create_compliance_feature(client, name=name, slug=slug, description=description)
        if ctx.obj.get("json", False):
            print(format_json(result.model_dump()))
        else:
            print(format_table([result.model_dump()], FEATURE_COLUMNS))
    except Exception as e:
        handle_cli_error(e)


@golden_config_app.command("delete-feature")
def delete_feature(
    ctx: typer.Context,
    feature_id: str = typer.Argument(..., help="Feature UUID"),
) -> None:
    """Delete a compliance feature."""
    try:
        client = get_client_from_ctx(ctx)
        result = gc.delete_compliance_feature(client, feature_id)
        if ctx.obj.get("json", False):
            print(format_json(result))
        else:
            typer.echo(result.get("message", "Deleted"))
    except Exception as e:
        handle_cli_error(e)


@golden_config_app.command("list-rules")
def list_rules(
    ctx: typer.Context,
    feature: Optional[str] = typer.Option(None, help="Filter by feature name"),
    platform: Optional[str] = typer.Option(None, help="Filter by platform slug"),
) -> None:
    """List compliance rules."""
    try:
        client = get_client_from_ctx(ctx)
        result = gc.list_compliance_rules(client, feature=feature, platform=platform)
        data = result.model_dump()
        if ctx.obj.get("json", False):
            print(format_json(data))
        else:
            results = data.get("results", [])
            if results:
                print(format_table(results, RULE_COLUMNS))
            else:
                typer.echo("No compliance rules found.")
    except Exception as e:
        handle_cli_error(e)


@golden_config_app.command("create-rule")
def create_rule(
    ctx: typer.Context,
    feature: str = typer.Argument(..., help="Feature name"),
    platform: str = typer.Argument(..., help="Platform slug"),
    config_ordered: bool = typer.Option(False, help="Whether config order matters"),
    match_config: str = typer.Option("", help="Match config pattern"),
    description: str = typer.Option("", help="Rule description"),
) -> None:
    """Create a new compliance rule."""
    try:
        client = get_client_from_ctx(ctx)
        result = gc.create_compliance_rule(
            client, feature=feature, platform=platform,
            config_ordered=config_ordered, match_config=match_config,
            description=description,
        )
        if ctx.obj.get("json", False):
            print(format_json(result.model_dump()))
        else:
            print(format_table([result.model_dump()], RULE_COLUMNS))
    except Exception as e:
        handle_cli_error(e)


@golden_config_app.command("update-rule")
def update_rule(
    ctx: typer.Context,
    rule_id: str = typer.Argument(..., help="Rule UUID"),
    config_ordered: Optional[bool] = typer.Option(None, help="Config ordering"),
    match_config: Optional[str] = typer.Option(None, help="Match config pattern"),
    description: Optional[str] = typer.Option(None, help="Description"),
) -> None:
    """Update a compliance rule."""
    try:
        client = get_client_from_ctx(ctx)
        updates = {}
        if config_ordered is not None:
            updates["config_ordered"] = config_ordered
        if match_config is not None:
            updates["match_config"] = match_config
        if description is not None:
            updates["description"] = description
        result = gc.update_compliance_rule(client, rule_id, **updates)
        if ctx.obj.get("json", False):
            print(format_json(result.model_dump()))
        else:
            print(format_table([result.model_dump()], RULE_COLUMNS))
    except Exception as e:
        handle_cli_error(e)


@golden_config_app.command("delete-rule")
def delete_rule(
    ctx: typer.Context,
    rule_id: str = typer.Argument(..., help="Rule UUID"),
) -> None:
    """Delete a compliance rule."""
    try:
        client = get_client_from_ctx(ctx)
        result = gc.delete_compliance_rule(client, rule_id)
        if ctx.obj.get("json", False):
            print(format_json(result))
        else:
            typer.echo(result.get("message", "Deleted"))
    except Exception as e:
        handle_cli_error(e)


@golden_config_app.command("compliance")
def compliance(
    ctx: typer.Context,
    device: str = typer.Argument(..., help="Device name or ID"),
) -> None:
    """Get compliance results for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = gc.get_compliance_results(client, device)
        data = result.model_dump()
        if ctx.obj.get("json", False):
            print(format_json(data))
        else:
            typer.echo(f"Device: {result.device}")
            typer.echo(f"Overall: {result.overall_status}")
            if result.features:
                features_data = [f.model_dump() for f in result.features]
                print(format_table(features_data, COMPLIANCE_COLUMNS))
            else:
                typer.echo("No feature results.")
    except Exception as e:
        handle_cli_error(e)


@golden_config_app.command("quick-diff")
def quick_diff(
    ctx: typer.Context,
    device: str = typer.Argument(..., help="Device name or ID"),
) -> None:
    """Quick diff intended vs backup config for a device."""
    try:
        client = get_client_from_ctx(ctx)
        result = gc.quick_diff_config(client, device)
        data = result.model_dump()
        if ctx.obj.get("json", False):
            print(format_json(data))
        else:
            typer.echo(f"Device: {result.device}")
            typer.echo(f"Overall: {result.overall_status} (source: {result.source})")
            if result.features:
                features_data = [f.model_dump() for f in result.features]
                print(format_table(features_data, COMPLIANCE_COLUMNS))
    except Exception as e:
        handle_cli_error(e)
