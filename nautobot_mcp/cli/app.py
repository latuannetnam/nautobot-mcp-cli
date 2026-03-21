"""Typer CLI application root with global options and error handling.

Entry point: nautobot-mcp (registered in pyproject.toml)
"""

from __future__ import annotations

from typing import Optional

import typer

from nautobot_mcp.client import NautobotClient
from nautobot_mcp.config import NautobotProfile, NautobotSettings
from nautobot_mcp.exceptions import (
    NautobotConnectionError,
    NautobotMCPError,
    NautobotNotFoundError,
    NautobotValidationError,
)

app = typer.Typer(
    name="nautobot-mcp",
    help="Nautobot MCP CLI - Network automation via Nautobot API",
)


# ---------------------------------------------------------------------------
# Global callback with shared options
# ---------------------------------------------------------------------------


@app.callback()
def main(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", help="Config profile name"),
    url: Optional[str] = typer.Option(None, "--url", help="Nautobot URL override"),
    token: Optional[str] = typer.Option(None, "--token", help="API token override"),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip SSL verification"),
) -> None:
    """Global options applied to all commands."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    ctx.obj["profile"] = profile
    ctx.obj["url"] = url
    ctx.obj["token"] = token
    ctx.obj["no_verify"] = no_verify


# ---------------------------------------------------------------------------
# Client factory from CLI context
# ---------------------------------------------------------------------------


def get_client_from_ctx(ctx: typer.Context) -> NautobotClient:
    """Create a NautobotClient from global CLI options.

    Applies --url, --token, --profile, --no-verify overrides.
    """
    obj = ctx.obj or {}
    url = obj.get("url")
    token = obj.get("token")
    profile_name = obj.get("profile")
    no_verify = obj.get("no_verify", False)

    if url and token:
        # Direct override — create profile from CLI flags
        profile = NautobotProfile(url=url, token=token, verify_ssl=not no_verify)
        return NautobotClient(profile=profile)

    # Load from settings, optionally switching profile
    settings = NautobotSettings.discover()
    if profile_name:
        settings.active_profile = profile_name
    client = NautobotClient(settings=settings)

    # Apply verify override if specified
    if no_verify and client._profile:
        client._profile.verify_ssl = False

    return client


# ---------------------------------------------------------------------------
# Error handler — maps exceptions to exit codes
# ---------------------------------------------------------------------------


def handle_cli_error(e: Exception) -> None:
    """Map NautobotMCPError hierarchy to CLI exit codes.

    Exit codes:
        0 — success
        1 — general error
        2 — connection error
        3 — not found
        4 — validation error
    """
    if isinstance(e, NautobotConnectionError):
        typer.echo(f"Connection error: {e.message}", err=True)
        raise typer.Exit(code=2)
    elif isinstance(e, NautobotNotFoundError):
        typer.echo(f"Not found: {e.message}", err=True)
        raise typer.Exit(code=3)
    elif isinstance(e, NautobotValidationError):
        typer.echo(f"Validation error: {e.message}", err=True)
        raise typer.Exit(code=4)
    elif isinstance(e, NautobotMCPError):
        typer.echo(f"Error: {e.message}", err=True)
        raise typer.Exit(code=1)
    else:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Register sub-apps (lazy imports at module level)
# ---------------------------------------------------------------------------

from nautobot_mcp.cli.devices import devices_app  # noqa: E402
from nautobot_mcp.cli.interfaces import interfaces_app  # noqa: E402
from nautobot_mcp.cli.ipam import ipam_app  # noqa: E402
from nautobot_mcp.cli.organization import org_app  # noqa: E402
from nautobot_mcp.cli.circuits import circuits_app  # noqa: E402
from nautobot_mcp.cli.golden_config import golden_config_app  # noqa: E402
from nautobot_mcp.cli.parse import parse_app  # noqa: E402
from nautobot_mcp.cli.onboard import onboard_app  # noqa: E402
from nautobot_mcp.cli.verify import verify_app  # noqa: E402
from nautobot_mcp.cli.cms_routing import routing_app  # noqa: E402
from nautobot_mcp.cli.cms_interfaces import interfaces_cli_app  # noqa: E402
from nautobot_mcp.cli.cms_firewalls import firewalls_app  # noqa: E402
from nautobot_mcp.cli.cms_policies import policies_app  # noqa: E402
from nautobot_mcp.cli.cms_drift import drift_app  # noqa: E402

app.add_typer(devices_app, name="devices")
app.add_typer(interfaces_app, name="interfaces")
app.add_typer(ipam_app, name="ipam")
app.add_typer(org_app, name="org")
app.add_typer(circuits_app, name="circuits")
app.add_typer(golden_config_app, name="golden-config")
app.add_typer(parse_app, name="parse")
app.add_typer(onboard_app, name="onboard")
app.add_typer(verify_app, name="verify")

# CMS plugin sub-group
cms_app = typer.Typer(name="cms", help="CMS plugin operations (Juniper models)")
cms_app.add_typer(routing_app, name="routing")
cms_app.add_typer(interfaces_cli_app, name="interfaces")
cms_app.add_typer(firewalls_app, name="firewalls")
cms_app.add_typer(policies_app, name="policies")
cms_app.add_typer(drift_app, name="drift")
app.add_typer(cms_app, name="cms")


if __name__ == "__main__":
    app()
