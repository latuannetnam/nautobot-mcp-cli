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

# Per-endpoint primary FK filters (derived from codebase analysis of cms_list() call sites)
CMS_ENDPOINT_FILTERS: dict[str, list[str]] = {
    # Routing — Static Routes
    "juniper_static_routes": ["device"],
    "juniper_static_route_nexthops": ["route"],
    "juniper_static_route_qualified_nexthops": ["route"],
    # Routing — BGP
    "juniper_bgp_groups": ["device"],
    "juniper_bgp_neighbors": ["group"],
    "juniper_bgp_address_families": ["group", "neighbor"],
    "juniper_bgp_policy_associations": ["group", "neighbor"],
    "juniper_bgp_received_routes": ["neighbor"],
    # Interfaces
    "juniper_interface_units": ["device"],
    "juniper_interface_families": ["interface_unit"],
    "juniper_interface_family_filters": ["interface_family"],
    "juniper_interface_family_policers": ["interface_family"],
    "juniper_interface_vrrp_groups": ["interface_family"],
    "vrrp_track_routes": ["vrrp_group"],
    "vrrp_track_interfaces": ["vrrp_group"],
    # Firewalls
    "juniper_firewall_filters": ["device"],
    "juniper_firewall_terms": ["firewall_filter"],
    "juniper_firewall_match_conditions": ["firewall_term"],
    "juniper_firewall_actions": ["firewall_term"],
    "juniper_firewall_policers": ["device"],
    "juniper_firewall_policer_actions": ["policer"],
    "juniper_firewall_match_condition_prefix_lists": ["match_condition"],
    # Policies — Statements
    "juniper_policy_statements": ["device"],
    "jps_terms": ["policy_statement"],
    "jps_match_conditions": ["jps_term"],
    "jps_match_condition_route_filters": ["match_condition"],
    "jps_match_condition_prefix_lists": ["match_condition"],
    "jps_match_condition_communities": ["match_condition"],
    "jps_match_condition_as_paths": ["match_condition"],
    "jps_actions": ["jps_term"],
    "jps_action_communities": ["action"],
    "jps_action_as_paths": ["action"],
    "jps_action_load_balances": ["action"],
    "jps_action_install_nexthops": ["action"],
    # Policies — Standalone
    "juniper_policy_as_paths": ["device"],
    "juniper_policy_communities": ["device"],
    "juniper_policy_prefix_lists": ["device"],
    "juniper_policy_prefixes": ["prefix_list"],
    # ARP
    "juniper_arp_entries": ["device"],
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
        filters = CMS_ENDPOINT_FILTERS.get(endpoint_name, [])

        cms_catalog[domain][short_key] = {
            "endpoint": f"cms:{endpoint_name}",
            "display_name": friendly,
            "methods": ["GET", "POST", "PATCH", "DELETE"],
            "filters": filters,
            "description": f"{friendly} configuration records",
        }

    return cms_catalog
