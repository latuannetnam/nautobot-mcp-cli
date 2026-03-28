"""Workflow catalog stubs for the API catalog.

Lists all available workflows with params, descriptions, and which
endpoints they aggregate. Actual function references are added in
Phase 17 (Workflow Registry).
"""

WORKFLOW_STUBS = {
    "bgp_summary": {
        "params": {"device": "str (required)", "detail": "bool (optional)", "limit": "int (optional, default 0)"},
        "description": "BGP groups, neighbors, address families for a device",
        "aggregates": [
            "cms:juniper_bgp_groups",
            "cms:juniper_bgp_neighbors",
            "cms:juniper_bgp_address_families",
            "cms:juniper_bgp_policy_associations",
        ],
    },
    "routing_table": {
        "params": {"device": "str (required)", "detail": "bool (optional, default false)", "limit": "int (optional, default 0)"},
        "description": "Static routes with nexthops for a device",
        "aggregates": [
            "cms:juniper_static_routes",
            "cms:juniper_static_route_nexthops",
            "cms:juniper_static_route_qualified_nexthops",
        ],
    },
    "firewall_summary": {
        "params": {"device": "str (required)", "detail": "bool (optional, default false)", "limit": "int (optional, default 0)"},
        "description": "Firewall filters, terms, match conditions, and actions",
        "aggregates": [
            "cms:juniper_firewall_filters",
            "cms:juniper_firewall_terms",
            "cms:juniper_firewall_match_conditions",
            "cms:juniper_firewall_actions",
        ],
    },
    "interface_detail": {
        "params": {
            "device": "str (required)",
            "include_arp": "bool (optional, default false)",
            "detail": "bool (optional, default true)",
            "limit": "int (optional, default 0)",
        },
        "description": "Interface units, families, VRRP groups for a device",
        "aggregates": [
            "cms:juniper_interface_units",
            "cms:juniper_interface_families",
            "cms:juniper_interface_vrrp_groups",
        ],
    },
    "onboard_config": {
        "params": {
            "config_data": "dict (required, ParsedConfig schema)",
            "device_name": "str (required)",
            "dry_run": "bool (optional, default true)",
        },
        "description": "Parse and onboard JunOS config into Nautobot CMS models",
        "aggregates": ["cms:*"],
    },
    "compare_device": {
        "params": {
            "device_name": "str (required)",
            "live_data": "dict (required, {iface_name: {ips: [...], vlans: [...]}})",
        },
        "description": "Compare live device state against Nautobot records",
        "aggregates": ["/api/dcim/devices/", "/api/dcim/interfaces/", "/api/ipam/ip-addresses/"],
    },
    "verify_data_model": {
        "params": {
            "device_name": "str (required)",
            "parsed_config": "dict (required, ParsedConfig schema)",
        },
        "description": "Verify device data model consistency in Nautobot",
        "aggregates": ["/api/dcim/devices/", "/api/dcim/interfaces/", "/api/ipam/ip-addresses/"],
    },
    "verify_compliance": {
        "params": {"device_name": "str (required)"},
        "description": "Check device compliance against Golden Config rules",
        "aggregates": ["plugins:golden_config"],
    },
    "compare_bgp": {
        "params": {"device_name": "str (required)", "live_neighbors": "list (required)"},
        "description": "Compare live BGP neighbors against CMS records",
        "aggregates": [
            "cms:juniper_bgp_groups",
            "cms:juniper_bgp_neighbors",
        ],
    },
    "compare_routes": {
        "params": {"device_name": "str (required)", "live_routes": "list (required)"},
        "description": "Compare live routes against CMS static route records",
        "aggregates": [
            "cms:juniper_static_routes",
            "cms:juniper_static_route_nexthops",
        ],
    },
    "devices_inventory": {
        "params": {
            "device": "str (required)",
            "detail": "str (optional, 'interfaces'|'ips'|'vlans'|'all', default: 'interfaces')",
            "limit": "int (optional, default 50)",
            "offset": "int (optional, default 0)",
        },
        "description": "Paginated device inventory: interfaces, IPs, VLANs with bulk fetches",
        "aggregates": [
            "/api/dcim/interfaces/",
            "/api/ipam/ip-addresses/",
            "/api/ipam/vlans/",
        ],
    },
}
