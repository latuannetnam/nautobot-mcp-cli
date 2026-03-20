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


@verify_app.command("quick-drift")
def verify_quick_drift_cmd(
    ctx: typer.Context,
    device: str = typer.Argument(..., help="Device name in Nautobot"),
    interface: Optional[list[str]] = typer.Option(None, "--interface", "-i", help="Interface name(s)"),
    ip: Optional[list[str]] = typer.Option(None, "--ip", help="IP address(es) for the last --interface"),
    vlan: Optional[list[int]] = typer.Option(None, "--vlan", help="VLAN ID(s) for the last --interface"),
    data: Optional[str] = typer.Option(None, "--data", "-d", help="JSON string of interfaces_data"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to JSON file with interfaces_data"),
) -> None:
    """Compare interface data against Nautobot — no config file needed.

    Quick check (flags):
      nautobot-mcp verify quick-drift DEVICE -i ae0.0 --ip 10.1.1.1/30

    Bulk check (JSON):
      nautobot-mcp verify quick-drift DEVICE -d '{"ae0.0": {"ips": ["10.1.1.1/30"]}}'

    File input:
      nautobot-mcp verify quick-drift DEVICE -f drift-input.json
    """
    try:
        import json

        from nautobot_mcp.drift import compare_device

        # Build interfaces_data from flags or --data or --file
        if data:
            interfaces_data = json.loads(data)
        elif file:
            interfaces_data = json.loads(file.read_text())
        elif interface:
            # Build from --interface/--ip/--vlan flags
            interfaces_data = {}
            current_iface = None
            for iface_name in interface:
                if iface_name not in interfaces_data:
                    interfaces_data[iface_name] = {"ips": [], "vlans": []}
                current_iface = iface_name
            if current_iface and ip:
                interfaces_data[current_iface]["ips"] = list(ip)
            if current_iface and vlan:
                interfaces_data[current_iface]["vlans"] = list(vlan)
        else:
            # Try reading from stdin
            import sys
            if not sys.stdin.isatty():
                stdin_data = sys.stdin.read().strip()
                if stdin_data:
                    interfaces_data = json.loads(stdin_data)
                else:
                    typer.echo("Error: No input provided. Use --interface/--ip, --data, --file, or pipe JSON.", err=True)
                    raise typer.Exit(1)
            else:
                typer.echo("Error: No input provided. Use --interface/--ip, --data, --file, or pipe JSON.", err=True)
                raise typer.Exit(1)

        client = get_client_from_ctx(ctx)
        result = compare_device(client, device, interfaces_data)

        if ctx.obj.get("json", False):
            print(format_json(result.model_dump()))
        else:
            # Colored table output
            typer.echo(f"Device: {result.device}")
            typer.echo(f"Timestamp: {result.timestamp}")

            if result.warnings:
                for w in result.warnings:
                    typer.echo(typer.style(f"  ⚠ {w}", fg=typer.colors.YELLOW))

            if result.summary.missing_interfaces:
                typer.echo(typer.style(
                    f"\n  Missing interfaces (not in Nautobot): {', '.join(result.summary.missing_interfaces)}",
                    fg=typer.colors.RED,
                ))

            typer.echo(f"\n{'Interface':<25} {'IPs':>8} {'VLANs':>8} {'Status':>8}")
            typer.echo("-" * 55)
            for d in result.interface_drifts:
                ip_drift = len(d.missing_ips) + len(d.extra_ips)
                vlan_drift = len(d.missing_vlans) + len(d.extra_vlans)
                if d.has_drift:
                    status = typer.style("❌ DRIFT", fg=typer.colors.RED)
                else:
                    status = typer.style("✅ OK", fg=typer.colors.GREEN)
                typer.echo(f"  {d.interface:<23} {ip_drift:>8} {vlan_drift:>8}   {status}")

                # Show details for drifted interfaces
                if d.missing_ips:
                    for mip in d.missing_ips:
                        typer.echo(typer.style(f"    + {mip} (not in Nautobot)", fg=typer.colors.RED))
                if d.extra_ips:
                    for eip in d.extra_ips:
                        typer.echo(typer.style(f"    - {eip} (extra in Nautobot)", fg=typer.colors.YELLOW))
                if d.missing_vlans:
                    for mv in d.missing_vlans:
                        typer.echo(typer.style(f"    + VLAN {mv} (not in Nautobot)", fg=typer.colors.RED))
                if d.extra_vlans:
                    for ev in d.extra_vlans:
                        typer.echo(typer.style(f"    - VLAN {ev} (extra in Nautobot)", fg=typer.colors.YELLOW))

            typer.echo(f"\nTotal drifts: {result.summary.total_drifts}")
            typer.echo(f"Interfaces checked: {result.summary.interfaces_checked}, "
                       f"with drift: {result.summary.interfaces_with_drift}")

    except json.JSONDecodeError as e:
        typer.echo(f"Error: Invalid JSON input: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        handle_cli_error(e)
