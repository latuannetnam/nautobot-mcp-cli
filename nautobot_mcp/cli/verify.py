"""CLI commands for verification and drift reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cli.formatters import format_json, format_table

verify_app = typer.Typer(help="Verification & drift detection — compare device state vs Nautobot")

# Column definitions
DRIFT_COLUMNS = ["name", "status"]


@verify_app.command("compliance")
def verify_compliance_cmd(
    ctx: typer.Context,
    device: str = typer.Argument(..., help="Device name or UUID"),
) -> None:
    """Check config compliance via Golden Config quick diff.

    Compares intended vs backup config and returns compliance status.
    """
    try:
        from nautobot_mcp.verification import verify_config_compliance

        client = get_client_from_ctx(ctx)
        result = verify_config_compliance(client, device)

        if ctx.obj.get("json", False):
            print(format_json(result.model_dump()))
        else:
            typer.echo(f"Device: {result.device}")
            typer.echo(f"Source: {result.source}")
            if result.config_compliance:
                typer.echo(f"Overall: {result.config_compliance.get('overall_status', 'unknown')}")
            typer.echo(f"Timestamp: {result.timestamp}")

    except Exception as e:
        handle_cli_error(e)


@verify_app.command("data-model")
def verify_data_model_cmd(
    ctx: typer.Context,
    config_file: Path = typer.Argument(..., help="Path to JunOS JSON config file"),
    device_name: str = typer.Argument(..., help="Device name in Nautobot"),
    network_os: str = typer.Option("juniper_junos", help="Parser identifier"),
) -> None:
    """Compare parsed device config against Nautobot data model.

    Uses DiffSync for object-by-object comparison across interfaces,
    IP addresses, and VLANs. Shows missing, extra, and changed items.
    """
    try:
        import json

        from nautobot_mcp.parsers import ParserRegistry
        from nautobot_mcp.verification import verify_data_model

        config_data = json.loads(config_file.read_text())
        parser = ParserRegistry.get(network_os)
        parsed_config = parser.parse(config_data)

        client = get_client_from_ctx(ctx)
        result = verify_data_model(client, device_name, parsed_config)

        if ctx.obj.get("json", False):
            print(format_json(result.model_dump()))
        else:
            typer.echo(f"Device: {result.device}")
            typer.echo(f"Timestamp: {result.timestamp}")
            typer.echo(f"Total drifts: {result.summary.get('total_drifts', 0)}")
            typer.echo("---")

            # Show drifts by section
            for section_name, section in [
                ("Interfaces", result.interfaces),
                ("IP Addresses", result.ip_addresses),
                ("VLANs", result.vlans),
            ]:
                all_items = section.missing + section.extra + section.changed
                if all_items:
                    typer.echo(f"\n{section_name}:")
                    drift_data = [item.model_dump() for item in all_items]
                    print(format_table(drift_data, DRIFT_COLUMNS))

    except FileNotFoundError:
        typer.echo(f"Error: Config file not found: {config_file}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        handle_cli_error(e)
