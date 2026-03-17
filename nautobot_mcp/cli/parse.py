"""CLI commands for config parsing operations."""

from __future__ import annotations

import json
import sys

import typer

from nautobot_mcp.parsers import ParserRegistry

parse_app = typer.Typer(help="Parse device configurations into structured data.")


@parse_app.command("junos")
def junos(
    config_file: str = typer.Argument(None, help="Path to JunOS JSON config file. Use '-' for stdin."),
    network_os: str = typer.Option("juniper_junos", help="Parser network_os identifier"),
    json_output: bool = typer.Option(False, "--json", help="Output full JSON"),
) -> None:
    """Parse a JunOS configuration (JSON format) into structured data."""
    try:
        if config_file == "-" or config_file is None:
            config_text = sys.stdin.read()
        else:
            with open(config_file) as f:
                config_text = f.read()

        config_data = json.loads(config_text)
        parser = ParserRegistry.get(network_os)
        result = parser.parse(config_data)

        if json_output:
            print(result.model_dump_json(indent=2))
        else:
            typer.echo(f"Hostname: {result.hostname}")
            typer.echo(f"Platform: {result.platform} ({result.network_os})")
            typer.echo(f"Interfaces: {len(result.interfaces)}")
            typer.echo(f"IP Addresses: {len(result.ip_addresses)}")
            typer.echo(f"VLANs: {len(result.vlans)}")
            typer.echo(f"Routing Instances: {len(result.routing_instances)}")
            typer.echo(f"Protocols: {len(result.protocols)}")
            typer.echo(f"Firewall Filters: {len(result.firewall_filters)}")
            if result.warnings:
                typer.echo(f"Warnings: {len(result.warnings)}")
                for w in result.warnings:
                    typer.echo(f"  ⚠ {w}")
    except json.JSONDecodeError as e:
        typer.echo(f"Invalid JSON: {e}", err=True)
        raise typer.Exit(code=1)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except FileNotFoundError:
        typer.echo(f"File not found: {config_file}", err=True)
        raise typer.Exit(code=1)


@parse_app.command("list-parsers")
def list_parsers() -> None:
    """List available configuration parsers."""
    parsers = ParserRegistry.list_parsers()
    if parsers:
        for p in parsers:
            typer.echo(f"  - {p}")
    else:
        typer.echo("No parsers registered.")
