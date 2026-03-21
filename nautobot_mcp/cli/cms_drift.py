"""CLI commands for CMS drift verification.

Provides commands under: nautobot-mcp cms drift
"""

from __future__ import annotations

import json as json_mod
import pathlib
import sys
from typing import Optional

import typer

from nautobot_mcp.cli.app import get_client_from_ctx, handle_cli_error
from nautobot_mcp.cms.cms_drift import compare_bgp_neighbors, compare_static_routes

drift_app = typer.Typer(help="CMS drift verification commands")


@drift_app.command("bgp")
def drift_bgp(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device hostname in Nautobot"),
    from_file: Optional[str] = typer.Option(None, "--from-file", help="JSON file with live BGP data (list of neighbor dicts)"),
) -> None:
    """Compare live BGP neighbors against Nautobot CMS records.

    Provide live BGP data via --from-file (JSON array of neighbor dicts)
    or pipe JSON to stdin.

    Each dict should have: peer_ip, peer_as, local_address, group_name.
    """
    try:
        if from_file:
            raw = pathlib.Path(from_file).read_text()
        else:
            raw = sys.stdin.read()
        live_data = json_mod.loads(raw)
        client = get_client_from_ctx(ctx)
        result = compare_bgp_neighbors(client, device_name=device, live_neighbors=live_data)
        if ctx.obj.get("json", False):
            typer.echo(json_mod.dumps(result.model_dump(), indent=2, default=str))
            return
        summary = result.summary
        total = summary.get("total_drifts", 0)
        by_type = summary.get("by_type", {})
        bgp_info = by_type.get("bgp_neighbors", {})
        typer.echo(f"Device: {device} | BGP Drift: {total} total")
        typer.echo(f"  Missing in Nautobot: {bgp_info.get('missing', 0)}")
        typer.echo(f"  Extra in Nautobot:   {bgp_info.get('extra', 0)}")
        typer.echo(f"  Changed:             {bgp_info.get('changed', 0)}")
        if result.bgp_neighbors.missing:
            typer.echo("\nMissing in Nautobot (on device, not in CMS):")
            for item in result.bgp_neighbors.missing:
                typer.echo(f"  - {item.name}")
        if result.bgp_neighbors.extra:
            typer.echo("\nExtra in Nautobot (in CMS, not on device):")
            for item in result.bgp_neighbors.extra:
                typer.echo(f"  - {item.name}")
        if result.bgp_neighbors.changed:
            typer.echo("\nChanged (exists in both, fields differ):")
            for item in result.bgp_neighbors.changed:
                typer.echo(f"  - {item.name}: {list(item.changed_fields.keys())}")
    except Exception as e:
        handle_cli_error(e)


@drift_app.command("routes")
def drift_routes(
    ctx: typer.Context,
    device: str = typer.Option(..., help="Device hostname in Nautobot"),
    from_file: Optional[str] = typer.Option(None, "--from-file", help="JSON file with live static route data (list of route dicts)"),
) -> None:
    """Compare live static routes against Nautobot CMS records.

    Provide live route data via --from-file (JSON array of route dicts)
    or pipe JSON to stdin.

    Each dict should have: destination, nexthops (list[str]), preference,
    metric, routing_instance.
    """
    try:
        if from_file:
            raw = pathlib.Path(from_file).read_text()
        else:
            raw = sys.stdin.read()
        live_data = json_mod.loads(raw)
        client = get_client_from_ctx(ctx)
        result = compare_static_routes(client, device_name=device, live_routes=live_data)
        if ctx.obj.get("json", False):
            typer.echo(json_mod.dumps(result.model_dump(), indent=2, default=str))
            return
        summary = result.summary
        total = summary.get("total_drifts", 0)
        by_type = summary.get("by_type", {})
        route_info = by_type.get("static_routes", {})
        typer.echo(f"Device: {device} | Static Route Drift: {total} total")
        typer.echo(f"  Missing in Nautobot: {route_info.get('missing', 0)}")
        typer.echo(f"  Extra in Nautobot:   {route_info.get('extra', 0)}")
        typer.echo(f"  Changed:             {route_info.get('changed', 0)}")
        if result.static_routes.missing:
            typer.echo("\nMissing in Nautobot (on device, not in CMS):")
            for item in result.static_routes.missing:
                typer.echo(f"  - {item.name}")
        if result.static_routes.extra:
            typer.echo("\nExtra in Nautobot (in CMS, not on device):")
            for item in result.static_routes.extra:
                typer.echo(f"  - {item.name}")
        if result.static_routes.changed:
            typer.echo("\nChanged (exists in both, fields differ):")
            for item in result.static_routes.changed:
                typer.echo(f"  - {item.name}: {list(item.changed_fields.keys())}")
    except Exception as e:
        handle_cli_error(e)
