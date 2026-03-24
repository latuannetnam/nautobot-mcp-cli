"""Workflow catalog stubs for the API catalog.

Lists all available workflows with params, descriptions, and which
endpoints they aggregate. Actual function references are added in
Phase 17 (Workflow Registry).
"""

WORKFLOW_STUBS = {
    "bgp_summary": {
        "params": {"device": "str (required)", "detail": "bool (optional)"},
        "description": "BGP groups, neighbors, address families for a device",
        "aggregates": [
            "cms:juniper_bgp_groups",
            "cms:juniper_bgp_neighbors",
            "cms:juniper_bgp_address_families",
            "cms:juniper_bgp_policy_associations",
        ],
    },
    "routing_table": {
        "params": {"device": "str (required)", "routing_table": "str (optional, default inet.0)"},
        "description": "Static routes with nexthops for a device",
        "aggregates": [
            "cms:juniper_static_routes",
            "cms:juniper_static_route_nexthops",
            "cms:juniper_static_route_qualified_nexthops",
        ],
    },
    "firewall_summary": {
        "params": {"device": "str (required)"},
        "description": "Firewall filters, terms, match conditions, and actions",
        "aggregates": [
            "cms:juniper_firewall_filters",
            "cms:juniper_firewall_terms",
            "cms:juniper_firewall_match_conditions",
            "cms:juniper_firewall_actions",
        ],
    },
    "interface_detail": {
        "params": {"device": "str (required)", "interface_name": "str (optional)"},
        "description": "Interface units, families, VRRP groups for a device",
        "aggregates": [
            "cms:juniper_interface_units",
            "cms:juniper_interface_families",
            "cms:juniper_interface_vrrp_groups",
        ],
    },
    "onboard_config": {
        "params": {
            "config_json": "str (required)",
            "device_name": "str (required)",
            "dry_run": "bool (optional, default true)",
        },
        "description": "Parse and onboard JunOS config into Nautobot CMS models",
        "aggregates": ["cms:*"],
    },
    "compare_device": {
        "params": {"device_name": "str (required)", "live_data": "dict (required)"},
        "description": "Compare live device state against Nautobot records",
        "aggregates": ["/api/dcim/devices/", "/api/dcim/interfaces/", "/api/ipam/ip-addresses/"],
    },
    "verify_data_model": {
        "params": {"device_name": "str (required)"},
        "description": "Verify device data model consistency in Nautobot",
        "aggregates": ["/api/dcim/devices/", "/api/dcim/interfaces/", "/api/ipam/ip-addresses/"],
    },
    "verify_compliance": {
        "params": {"device_name": "str (required)"},
        "description": "Check device compliance against Golden Config rules",
        "aggregates": ["plugins:golden_config"],
    },
    "compare_bgp": {
        "params": {"device": "str (required)", "live_neighbors": "list (required)"},
        "description": "Compare live BGP neighbors against CMS records",
        "aggregates": [
            "cms:juniper_bgp_groups",
            "cms:juniper_bgp_neighbors",
        ],
    },
    "compare_routes": {
        "params": {"device": "str (required)", "live_routes": "list (required)"},
        "description": "Compare live routes against CMS static route records",
        "aggregates": [
            "cms:juniper_static_routes",
            "cms:juniper_static_route_nexthops",
        ],
    },
}
