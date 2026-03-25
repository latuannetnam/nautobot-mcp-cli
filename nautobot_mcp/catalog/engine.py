"""Catalog engine — assembles and serves endpoint/workflow metadata.

Combines static core endpoints, dynamic CMS discovery, and workflow stubs
into a unified catalog with optional domain filtering.
"""

from __future__ import annotations

from typing import Optional

from nautobot_mcp.catalog.core_endpoints import CORE_ENDPOINTS
from nautobot_mcp.catalog.cms_discovery import discover_cms_endpoints
from nautobot_mcp.catalog.workflow_stubs import WORKFLOW_STUBS


# Cache CMS discovery result (computed once at import time)
_cms_cache: dict | None = None


def _get_cms_catalog() -> dict:
    """Get cached CMS catalog (lazy singleton)."""
    global _cms_cache
    if _cms_cache is None:
        _cms_cache = discover_cms_endpoints()
    return _cms_cache


def get_catalog(
    client=None,
    domain: Optional[str] = None,
    include_workflows: bool = True,
    include_cms: bool = True,
) -> dict:
    """Assemble the full API catalog or filter by domain.

    Args:
        client: NautobotClient instance (reserved for future dynamic discovery).
        domain: Optional domain filter. Valid values:
            "dcim", "ipam", "circuits", "tenancy" — core endpoints
            "cms" — CMS plugin endpoints (all sub-domains)
            "workflows" — available server-side workflows
            None — returns all domains
        include_workflows: Include composite workflow entries (default: True).
        include_cms: Include CMS plugin endpoints (default: True).

    Returns:
        Dict of catalog entries grouped by domain.

    Raises:
        ValueError: If domain is not a valid catalog domain.
    """
    cms_catalog = _get_cms_catalog()

    valid_domains = set(CORE_ENDPOINTS.keys()) | {"cms", "workflows"}

    if domain is not None:
        domain = domain.lower().strip()
        if domain not in valid_domains:
            available = ", ".join(sorted(valid_domains))
            raise ValueError(
                f"Unknown catalog domain: '{domain}'. "
                f"Available domains: {available}"
            )

        if domain == "cms":
            return {"cms": cms_catalog} if include_cms else {}
        elif domain == "workflows":
            return {"workflows": WORKFLOW_STUBS} if include_workflows else {}
        else:
            return {domain: CORE_ENDPOINTS[domain]}

    # Full catalog — include all domains
    catalog: dict = {}

    # Core endpoints
    for dom, entries in CORE_ENDPOINTS.items():
        catalog[dom] = entries

    # CMS endpoints (full listing)
    if include_cms:
        catalog["cms"] = cms_catalog

    # Workflows
    if include_workflows:
        catalog["workflows"] = WORKFLOW_STUBS

    return catalog
