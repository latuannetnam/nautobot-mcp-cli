"""Static catalog of core Nautobot REST API endpoints.

Curated subset of endpoints useful for network automation agents.
Admin-only endpoints (object_changes, custom_fields, etc.) are excluded.
"""

CORE_ENDPOINTS = {
    "dcim": {
        "devices": {
            "endpoint": "/api/dcim/devices/",
            "methods": ["GET", "POST", "PATCH", "DELETE"],
            "filters": ["name", "location", "role", "status", "tenant", "platform", "q"],
            "description": "Network devices (routers, switches, firewalls)",
        },
        "interfaces": {
            "endpoint": "/api/dcim/interfaces/",
            "methods": ["GET", "POST", "PATCH", "DELETE"],
            "filters": ["device", "device_id", "name", "type", "enabled"],
            "description": "Device interfaces (physical and virtual ports)",
        },
        "device_types": {
            "endpoint": "/api/dcim/device-types/",
            "methods": ["GET", "POST", "PATCH", "DELETE"],
            "filters": ["manufacturer", "model", "q"],
            "description": "Device hardware models",
        },
        "platforms": {
            "endpoint": "/api/dcim/platforms/",
            "methods": ["GET", "POST"],
            "filters": ["name", "manufacturer"],
            "description": "Software platforms (JunOS, IOS-XR, etc.)",
        },
        "locations": {
            "endpoint": "/api/dcim/locations/",
            "methods": ["GET", "POST", "PATCH", "DELETE"],
            "filters": ["name", "location_type", "parent", "tenant", "q"],
            "description": "Physical locations (sites, buildings, floors)",
        },
        "manufacturers": {
            "endpoint": "/api/dcim/manufacturers/",
            "methods": ["GET", "POST"],
            "filters": ["name", "q"],
            "description": "Device manufacturers (Juniper, Cisco, etc.)",
        },
    },
    "ipam": {
        "ip_addresses": {
            "endpoint": "/api/ipam/ip-addresses/",
            "methods": ["GET", "POST", "PATCH", "DELETE"],
            "filters": ["address", "device", "interface", "namespace", "status"],
            "description": "IP addresses assigned to devices",
        },
        "prefixes": {
            "endpoint": "/api/ipam/prefixes/",
            "methods": ["GET", "POST", "PATCH", "DELETE"],
            "filters": ["prefix", "namespace", "location", "tenant", "status"],
            "description": "IP network prefixes (subnets)",
        },
        "vlans": {
            "endpoint": "/api/ipam/vlans/",
            "methods": ["GET", "POST", "PATCH", "DELETE"],
            "filters": ["vid", "name", "location", "tenant", "status"],
            "description": "VLANs for network segmentation",
        },
        "namespaces": {
            "endpoint": "/api/ipam/namespaces/",
            "methods": ["GET", "POST"],
            "filters": ["name"],
            "description": "IP address namespaces for uniqueness",
        },
    },
    "circuits": {
        "circuits": {
            "endpoint": "/api/circuits/circuits/",
            "methods": ["GET", "POST", "PATCH", "DELETE"],
            "filters": ["provider", "circuit_type", "status", "location", "q"],
            "description": "Network circuits (WAN links, internet, MPLS)",
        },
        "providers": {
            "endpoint": "/api/circuits/providers/",
            "methods": ["GET", "POST", "PATCH", "DELETE"],
            "filters": ["name", "q"],
            "description": "Circuit providers (ISPs, carriers)",
        },
        "circuit_types": {
            "endpoint": "/api/circuits/circuit-types/",
            "methods": ["GET", "POST"],
            "filters": ["name"],
            "description": "Circuit type classifications",
        },
    },
    "tenancy": {
        "tenants": {
            "endpoint": "/api/tenancy/tenants/",
            "methods": ["GET", "POST", "PATCH", "DELETE"],
            "filters": ["name", "q"],
            "description": "Organizational tenants",
        },
        "tenant_groups": {
            "endpoint": "/api/tenancy/tenant-groups/",
            "methods": ["GET", "POST"],
            "filters": ["name", "q"],
            "description": "Tenant group hierarchy",
        },
    },
}
