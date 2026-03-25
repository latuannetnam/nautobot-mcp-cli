"""API Catalog engine for Nautobot MCP Server.

Assembles endpoint metadata from static core definitions,
dynamic CMS plugin discovery, and workflow registry stubs.
"""

from nautobot_mcp.catalog.engine import get_catalog

__all__ = ["get_catalog"]
