"""Dynamic CMS endpoint discovery from CMS_ENDPOINTS registry.

Reads nautobot_mcp.cms.client.CMS_ENDPOINTS at import time and transforms
entries into catalog format with friendly display names and domain grouping.
"""

from nautobot_mcp.cms.client import CMS_ENDPOINTS

# Map endpoint name prefixes to CMS sub-domains and friendly names
CMS_DOMAIN_MAP = {
    "juniper_static_route": ("routing", "Static Routes"),
    "juniper_bgp": ("routing", "BGP"),
    "juniper_interface": ("interfaces", "Interfaces"),
    "juniper_firewall": ("firewalls", "Firewalls"),
    "juniper_policy": ("policies", "Policies"),
    "jps_": ("policies", "Policy Statements"),
    "vrrp_": ("interfaces", "VRRP"),
    "juniper_arp": ("arp", "ARP"),
}

# Common filters by CMS domain
CMS_DOMAIN_FILTERS = {
    "routing": ["device"],
    "interfaces": ["device"],
    "firewalls": ["device"],
    "policies": ["device"],
    "arp": ["device"],
}


def _get_friendly_name(endpoint_name: str) -> str:
    """Convert underscore endpoint name to friendly display name."""
    # Use model name from CMS_ENDPOINTS, clean up 'Juniper' prefix
    model_name = CMS_ENDPOINTS.get(endpoint_name, endpoint_name)
    return (
        model_name.replace("Juniper", "")
        .replace("JPS", "Policy Statement")
        .replace("VRRP", "VRRP")
        .strip()
    )


def _get_cms_domain(endpoint_name: str) -> str:
    """Determine CMS sub-domain from endpoint name."""
    for prefix, (domain, _) in CMS_DOMAIN_MAP.items():
        if endpoint_name.startswith(prefix):
            return domain
    return "other"


def discover_cms_endpoints() -> dict:
    """Build CMS catalog entries from CMS_ENDPOINTS registry.

    Returns:
        Dict of CMS endpoint entries grouped by sub-domain, with format:
        {
            "routing": {
                "static_routes": {
                    "endpoint": "cms:juniper_static_routes",
                    "display_name": "Static Route",
                    "methods": ["GET", "POST", "PATCH", "DELETE"],
                    "filters": ["device"],
                    "description": "Juniper static routes"
                },
                ...
            }
        }
    """
    cms_catalog: dict = {}

    for endpoint_name, model_name in CMS_ENDPOINTS.items():
        domain = _get_cms_domain(endpoint_name)
        if domain not in cms_catalog:
            cms_catalog[domain] = {}

        # Use short key (strip juniper_ or jps_ prefix for readability)
        short_key = endpoint_name
        for prefix in ("juniper_", "jps_"):
            if short_key.startswith(prefix):
                short_key = short_key[len(prefix):]
                break

        friendly = _get_friendly_name(endpoint_name)
        filters = CMS_DOMAIN_FILTERS.get(domain, ["device"])

        cms_catalog[domain][short_key] = {
            "endpoint": f"cms:{endpoint_name}",
            "display_name": friendly,
            "methods": ["GET", "POST", "PATCH", "DELETE"],
            "filters": filters,
            "description": f"{friendly} configuration records",
        }

    return cms_catalog
