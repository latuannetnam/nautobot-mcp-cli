"""Nautobot API Bridge MCP Server — 3-tool interface.

Exposes three tools to AI agents:
  1. nautobot_api_catalog   — discover endpoints and workflows
  2. nautobot_call_nautobot — REST CRUD bridge for any Nautobot endpoint
  3. nautobot_run_workflow  — dispatch pre-built composite workflows
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from nautobot_mcp.bridge import call_nautobot
from nautobot_mcp.catalog.engine import get_catalog
from nautobot_mcp.client import NautobotClient
from nautobot_mcp.config import NautobotSettings
from nautobot_mcp.exceptions import NautobotMCPError
from nautobot_mcp.workflows import run_workflow

mcp = FastMCP("Nautobot API Bridge")


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

_client: NautobotClient | None = None


def get_client() -> NautobotClient:
    """Return a lazily-initialized NautobotClient singleton."""
    global _client
    if _client is None:
        settings = NautobotSettings.discover()
        _client = NautobotClient(settings=settings)
    return _client


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def handle_error(e: Exception) -> None:
    """Translate NautobotMCPError hierarchy to ToolError for MCP responses."""
    if isinstance(e, NautobotMCPError):
        msg = e.message
        if hasattr(e, "hint") and e.hint:
            msg += f". Hint: {e.hint}"
        raise ToolError(msg)
    raise ToolError(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Tool 1: nautobot_api_catalog
# ---------------------------------------------------------------------------


@mcp.tool(name="nautobot_api_catalog")
def nautobot_api_catalog(
    domain: str | None = None,
    include_workflows: bool = True,
    include_cms: bool = True,
) -> dict:
    """Discover available Nautobot API endpoints and composite workflows.

    Returns a structured catalog of all endpoints the agent can access,
    including core Nautobot REST endpoints, CMS plugin endpoints, and
    pre-built composite workflows. Use this first to understand what's
    available before calling nautobot_call_nautobot or nautobot_run_workflow.

    Args:
        domain: Filter by domain (e.g., 'dcim', 'ipam', 'circuits', 'cms',
            'workflows'). None returns the full catalog.
        include_workflows: Include composite workflow entries (default: True).
        include_cms: Include CMS plugin endpoints (default: True).

    Returns:
        Dict with 'endpoints' (list of {path, methods, description, domain}),
        'workflows' (dict mapping workflow IDs to param/description metadata),
        and 'summary' (counts by domain).
    """
    try:
        client = get_client()
        catalog = get_catalog(
            client,
            domain=domain,
            include_workflows=include_workflows,
            include_cms=include_cms,
        )
        return catalog.model_dump() if hasattr(catalog, "model_dump") else catalog
    except Exception as e:
        handle_error(e)


# ---------------------------------------------------------------------------
# Tool 2: nautobot_call_nautobot
# ---------------------------------------------------------------------------


@mcp.tool(name="nautobot_call_nautobot")
def nautobot_call_nautobot(
    method: str,
    endpoint: str,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict:
    """Execute a REST CRUD operation against any Nautobot API endpoint.

    Provides direct access to any Nautobot REST endpoint — core API and
    plugin endpoints (CMS, Golden Config, etc.). Supports full CRUD.
    Use nautobot_api_catalog first to discover endpoint paths.

    Args:
        method: HTTP method — GET, POST, PATCH, PUT, DELETE.
        endpoint: API path (e.g., '/api/dcim/devices/', '/api/plugins/cms/bgp-groups/').
            Can be partial path; bridge performs fuzzy matching if needed.
        params: Query parameters for filtering (GET requests). Optional.
            Example: {"device": "core-rtr-01", "limit": 50}
        body: Request body for write operations (POST, PATCH, PUT). Optional.
            Must match Nautobot's expected schema for the endpoint.

    Returns:
        Dict with 'status' (ok/error), 'method', 'endpoint', 'data' (response
        body or list for GET), 'count' (total results for paginated GET),
        and 'error' (message if status=error).
    """
    try:
        client = get_client()
        return call_nautobot(
            client,
            method=method,
            endpoint=endpoint,
            params=params,
            body=body,
        )
    except Exception as e:
        handle_error(e)


# ---------------------------------------------------------------------------
# Tool 3: nautobot_run_workflow
# ---------------------------------------------------------------------------


@mcp.tool(name="nautobot_run_workflow")
def nautobot_run_workflow(
    workflow_id: str,
    params: dict[str, Any],
) -> dict:
    """Execute a pre-built composite workflow aggregating multiple API calls.

    Composite workflows encapsulate multi-step operations that would otherwise
    require several sequential nautobot_call_nautobot calls. Use
    nautobot_api_catalog (include_workflows=True) to discover available
    workflows and their required parameters.

    Args:
        workflow_id: Workflow name (e.g., 'bgp_summary', 'firewall_summary',
            'compare_device', 'onboard_config'). See nautobot_api_catalog
            for the full list.
        params: Workflow-specific parameters. Required params vary by workflow.
            Example for bgp_summary: {"device": "core-rtr-01", "detail": false}
            Example for compare_device: {"device_name": "rtr-01", "live_data": {...}}

    Returns:
        Envelope dict with:
          - workflow: workflow_id echo
          - device: device identifier used
          - status: 'ok' or 'error'
          - data: workflow-specific output (serialized Pydantic model or dict)
          - error: error message if status=error, else null
          - timestamp: ISO 8601 UTC timestamp
    """
    try:
        client = get_client()
        return run_workflow(client, workflow_id=workflow_id, params=params)
    except Exception as e:
        handle_error(e)
