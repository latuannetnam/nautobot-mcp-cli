"""CLI commands for config onboarding operations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cli.formatters import format_json, format_table

onboard_app = typer.Typer(help="Config onboarding — parse router config and push to Nautobot")

# Column definitions
ACTION_COLUMNS = ["action", "object_type", "name", "reason"]


@onboard_app.command("config")
def onboard_config_cmd(
    ctx: typer.Context,
    config_file: Path = typer.Argument(..., help="Path to JunOS JSON config file"),
    device_name: str = typer.Argument(..., help="Target device name in Nautobot"),
    network_os: str = typer.Option("juniper_junos", help="Parser identifier"),
    commit: bool = typer.Option(False, "--commit", help="Actually commit changes (default: dry-run)"),
    update: bool = typer.Option(False, "--update", help="Update existing objects"),
    location: Optional[str] = typer.Option(None, help="Device location name"),
    device_type: Optional[str] = typer.Option(None, help="Device type name"),
    role: str = typer.Option("Router", help="Device role"),
    namespace: str = typer.Option("Global", help="IPAM namespace"),
) -> None:
    """Onboard a device config file into Nautobot.

    Parses the config and creates/updates device, interfaces, IPs, VLANs.
    Default is dry-run mode (shows planned changes).
    """
    try:
        import json

        from nautobot_mcp.onboarding import onboard_config
        from nautobot_mcp.parsers import ParserRegistry

        # Read and parse config file
        config_data = json.loads(config_file.read_text())
        parser = ParserRegistry.get(network_os)
        parsed_config = parser.parse(config_data)

        client = get_client_from_ctx(ctx)
        result = onboard_config(
            client, parsed_config, device_name,
            dry_run=not commit, update_existing=update,
            location=location, device_type=device_type,
            role=role, namespace=namespace,
        )

        if ctx.obj.get("json", False):
            print(format_json(result.model_dump()))
        else:
            mode = "COMMIT" if commit else "DRY-RUN"
            typer.echo(f"Device: {result.device} [{mode}]")
            typer.echo(f"Summary: {result.summary.total} total — "
                      f"{result.summary.created} create, "
                      f"{result.summary.updated} update, "
                      f"{result.summary.skipped} skip, "
                      f"{result.summary.failed} failed")
            typer.echo("---")

            actions_data = [a.model_dump() for a in result.actions]
            if actions_data:
                print(format_table(actions_data, ACTION_COLUMNS))

            if result.warnings:
                typer.echo("\nWarnings:")
                for w in result.warnings:
                    typer.echo(f"  ⚠ {w}")

    except FileNotFoundError:
        typer.echo(f"Error: Config file not found: {config_file}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        handle_cli_error(e)
