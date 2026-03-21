"""FastMCP server exposing Nautobot operations as MCP tools.

Each core function is wrapped as an individual @mcp.tool with nautobot_ prefix,
rich descriptions, and structured error handling via ToolError.
"""

from __future__ import annotations

from typing import Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from nautobot_mcp.client import NautobotClient
from nautobot_mcp.config import NautobotSettings
from nautobot_mcp.exceptions import NautobotMCPError

# Domain imports
from nautobot_mcp import circuits, devices, interfaces, ipam, organization
from nautobot_mcp import golden_config as gc
from nautobot_mcp import onboarding, verification
from nautobot_mcp import drift
from nautobot_mcp.parsers import ParserRegistry
from nautobot_mcp.cms import firewalls as cms_firewalls
from nautobot_mcp.cms import interfaces as cms_interfaces
from nautobot_mcp.cms import policies as cms_policies
from nautobot_mcp.cms import routing as cms_routing
from nautobot_mcp.cms import arp as cms_arp

mcp = FastMCP("Nautobot MCP Server")

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


# ===========================================================================
# DEVICE TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_list_devices")
def nautobot_list_devices(
    location: Optional[str] = None,
    tenant: Optional[str] = None,
    role: Optional[str] = None,
    platform: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List devices from Nautobot with optional filtering.

    Args:
        location: Filter by location name.
        tenant: Filter by tenant name.
        role: Filter by device role name.
        platform: Filter by platform name.
        q: Full-text search query.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with 'count' (total) and 'results' (list of device dicts).
    """
    try:
        client = get_client()
        result = devices.list_devices(
            client, location=location, tenant=tenant, role=role,
            platform=platform, q=q, limit=limit,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_get_device")
def nautobot_get_device(
    name: Optional[str] = None,
    id: Optional[str] = None,
) -> dict:
    """Get a single device by name or UUID.

    Args:
        name: Device hostname.
        id: Device UUID.

    Returns:
        Device dict with name, status, location, role, device_type, platform, etc.
    """
    try:
        client = get_client()
        result = devices.get_device(client, name=name, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_create_device")
def nautobot_create_device(
    name: str,
    device_type: str,
    location: str,
    role: str,
    status: str = "Active",
) -> dict:
    """Create a new device in Nautobot.

    Args:
        name: Device hostname.
        device_type: Device type name (must exist in Nautobot).
        location: Location name (must exist in Nautobot).
        role: Device role name (must exist in Nautobot).
        status: Device status (default: Active).

    Returns:
        Created device dict.
    """
    try:
        client = get_client()
        result = devices.create_device(
            client, name=name, device_type=device_type,
            location=location, role=role, status=status,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_update_device")
def nautobot_update_device(
    id: str,
    name: Optional[str] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
) -> dict:
    """Update an existing device.

    Args:
        id: Device UUID.
        name: New hostname (optional).
        status: New status (optional).
        role: New role (optional).

    Returns:
        Updated device dict.
    """
    try:
        client = get_client()
        updates = {}
        if name is not None:
            updates["name"] = name
        if status is not None:
            updates["status"] = status
        if role is not None:
            updates["role"] = role
        result = devices.update_device(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_delete_device")
def nautobot_delete_device(id: str) -> dict:
    """Delete a device from Nautobot.

    Args:
        id: Device UUID to delete.

    Returns:
        Dict with success status and message.
    """
    try:
        client = get_client()
        devices.delete_device(client, id=id)
        return {"success": True, "message": "Device deleted"}
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_device_summary")
def nautobot_device_summary(
    device_name: str,
) -> dict:
    """Get complete device overview in one call: info, interfaces, IPs, VLANs, and counts.

    Answers "tell me everything about device X" — no need to call multiple tools.
    Includes interface count, IP count, VLAN count, and link state statistics.

    Args:
        device_name: Device hostname (exact match).

    Returns:
        Dict with device (info), interfaces (list), interface_ips (list),
        vlans (list), and counts (interface_count, ip_count, vlan_count,
        enabled_count, disabled_count).
    """
    try:
        client = get_client()
        result = devices.get_device_summary(client, name=device_name)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# INTERFACE TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_list_interfaces")
def nautobot_list_interfaces(
    device: Optional[str] = None,
    device_id: Optional[str] = None,
    include_ips: bool = False,
    limit: int = 50,
) -> dict:
    """List interfaces with optional device filtering and IP enrichment.

    Args:
        device: Filter by parent device name.
        device_id: Filter by parent device UUID.
        include_ips: If True, enrich each interface with its assigned IP
            addresses via M2M batch query. Each interface's ip_addresses
            field will contain rich objects with address, status, and IDs.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with 'count' and 'results' (list of interface dicts).
    """
    try:
        client = get_client()
        result = interfaces.list_interfaces(
            client, device_name=device, device_id=device_id,
            include_ips=include_ips, limit=limit,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_get_interface")
def nautobot_get_interface(
    id: Optional[str] = None,
    device_name: Optional[str] = None,
    name: Optional[str] = None,
) -> dict:
    """Get a single interface by ID or device_name+name.

    Args:
        id: Interface UUID.
        device_name: Parent device name (used with name).
        name: Interface name (used with device_name).

    Returns:
        Interface dict with name, type, enabled, description, etc.
    """
    try:
        client = get_client()
        result = interfaces.get_interface(
            client, id=id, device_name=device_name, name=name,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_create_interface")
def nautobot_create_interface(
    device: str,
    name: str,
    type: str = "1000base-t",
) -> dict:
    """Create a new interface on a device.

    Args:
        device: Parent device name.
        name: Interface name (e.g., GigabitEthernet0/1).
        type: Interface type (default: 1000base-t).

    Returns:
        Created interface dict.
    """
    try:
        client = get_client()
        result = interfaces.create_interface(
            client, device=device, name=name, type=type,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_update_interface")
def nautobot_update_interface(
    id: str,
    name: Optional[str] = None,
    enabled: Optional[bool] = None,
    description: Optional[str] = None,
) -> dict:
    """Update an existing interface.

    Args:
        id: Interface UUID.
        name: New name (optional).
        enabled: Enable/disable (optional).
        description: New description (optional).

    Returns:
        Updated interface dict.
    """
    try:
        client = get_client()
        updates = {}
        if name is not None:
            updates["name"] = name
        if enabled is not None:
            updates["enabled"] = enabled
        if description is not None:
            updates["description"] = description
        result = interfaces.update_interface(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_assign_ip_to_interface")
def nautobot_assign_ip_to_interface(
    interface_id: str,
    ip_address_id: str,
) -> dict:
    """Assign an IP address to an interface.

    Uses Nautobot v2 IPAddressToInterface M2M association.

    Args:
        interface_id: UUID of the interface.
        ip_address_id: UUID of the IP address.

    Returns:
        Dict with assignment details (id, interface, ip_address, status).
    """
    try:
        client = get_client()
        return interfaces.assign_ip_to_interface(
            client, interface_id=interface_id, ip_address_id=ip_address_id,
        )
    except Exception as e:
        handle_error(e)


# ===========================================================================
# IPAM TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_list_prefixes")
def nautobot_list_prefixes(
    namespace: Optional[str] = None,
    location: Optional[str] = None,
    tenant: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List IP prefixes with optional filtering.

    Args:
        namespace: Filter by namespace name.
        location: Filter by location name.
        tenant: Filter by tenant name.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with 'count' and 'results' (list of prefix dicts).
    """
    try:
        client = get_client()
        result = ipam.list_prefixes(
            client, namespace=namespace, location=location, tenant=tenant,
            limit=limit,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_create_prefix")
def nautobot_create_prefix(
    prefix: str,
    namespace: str = "Global",
    status: str = "Active",
) -> dict:
    """Create a new IP prefix. Nautobot v2 requires Namespace for uniqueness.

    Args:
        prefix: Network prefix in CIDR notation (e.g., 10.0.0.0/24).
        namespace: Namespace name (default: Global).
        status: Prefix status (default: Active).

    Returns:
        Created prefix dict.
    """
    try:
        client = get_client()
        result = ipam.create_prefix(
            client, prefix=prefix, namespace=namespace, status=status,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_list_ip_addresses")
def nautobot_list_ip_addresses(
    device: Optional[str] = None,
    interface: Optional[str] = None,
    prefix: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List IP addresses with optional filtering.

    Args:
        device: Filter by device name.
        interface: Filter by interface name.
        prefix: Filter by parent prefix.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with 'count' and 'results' (list of IP address dicts).
    """
    try:
        client = get_client()
        result = ipam.list_ip_addresses(
            client, device=device, interface=interface, prefix=prefix,
            limit=limit,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_create_ip_address")
def nautobot_create_ip_address(
    address: str,
    namespace: str = "Global",
    status: str = "Active",
) -> dict:
    """Create a new IP address. Nautobot v2 requires Namespace.

    Args:
        address: IP address with mask (e.g., 10.0.0.1/24).
        namespace: Namespace name (default: Global).
        status: Address status (default: Active).

    Returns:
        Created IP address dict.
    """
    try:
        client = get_client()
        result = ipam.create_ip_address(
            client, address=address, namespace=namespace, status=status,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_get_device_ips")
def nautobot_get_device_ips(
    device_name: str,
) -> dict:
    """Get all IP addresses assigned to a device's interfaces in one call.

    Returns IPs mapped to their interfaces — answers "what IPs does device X have?"
    without needing to query interfaces and IP-to-interface M2M records separately.

    Args:
        device_name: Device hostname (exact match).

    Returns:
        Dict with device_name, total_ips, interface_ips (list of {interface_name,
        interface_id, address, ip_id, status}), and unlinked_ips.
    """
    try:
        client = get_client()
        result = ipam.get_device_ips(client, device_name=device_name)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


def nautobot_list_vlans(
    location: Optional[str] = None,
    tenant: Optional[str] = None,
    device_name: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List VLANs with optional filtering.

    Args:
        location: Filter by location name.
        tenant: Filter by tenant name.
        device_name: Filter by device name — returns only VLANs on device's interfaces.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with 'count' and 'results' (list of VLAN dicts).
    """
    try:
        client = get_client()
        result = ipam.list_vlans(
            client, location=location, tenant=tenant,
            device=device_name, limit=limit,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_create_vlan")
def nautobot_create_vlan(
    vid: int,
    name: str,
    status: str = "Active",
) -> dict:
    """Create a new VLAN.

    Args:
        vid: VLAN ID (1-4094).
        name: VLAN name.
        status: VLAN status (default: Active).

    Returns:
        Created VLAN dict.
    """
    try:
        client = get_client()
        result = ipam.create_vlan(
            client, vid=vid, name=name, status=status,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# ORGANIZATION TOOLS — Tenants
# ===========================================================================


@mcp.tool(name="nautobot_list_tenants")
def nautobot_list_tenants(
    q: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List tenants with optional search.

    Args:
        q: Full-text search query.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with 'count' and 'results' (list of tenant dicts).
    """
    try:
        client = get_client()
        result = organization.list_tenants(client, q=q, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_get_tenant")
def nautobot_get_tenant(
    name: Optional[str] = None,
    id: Optional[str] = None,
) -> dict:
    """Get a single tenant by name or UUID.

    Args:
        name: Tenant name.
        id: Tenant UUID.

    Returns:
        Tenant dict with name, description, etc.
    """
    try:
        client = get_client()
        result = organization.get_tenant(client, name=name, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_create_tenant")
def nautobot_create_tenant(name: str) -> dict:
    """Create a new tenant.

    Args:
        name: Tenant name.

    Returns:
        Created tenant dict.
    """
    try:
        client = get_client()
        result = organization.create_tenant(client, name=name)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_update_tenant")
def nautobot_update_tenant(
    id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Update an existing tenant.

    Args:
        id: Tenant UUID.
        name: New name (optional).
        description: New description (optional).

    Returns:
        Updated tenant dict.
    """
    try:
        client = get_client()
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        result = organization.update_tenant(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# ORGANIZATION TOOLS — Locations
# ===========================================================================


@mcp.tool(name="nautobot_list_locations")
def nautobot_list_locations(
    location_type: Optional[str] = None,
    parent: Optional[str] = None,
    tenant: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List locations with optional filtering.

    Args:
        location_type: Filter by location type name.
        parent: Filter by parent location name.
        tenant: Filter by tenant name.
        q: Full-text search query.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with 'count' and 'results' (list of location dicts).
    """
    try:
        client = get_client()
        result = organization.list_locations(
            client, location_type=location_type, parent=parent,
            tenant=tenant, q=q, limit=limit,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_get_location")
def nautobot_get_location(
    name: Optional[str] = None,
    id: Optional[str] = None,
) -> dict:
    """Get a single location by name or UUID.

    Args:
        name: Location name.
        id: Location UUID.

    Returns:
        Location dict with name, location_type, parent, etc.
    """
    try:
        client = get_client()
        result = organization.get_location(client, name=name, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_create_location")
def nautobot_create_location(
    name: str,
    location_type: str,
    status: str = "Active",
) -> dict:
    """Create a new location.

    Args:
        name: Location name.
        location_type: Location type name (must exist in Nautobot).
        status: Location status (default: Active).

    Returns:
        Created location dict.
    """
    try:
        client = get_client()
        result = organization.create_location(
            client, name=name, location_type=location_type, status=status,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_update_location")
def nautobot_update_location(
    id: str,
    name: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """Update an existing location.

    Args:
        id: Location UUID.
        name: New name (optional).
        status: New status (optional).

    Returns:
        Updated location dict.
    """
    try:
        client = get_client()
        updates = {}
        if name is not None:
            updates["name"] = name
        if status is not None:
            updates["status"] = status
        result = organization.update_location(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# CIRCUIT TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_list_circuits")
def nautobot_list_circuits(
    provider: Optional[str] = None,
    circuit_type: Optional[str] = None,
    location: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List circuits with optional filtering.

    Args:
        provider: Filter by provider name.
        circuit_type: Filter by circuit type name.
        location: Filter by location name.
        q: Full-text search query.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with 'count' and 'results' (list of circuit dicts).
    """
    try:
        client = get_client()
        result = circuits.list_circuits(
            client, provider=provider, circuit_type=circuit_type,
            location=location, q=q, limit=limit,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_get_circuit")
def nautobot_get_circuit(
    cid: Optional[str] = None,
    id: Optional[str] = None,
) -> dict:
    """Get a single circuit by circuit ID or UUID.

    Args:
        cid: Circuit identifier string.
        id: Circuit UUID.

    Returns:
        Circuit dict with cid, provider, circuit_type, status, etc.
    """
    try:
        client = get_client()
        result = circuits.get_circuit(client, cid=cid, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_create_circuit")
def nautobot_create_circuit(
    cid: str,
    provider: str,
    circuit_type: str,
    status: str = "Active",
) -> dict:
    """Create a new circuit.

    Args:
        cid: Circuit identifier string.
        provider: Provider name (must exist in Nautobot).
        circuit_type: Circuit type name (must exist in Nautobot).
        status: Circuit status (default: Active).

    Returns:
        Created circuit dict.
    """
    try:
        client = get_client()
        result = circuits.create_circuit(
            client, cid=cid, provider=provider, circuit_type=circuit_type,
            status=status,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_update_circuit")
def nautobot_update_circuit(
    id: str,
    cid: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """Update an existing circuit.

    Args:
        id: Circuit UUID.
        cid: New circuit identifier (optional).
        status: New status (optional).

    Returns:
        Updated circuit dict.
    """
    try:
        client = get_client()
        updates = {}
        if cid is not None:
            updates["cid"] = cid
        if status is not None:
            updates["status"] = status
        result = circuits.update_circuit(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# GOLDEN CONFIG TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_get_intended_config")
def nautobot_get_intended_config(device: str) -> dict:
    """Retrieve the intended (golden) configuration for a device.

    Returns the full config text that should be on the device.

    Args:
        device: Device name or UUID.

    Returns:
        Dict with device, intended_config, backup_config fields.
    """
    try:
        client = get_client()
        result = gc.get_intended_config(client, device)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_get_backup_config")
def nautobot_get_backup_config(device: str) -> dict:
    """Retrieve the backup (actual) configuration for a device.

    Returns the last collected config from the device.

    Args:
        device: Device name or UUID.

    Returns:
        Dict with device, intended_config, backup_config fields.
    """
    try:
        client = get_client()
        result = gc.get_backup_config(client, device)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_list_compliance_features")
def nautobot_list_compliance_features() -> dict:
    """List all compliance features defined in Golden Config.

    Returns:
        Dict with 'count' and 'results' (list of feature dicts).
    """
    try:
        client = get_client()
        result = gc.list_compliance_features(client)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_create_compliance_feature")
def nautobot_create_compliance_feature(
    name: str,
    slug: str,
    description: str = "",
) -> dict:
    """Create a new compliance feature.

    Args:
        name: Feature name.
        slug: Feature slug.
        description: Optional description.

    Returns:
        Created compliance feature dict.
    """
    try:
        client = get_client()
        result = gc.create_compliance_feature(client, name=name, slug=slug, description=description)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_delete_compliance_feature")
def nautobot_delete_compliance_feature(feature_id: str) -> dict:
    """Delete a compliance feature.

    Args:
        feature_id: UUID of the compliance feature.

    Returns:
        Dict with success status.
    """
    try:
        client = get_client()
        return gc.delete_compliance_feature(client, feature_id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_list_compliance_rules")
def nautobot_list_compliance_rules(
    feature: Optional[str] = None,
    platform: Optional[str] = None,
) -> dict:
    """List compliance rules with optional filtering.

    Args:
        feature: Filter by feature name.
        platform: Filter by platform slug.

    Returns:
        Dict with 'count' and 'results' (list of rule dicts).
    """
    try:
        client = get_client()
        result = gc.list_compliance_rules(client, feature=feature, platform=platform)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_create_compliance_rule")
def nautobot_create_compliance_rule(
    feature: str,
    platform: str,
    config_ordered: bool = False,
    match_config: str = "",
    description: str = "",
) -> dict:
    """Create a new compliance rule.

    Args:
        feature: Feature name to associate.
        platform: Platform slug.
        config_ordered: Whether config order matters.
        match_config: Regex/pattern to match config sections.
        description: Optional description.

    Returns:
        Created compliance rule dict.
    """
    try:
        client = get_client()
        result = gc.create_compliance_rule(
            client, feature=feature, platform=platform,
            config_ordered=config_ordered, match_config=match_config,
            description=description,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_update_compliance_rule")
def nautobot_update_compliance_rule(
    rule_id: str,
    config_ordered: Optional[bool] = None,
    match_config: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Update an existing compliance rule.

    Args:
        rule_id: UUID of the rule.
        config_ordered: New value for config ordering.
        match_config: New match config pattern.
        description: New description.

    Returns:
        Updated compliance rule dict.
    """
    try:
        client = get_client()
        updates = {}
        if config_ordered is not None:
            updates["config_ordered"] = config_ordered
        if match_config is not None:
            updates["match_config"] = match_config
        if description is not None:
            updates["description"] = description
        result = gc.update_compliance_rule(client, rule_id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_delete_compliance_rule")
def nautobot_delete_compliance_rule(rule_id: str) -> dict:
    """Delete a compliance rule.

    Args:
        rule_id: UUID of the compliance rule.

    Returns:
        Dict with success status.
    """
    try:
        client = get_client()
        return gc.delete_compliance_rule(client, rule_id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_get_compliance_results")
def nautobot_get_compliance_results(device: str) -> dict:
    """Get compliance results for a device from Golden Config.

    Returns per-feature compliance status (compliant/non-compliant).

    Args:
        device: Device name or UUID.

    Returns:
        ComplianceResult dict with device, overall_status, features.
    """
    try:
        client = get_client()
        result = gc.get_compliance_results(client, device)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_quick_diff_config")
def nautobot_quick_diff_config(device: str) -> dict:
    """Quick diff intended vs backup config for a device.

    Uses difflib to compare configs without running a full compliance check.

    Args:
        device: Device name or UUID.

    Returns:
        ComplianceResult dict with diff-based compliance status.
    """
    try:
        client = get_client()
        result = gc.quick_diff_config(client, device)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# PARSER TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_parse_config")
def nautobot_parse_config(
    config_json: str,
    network_os: str = "juniper_junos",
) -> dict:
    """Parse a device configuration JSON to extract structured network data.

    Supports JunOS (show configuration | display json).
    Returns interfaces, IPs, VLANs, routing instances, protocols,
    firewall filters, and system settings.

    Args:
        config_json: Raw JSON string of the device configuration.
        network_os: Parser identifier (default: juniper_junos).

    Returns:
        ParsedConfig dict with all extracted network data.
    """
    try:
        import json
        config_data = json.loads(config_json)
        parser = ParserRegistry.get(network_os)
        result = parser.parse(config_data)
        return result.model_dump()
    except ValueError as e:
        raise ToolError(str(e))
    except json.JSONDecodeError as e:
        raise ToolError(f"Invalid JSON: {str(e)}")
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_list_parsers")
def nautobot_list_parsers() -> dict:
    """List available configuration parsers and their supported network_os identifiers.

    Returns:
        Dict with 'parsers' list of registered parser identifiers.
    """
    return {"parsers": ParserRegistry.list_parsers()}

# ===========================================================================
# ONBOARDING TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_onboard_config")
def nautobot_onboard_config(
    config_json: str,
    device_name: str,
    network_os: str = "juniper_junos",
    dry_run: bool = True,
    update_existing: bool = False,
    location: Optional[str] = None,
    device_type: Optional[str] = None,
    role: str = "Router",
    namespace: str = "Global",
) -> dict:
    """Onboard a parsed router config into Nautobot.

    Parses the config, then creates/updates device, interfaces, IPs, and VLANs.
    Default is dry-run mode (shows planned changes without committing).

    Args:
        config_json: Raw JSON string of the device configuration.
        device_name: Target device name in Nautobot.
        network_os: Parser identifier (default: juniper_junos).
        dry_run: If True, show planned changes without committing.
        update_existing: If True, update existing objects with new values.
        location: Device location name.
        device_type: Device type name.
        role: Device role (default: Router).
        namespace: IPAM namespace (default: Global).

    Returns:
        OnboardResult dict with summary, actions, and warnings.
    """
    try:
        import json as json_mod
        config_data = json_mod.loads(config_json)
        parser = ParserRegistry.get(network_os)
        parsed_config = parser.parse(config_data)
        client = get_client()
        result = onboarding.onboard_config(
            client, parsed_config, device_name,
            dry_run=dry_run, update_existing=update_existing,
            location=location, device_type=device_type,
            role=role, namespace=namespace,
        )
        return result.model_dump()
    except ValueError as e:
        raise ToolError(str(e))
    except Exception as e:
        handle_error(e)


# ===========================================================================
# VERIFICATION TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_verify_config_compliance")
def nautobot_verify_config_compliance(device: str) -> dict:
    """Compare device's intended vs backup config using Golden Config.

    Runs a quick diff and returns structured compliance results.

    Args:
        device: Device name or UUID.

    Returns:
        DriftReport dict with config_compliance field.
    """
    try:
        client = get_client()
        result = verification.verify_config_compliance(client, device)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_verify_data_model")
def nautobot_verify_data_model(
    config_json: str,
    device_name: str,
    network_os: str = "juniper_junos",
) -> dict:
    """Compare parsed device config against Nautobot data model records.

    Uses DiffSync for object-by-object comparison across interfaces,
    IP addresses, and VLANs. Returns a structured drift report.

    Args:
        config_json: Raw JSON string of the device configuration.
        device_name: Device name in Nautobot.
        network_os: Parser identifier (default: juniper_junos).

    Returns:
        DriftReport dict with interface, IP, VLAN drift sections and summary.
    """
    try:
        import json as json_mod
        config_data = json_mod.loads(config_json)
        parser = ParserRegistry.get(network_os)
        parsed_config = parser.parse(config_data)
        client = get_client()
        result = verification.verify_data_model(client, device_name, parsed_config)
        return result.model_dump()
    except ValueError as e:
        raise ToolError(str(e))
    except Exception as e:
        handle_error(e)


# ===========================================================================
# DRIFT TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_compare_device")
def nautobot_compare_device(
    device_name: str,
    interfaces_data: dict | list,
) -> dict:
    """Compare structured interface data against Nautobot records — no config file needed.

    Accepts two input shapes (auto-detected):
    1. Flat map: {"ae0.0": {"ips": ["10.1.1.1/30"], "vlans": [100]}, "ge-0/0/0.0": {"ips": ["192.168.1.1/24"]}}
    2. DeviceIPEntry list: [{"interface": "ae0", "address": "10.1.1.1/30"}, ...]
       (output from nautobot_get_device_ips can be passed directly)

    Compares per-interface: IPs and VLANs. Returns per-interface drift detail + global summary.
    Lenient validation: accepts IPs with or without prefix length, warns when normalizing.

    Args:
        device_name: Device hostname in Nautobot (exact match).
        interfaces_data: Interface data to compare. Dict maps interface names to
            {"ips": [...], "vlans": [...]}. List accepts DeviceIPEntry objects.

    Returns:
        QuickDriftReport dict with interface_drifts (per-interface detail),
        summary (global counts), and warnings.
    """
    try:
        client = get_client()
        result = drift.compare_device(client, device_name, interfaces_data)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# CMS ROUTING TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_cms_list_static_routes")
def nautobot_cms_list_static_routes(
    device: str,
    routing_instance: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List Juniper static routes for a device with inlined next-hops.

    Args:
        device: Device name or UUID.
        routing_instance: Filter by routing instance name (e.g. "mgmt").
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results. Each route includes nexthops and
        qualified_nexthops inlined.
    """
    try:
        client = get_client()
        result = cms_routing.list_static_routes(
            client, device=device, routing_instance=routing_instance, limit=limit
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_static_route")
def nautobot_cms_get_static_route(id: str) -> dict:
    """Get a single Juniper static route by UUID, with inlined next-hops.

    Args:
        id: Static route UUID.

    Returns:
        Static route dict with nexthops and qualified_nexthops inlined.
    """
    try:
        client = get_client()
        result = cms_routing.get_static_route(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_static_route")
def nautobot_cms_create_static_route(
    device: str,
    destination: str,
    routing_table: str = "inet.0",
    preference: int = 5,
) -> dict:
    """Create a Juniper static route.

    Args:
        device: Device name or UUID.
        destination: Route destination prefix (e.g. "192.168.1.0/24").
        routing_table: Routing table name (default: inet.0).
        preference: Administrative distance (default: 5).

    Returns:
        Created static route dict.
    """
    try:
        client = get_client()
        result = cms_routing.create_static_route(
            client, device=device, destination=destination,
            routing_table=routing_table, preference=preference,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_update_static_route")
def nautobot_cms_update_static_route(
    id: str,
    preference: Optional[int] = None,
    metric: Optional[int] = None,
    enabled: Optional[bool] = None,
) -> dict:
    """Update a Juniper static route.

    Args:
        id: Static route UUID.
        preference: New preference (optional).
        metric: New metric (optional).
        enabled: Enable/disable (optional).

    Returns:
        Updated static route dict.
    """
    try:
        client = get_client()
        updates = {}
        if preference is not None:
            updates["preference"] = preference
        if metric is not None:
            updates["metric"] = metric
        if enabled is not None:
            updates["enabled"] = enabled
        result = cms_routing.update_static_route(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_static_route")
def nautobot_cms_delete_static_route(id: str) -> dict:
    """Delete a Juniper static route.

    Args:
        id: Static route UUID.

    Returns:
        Dict with success status and message.
    """
    try:
        client = get_client()
        return cms_routing.delete_static_route(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_bgp_groups")
def nautobot_cms_list_bgp_groups(
    device: str,
    routing_instance: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List Juniper BGP groups for a device.

    Args:
        device: Device name or UUID.
        routing_instance: Filter by routing instance name (optional).
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (list of BGP group dicts).
    """
    try:
        client = get_client()
        result = cms_routing.list_bgp_groups(
            client, device=device, routing_instance=routing_instance, limit=limit
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_bgp_group")
def nautobot_cms_get_bgp_group(id: str) -> dict:
    """Get a single Juniper BGP group by UUID.

    Args:
        id: BGP group UUID.

    Returns:
        BGP group dict.
    """
    try:
        client = get_client()
        result = cms_routing.get_bgp_group(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_bgp_group")
def nautobot_cms_create_bgp_group(
    device: str,
    name: str,
    type: str,
    local_address: Optional[str] = None,
    cluster_id: Optional[str] = None,
) -> dict:
    """Create a Juniper BGP group.

    Args:
        device: Device name or UUID.
        name: BGP group name.
        type: Group type ('internal' or 'external').
        local_address: Local address IP UUID (optional).
        cluster_id: Cluster ID for route reflector (optional).

    Returns:
        Created BGP group dict.
    """
    try:
        client = get_client()
        kwargs = {}
        if local_address is not None:
            kwargs["local_address"] = local_address
        if cluster_id is not None:
            kwargs["cluster_id"] = cluster_id
        result = cms_routing.create_bgp_group(
            client, device=device, name=name, type=type, **kwargs
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_update_bgp_group")
def nautobot_cms_update_bgp_group(
    id: str,
    name: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> dict:
    """Update a Juniper BGP group.

    Args:
        id: BGP group UUID.
        name: New name (optional).
        enabled: Enable/disable (optional).

    Returns:
        Updated BGP group dict.
    """
    try:
        client = get_client()
        updates = {}
        if name is not None:
            updates["name"] = name
        if enabled is not None:
            updates["enabled"] = enabled
        result = cms_routing.update_bgp_group(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_bgp_group")
def nautobot_cms_delete_bgp_group(id: str) -> dict:
    """Delete a Juniper BGP group.

    Args:
        id: BGP group UUID.

    Returns:
        Dict with success status and message.
    """
    try:
        client = get_client()
        return cms_routing.delete_bgp_group(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_bgp_neighbors")
def nautobot_cms_list_bgp_neighbors(
    device: Optional[str] = None,
    group_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List BGP neighbors. Provide device name to see all neighbors across all groups
    for device, or group_id for a specific group.

    Args:
        device: Device name or UUID (device-scoped query via all groups).
        group_id: Filter by specific BGP group UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (list of BGP neighbor dicts).
    """
    try:
        client = get_client()
        result = cms_routing.list_bgp_neighbors(
            client, device=device, group_id=group_id, limit=limit
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_bgp_neighbor")
def nautobot_cms_get_bgp_neighbor(id: str) -> dict:
    """Get a single BGP neighbor by UUID.

    Args:
        id: BGP neighbor UUID.

    Returns:
        BGP neighbor dict with session state and prefix counts.
    """
    try:
        client = get_client()
        result = cms_routing.get_bgp_neighbor(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_bgp_neighbor")
def nautobot_cms_create_bgp_neighbor(
    group_id: str,
    peer_ip: str,
    peer_as: Optional[int] = None,
    description: Optional[str] = None,
) -> dict:
    """Create a BGP neighbor.

    Args:
        group_id: Parent BGP group UUID.
        peer_ip: Peer IP address UUID or string.
        peer_as: Peer autonomous system number (optional).
        description: Neighbor description (optional).

    Returns:
        Created BGP neighbor dict.
    """
    try:
        client = get_client()
        kwargs = {}
        if peer_as is not None:
            kwargs["peer_as"] = peer_as
        if description is not None:
            kwargs["description"] = description
        result = cms_routing.create_bgp_neighbor(
            client, group_id=group_id, peer_ip=peer_ip, **kwargs
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_update_bgp_neighbor")
def nautobot_cms_update_bgp_neighbor(
    id: str,
    peer_as: Optional[int] = None,
    enabled: Optional[bool] = None,
    description: Optional[str] = None,
) -> dict:
    """Update a BGP neighbor.

    Args:
        id: BGP neighbor UUID.
        peer_as: New peer AS (optional).
        enabled: Enable/disable (optional).
        description: New description (optional).

    Returns:
        Updated BGP neighbor dict.
    """
    try:
        client = get_client()
        updates = {}
        if peer_as is not None:
            updates["peer_as"] = peer_as
        if enabled is not None:
            updates["enabled"] = enabled
        if description is not None:
            updates["description"] = description
        result = cms_routing.update_bgp_neighbor(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_bgp_neighbor")
def nautobot_cms_delete_bgp_neighbor(id: str) -> dict:
    """Delete a BGP neighbor.

    Args:
        id: BGP neighbor UUID.

    Returns:
        Dict with success status and message.
    """
    try:
        client = get_client()
        return cms_routing.delete_bgp_neighbor(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_bgp_address_families")
def nautobot_cms_list_bgp_address_families(
    group_id: Optional[str] = None,
    neighbor_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List BGP address families, optionally filtered by group or neighbor.

    Args:
        group_id: Filter by BGP group UUID.
        neighbor_id: Filter by BGP neighbor UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (read-only).
    """
    try:
        client = get_client()
        result = cms_routing.list_bgp_address_families(
            client, group_id=group_id, neighbor_id=neighbor_id, limit=limit
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_bgp_policy_associations")
def nautobot_cms_list_bgp_policy_associations(
    group_id: Optional[str] = None,
    neighbor_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List BGP policy associations, optionally filtered by group or neighbor.

    Args:
        group_id: Filter by BGP group UUID.
        neighbor_id: Filter by BGP neighbor UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (read-only).
    """
    try:
        client = get_client()
        result = cms_routing.list_bgp_policy_associations(
            client, group_id=group_id, neighbor_id=neighbor_id, limit=limit
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_bgp_received_routes")
def nautobot_cms_list_bgp_received_routes(
    neighbor_id: str,
    limit: int = 50,
) -> dict:
    """List BGP received routes for a specific BGP neighbor (read-only).

    Args:
        neighbor_id: BGP neighbor UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (BGP received route dicts).
    """
    try:
        client = get_client()
        result = cms_routing.list_bgp_received_routes(
            client, neighbor_id=neighbor_id, limit=limit
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_static_route_nexthops")
def nautobot_cms_list_static_route_nexthops(
    route_id: Optional[str] = None,
    device: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List static route nexthops, optionally filtered by route or device.

    Args:
        route_id: Filter by parent static route UUID.
        device: Filter by device name or UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (read-only).
    """
    try:
        client = get_client()
        result = cms_routing.list_static_route_nexthops(
            client, route_id=route_id, device=device, limit=limit
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# CMS ROUTING COMPOSITE TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_cms_get_device_bgp_summary")
def nautobot_cms_get_device_bgp_summary(
    device: str,
    detail: bool = False,
) -> dict:
    """Get a composite BGP summary for a Juniper device.

    Aggregates all BGP groups and their neighbors into a single response.
    In detail mode, each neighbor includes its address families and policy
    associations inline.

    Args:
        device: Device name or UUID.
        detail: If True, include address families and policy associations per neighbor.

    Returns:
        Dict with device_name, groups (with nested neighbors), total_groups,
        total_neighbors.
    """
    try:
        client = get_client()
        result = cms_routing.get_device_bgp_summary(client, device=device, detail=detail)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_device_routing_table")
def nautobot_cms_get_device_routing_table(
    device: str,
    detail: bool = False,
) -> dict:
    """Get a composite routing table summary for a Juniper device.

    Returns all static routes for the device. In default mode, nexthop counts
    are included but not the full nexthop list. In detail mode, all nexthops
    and qualified nexthops are inlined per route.

    Args:
        device: Device name or UUID.
        detail: If True, include full nexthop data per route.

    Returns:
        Dict with device_name, routes (list), total_routes.
    """
    try:
        client = get_client()
        result = cms_routing.get_device_routing_table(client, device=device, detail=detail)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# CMS INTERFACE TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_cms_list_interface_units")
def nautobot_cms_list_interface_units(
    device: str,
    limit: int = 50,
) -> dict:
    """List Juniper interface units for a device. Returns shallow list with family_count per unit.

    Args:
        device: Device name or UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (each unit has family_count).
    """
    try:
        client = get_client()
        result = cms_interfaces.list_interface_units(client, device=device, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_interface_unit")
def nautobot_cms_get_interface_unit(id: str) -> dict:
    """Get a single interface unit with inlined family details (filters, policers).

    Args:
        id: Interface unit UUID.

    Returns:
        Interface unit dict with family_count populated.
    """
    try:
        client = get_client()
        result = cms_interfaces.get_interface_unit(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_interface_unit")
def nautobot_cms_create_interface_unit(
    interface_id: str,
    vlan_mode: Optional[str] = None,
    encapsulation: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Create a Juniper interface unit.

    Args:
        interface_id: UUID of the parent interface.
        vlan_mode: VLAN mode (access, trunk, etc.).
        encapsulation: Encapsulation type.
        description: Unit description.

    Returns:
        Created interface unit dict.
    """
    try:
        client = get_client()
        kwargs = {}
        if vlan_mode is not None:
            kwargs["vlan_mode"] = vlan_mode
        if encapsulation is not None:
            kwargs["encapsulation"] = encapsulation
        if description is not None:
            kwargs["description"] = description
        result = cms_interfaces.create_interface_unit(client, interface_id=interface_id, **kwargs)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_update_interface_unit")
def nautobot_cms_update_interface_unit(
    id: str,
    vlan_mode: Optional[str] = None,
    encapsulation: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Update a Juniper interface unit.

    Args:
        id: Interface unit UUID.
        vlan_mode: New VLAN mode.
        encapsulation: New encapsulation type.
        description: New description.

    Returns:
        Updated interface unit dict.
    """
    try:
        client = get_client()
        updates = {}
        if vlan_mode is not None:
            updates["vlan_mode"] = vlan_mode
        if encapsulation is not None:
            updates["encapsulation"] = encapsulation
        if description is not None:
            updates["description"] = description
        result = cms_interfaces.update_interface_unit(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_interface_unit")
def nautobot_cms_delete_interface_unit(id: str) -> dict:
    """Delete a Juniper interface unit.

    Args:
        id: Interface unit UUID.

    Returns:
        Dict with success status.
    """
    try:
        client = get_client()
        return cms_interfaces.delete_interface_unit(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_interface_families")
def nautobot_cms_list_interface_families(
    unit_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List interface families, optionally filtered by interface unit.

    Args:
        unit_id: Filter by parent interface unit UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results.
    """
    try:
        client = get_client()
        result = cms_interfaces.list_interface_families(client, unit_id=unit_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_interface_family")
def nautobot_cms_get_interface_family(id: str) -> dict:
    """Get a single interface family by UUID.

    Args:
        id: Interface family UUID.

    Returns:
        Interface family dict.
    """
    try:
        client = get_client()
        result = cms_interfaces.get_interface_family(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_interface_family")
def nautobot_cms_create_interface_family(
    unit_id: str,
    family_type: str,
) -> dict:
    """Create a Juniper interface family.

    Args:
        unit_id: UUID of the parent interface unit.
        family_type: Address family type (inet, inet6, mpls, etc.).

    Returns:
        Created interface family dict.
    """
    try:
        client = get_client()
        result = cms_interfaces.create_interface_family(client, unit_id=unit_id, family_type=family_type)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_update_interface_family")
def nautobot_cms_update_interface_family(
    id: str,
    family_type: Optional[str] = None,
) -> dict:
    """Update a Juniper interface family.

    Args:
        id: Interface family UUID.
        family_type: New family type.

    Returns:
        Updated interface family dict.
    """
    try:
        client = get_client()
        updates = {}
        if family_type is not None:
            updates["family_type"] = family_type
        result = cms_interfaces.update_interface_family(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_interface_family")
def nautobot_cms_delete_interface_family(id: str) -> dict:
    """Delete a Juniper interface family.

    Args:
        id: Interface family UUID.

    Returns:
        Dict with success status.
    """
    try:
        client = get_client()
        return cms_interfaces.delete_interface_family(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_interface_family_filters")
def nautobot_cms_list_interface_family_filters(
    family_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List interface family filter associations, optionally filtered by family.

    Args:
        family_id: Filter by parent interface family UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (read-only associations).
    """
    try:
        client = get_client()
        result = cms_interfaces.list_interface_family_filters(client, family_id=family_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_interface_family_filter")
def nautobot_cms_get_interface_family_filter(id: str) -> dict:
    """Get a single interface family filter association by UUID.

    Args:
        id: Filter association UUID.

    Returns:
        Filter association dict.
    """
    try:
        client = get_client()
        result = cms_interfaces.get_interface_family_filter(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_interface_family_filter")
def nautobot_cms_create_interface_family_filter(
    family_id: str,
    filter_id: str,
    filter_type: str,
    enabled: bool = True,
) -> dict:
    """Create an interface family filter association.

    Args:
        family_id: UUID of the parent interface family.
        filter_id: UUID of the filter to associate.
        filter_type: Filter direction/type (input, output, etc.).
        enabled: Whether the association is active.

    Returns:
        Created filter association dict.
    """
    try:
        client = get_client()
        result = cms_interfaces.create_interface_family_filter(
            client, family_id=family_id, filter_id=filter_id,
            filter_type=filter_type, enabled=enabled,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_interface_family_filter")
def nautobot_cms_delete_interface_family_filter(id: str) -> dict:
    """Delete an interface family filter association.

    Args:
        id: Filter association UUID.

    Returns:
        Dict with success status.
    """
    try:
        client = get_client()
        return cms_interfaces.delete_interface_family_filter(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_interface_family_policers")
def nautobot_cms_list_interface_family_policers(
    family_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List interface family policer associations, optionally filtered by family.

    Args:
        family_id: Filter by parent interface family UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results.
    """
    try:
        client = get_client()
        result = cms_interfaces.list_interface_family_policers(client, family_id=family_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_interface_family_policer")
def nautobot_cms_get_interface_family_policer(id: str) -> dict:
    """Get a single interface family policer association by UUID.

    Args:
        id: Policer association UUID.

    Returns:
        Policer association dict.
    """
    try:
        client = get_client()
        result = cms_interfaces.get_interface_family_policer(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_interface_family_policer")
def nautobot_cms_create_interface_family_policer(
    family_id: str,
    policer_id: str,
    policer_type: str,
    enabled: bool = True,
) -> dict:
    """Create an interface family policer association.

    Args:
        family_id: UUID of the parent interface family.
        policer_id: UUID of the policer to associate.
        policer_type: Policer direction/type (input, output, etc.).
        enabled: Whether the association is active.

    Returns:
        Created policer association dict.
    """
    try:
        client = get_client()
        result = cms_interfaces.create_interface_family_policer(
            client, family_id=family_id, policer_id=policer_id,
            policer_type=policer_type, enabled=enabled,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_interface_family_policer")
def nautobot_cms_delete_interface_family_policer(id: str) -> dict:
    """Delete an interface family policer association.

    Args:
        id: Policer association UUID.

    Returns:
        Dict with success status.
    """
    try:
        client = get_client()
        return cms_interfaces.delete_interface_family_policer(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_vrrp_groups")
def nautobot_cms_list_vrrp_groups(
    family_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List VRRP groups, optionally filtered by interface family.

    Args:
        family_id: Filter by parent interface family UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results.
    """
    try:
        client = get_client()
        result = cms_interfaces.list_vrrp_groups(client, family_id=family_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_vrrp_group")
def nautobot_cms_get_vrrp_group(id: str) -> dict:
    """Get a single VRRP group by UUID.

    Args:
        id: VRRP group UUID.

    Returns:
        VRRP group dict.
    """
    try:
        client = get_client()
        result = cms_interfaces.get_vrrp_group(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_vrrp_group")
def nautobot_cms_create_vrrp_group(
    family_id: str,
    group_number: int,
    virtual_address_id: str,
    priority: int = 100,
) -> dict:
    """Create a VRRP group.

    Args:
        family_id: UUID of the parent interface family.
        group_number: VRRP group number (1-255).
        virtual_address_id: UUID of the virtual IP address.
        priority: VRRP priority (1-254, default 100).

    Returns:
        Created VRRP group dict.
    """
    try:
        client = get_client()
        result = cms_interfaces.create_vrrp_group(
            client, family_id=family_id, group_number=group_number,
            virtual_address_id=virtual_address_id, priority=priority,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_update_vrrp_group")
def nautobot_cms_update_vrrp_group(
    id: str,
    priority: Optional[int] = None,
    accept_data: Optional[bool] = None,
    preempt_hold_time: Optional[int] = None,
) -> dict:
    """Update a VRRP group.

    Args:
        id: VRRP group UUID.
        priority: New priority (optional).
        accept_data: Accept data for virtual IP (optional).
        preempt_hold_time: Preempt hold time in seconds (optional).

    Returns:
        Updated VRRP group dict.
    """
    try:
        client = get_client()
        updates = {}
        if priority is not None:
            updates["priority"] = priority
        if accept_data is not None:
            updates["accept_data"] = accept_data
        if preempt_hold_time is not None:
            updates["preempt_hold_time"] = preempt_hold_time
        result = cms_interfaces.update_vrrp_group(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_vrrp_group")
def nautobot_cms_delete_vrrp_group(id: str) -> dict:
    """Delete a VRRP group.

    Args:
        id: VRRP group UUID.

    Returns:
        Dict with success status.
    """
    try:
        client = get_client()
        return cms_interfaces.delete_vrrp_group(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_vrrp_track_routes")
def nautobot_cms_list_vrrp_track_routes(
    vrrp_group_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List VRRP tracked routes (read-only), optionally filtered by VRRP group.

    Args:
        vrrp_group_id: Filter by parent VRRP group UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results.
    """
    try:
        client = get_client()
        result = cms_interfaces.list_vrrp_track_routes(client, vrrp_group_id=vrrp_group_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_vrrp_track_route")
def nautobot_cms_get_vrrp_track_route(id: str) -> dict:
    """Get a single VRRP tracked route by UUID (read-only).

    Args:
        id: VRRP track route UUID.

    Returns:
        VRRP track route dict.
    """
    try:
        client = get_client()
        result = cms_interfaces.get_vrrp_track_route(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_vrrp_track_interfaces")
def nautobot_cms_list_vrrp_track_interfaces(
    vrrp_group_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List VRRP tracked interfaces (read-only), optionally filtered by VRRP group.

    Args:
        vrrp_group_id: Filter by parent VRRP group UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results.
    """
    try:
        client = get_client()
        result = cms_interfaces.list_vrrp_track_interfaces(client, vrrp_group_id=vrrp_group_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_vrrp_track_interface")
def nautobot_cms_get_vrrp_track_interface(id: str) -> dict:
    """Get a single VRRP tracked interface by UUID (read-only).

    Args:
        id: VRRP track interface UUID.

    Returns:
        VRRP track interface dict.
    """
    try:
        client = get_client()
        result = cms_interfaces.get_vrrp_track_interface(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# CMS INTERFACE COMPOSITE TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_cms_get_interface_detail")
def nautobot_cms_get_interface_detail(
    device: str,
    include_arp: bool = False,
) -> dict:
    """Get a composite interface detail summary for a Juniper device.

    Aggregates all interface units with their sub-families and VRRP groups
    in one call. Optionally includes ARP entries per interface.

    Args:
        device: Device name or UUID.
        include_arp: If True, include ARP entries for the device, matched
            by interface name.

    Returns:
        Dict with device_name, units (with nested families and vrrp_groups),
        total_units, and optionally arp_entries.
    """
    try:
        client = get_client()
        result = cms_interfaces.get_interface_detail(client, device=device, include_arp=include_arp)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_device_firewall_summary")
def nautobot_cms_get_device_firewall_summary(
    device: str,
    detail: bool = False,
) -> dict:
    """Get a composite firewall summary for a Juniper device.

    Returns all firewall filters (with term counts) and policers (with
    action counts) for a device. In detail mode, each filter includes its
    terms inlined and each policer includes its actions.

    Args:
        device: Device name or UUID.
        detail: If True, include inlined terms per filter and actions per policer.

    Returns:
        Dict with device_name, filters (list), policers (list),
        total_filters, total_policers.
    """
    try:
        client = get_client()
        result = cms_firewalls.get_device_firewall_summary(client, device=device, detail=detail)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# CMS FIREWALL TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_cms_list_firewall_filters")
def nautobot_cms_list_firewall_filters(
    device: str,
    family: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List Juniper firewall filters for a device.

    Args:
        device: Device name or UUID.
        family: Address family filter (inet, inet6, vpls, etc.).
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (each filter has term_count).
    """
    try:
        client = get_client()
        result = cms_firewalls.list_firewall_filters(client, device=device, family=family, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_firewall_filter")
def nautobot_cms_get_firewall_filter(id: str) -> dict:
    """Get a firewall filter with inlined term summaries.

    Args:
        id: Firewall filter UUID.

    Returns:
        Filter dict with term_count and terms list.
    """
    try:
        client = get_client()
        result = cms_firewalls.get_firewall_filter(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_firewall_filter")
def nautobot_cms_create_firewall_filter(
    device: str,
    name: str,
    family: str = "inet",
    description: Optional[str] = None,
) -> dict:
    """Create a Juniper firewall filter.

    Args:
        device: Device name or UUID.
        name: Filter name.
        family: Address family (inet, inet6, vpls). Default: inet.
        description: Optional description.

    Returns:
        Created filter dict.
    """
    try:
        client = get_client()
        kwargs = {}
        if description is not None:
            kwargs["description"] = description
        result = cms_firewalls.create_firewall_filter(client, device=device, name=name, family=family, **kwargs)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_update_firewall_filter")
def nautobot_cms_update_firewall_filter(
    id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Update a Juniper firewall filter.

    Args:
        id: Filter UUID.
        name: New name (optional).
        description: New description (optional).

    Returns:
        Updated filter dict.
    """
    try:
        client = get_client()
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        result = cms_firewalls.update_firewall_filter(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_firewall_filter")
def nautobot_cms_delete_firewall_filter(id: str) -> dict:
    """Delete a Juniper firewall filter.

    Args:
        id: Filter UUID.

    Returns:
        Dict with success status.
    """
    try:
        client = get_client()
        return cms_firewalls.delete_firewall_filter(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_firewall_policers")
def nautobot_cms_list_firewall_policers(
    device: str,
    limit: int = 50,
) -> dict:
    """List Juniper firewall policers for a device.

    Args:
        device: Device name or UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (each policer has action_count).
    """
    try:
        client = get_client()
        result = cms_firewalls.list_firewall_policers(client, device=device, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_firewall_policer")
def nautobot_cms_get_firewall_policer(id: str) -> dict:
    """Get a firewall policer with inlined actions.

    Args:
        id: Policer UUID.

    Returns:
        Policer dict with action_count and actions list.
    """
    try:
        client = get_client()
        result = cms_firewalls.get_firewall_policer(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_firewall_policer")
def nautobot_cms_create_firewall_policer(
    device: str,
    name: str,
    description: Optional[str] = None,
) -> dict:
    """Create a Juniper firewall policer.

    Args:
        device: Device name or UUID.
        name: Policer name.
        description: Optional description.

    Returns:
        Created policer dict.
    """
    try:
        client = get_client()
        kwargs = {}
        if description is not None:
            kwargs["description"] = description
        result = cms_firewalls.create_firewall_policer(client, device=device, name=name, **kwargs)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_update_firewall_policer")
def nautobot_cms_update_firewall_policer(
    id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Update a Juniper firewall policer.

    Args:
        id: Policer UUID.
        name: New name (optional).
        description: New description (optional).

    Returns:
        Updated policer dict.
    """
    try:
        client = get_client()
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        result = cms_firewalls.update_firewall_policer(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_firewall_policer")
def nautobot_cms_delete_firewall_policer(id: str) -> dict:
    """Delete a Juniper firewall policer.

    Args:
        id: Policer UUID.

    Returns:
        Dict with success status.
    """
    try:
        client = get_client()
        return cms_firewalls.delete_firewall_policer(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_firewall_terms")
def nautobot_cms_list_firewall_terms(
    filter_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List firewall terms (read-only), optionally by parent filter.

    Args:
        filter_id: Filter by parent firewall filter UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (each term has match_count, action_count).
    """
    try:
        client = get_client()
        result = cms_firewalls.list_firewall_terms(client, filter_id=filter_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_firewall_term")
def nautobot_cms_get_firewall_term(id: str) -> dict:
    """Get a firewall term with inlined match conditions and actions.

    Args:
        id: Term UUID.

    Returns:
        Term dict with match_conditions and actions lists.
    """
    try:
        client = get_client()
        result = cms_firewalls.get_firewall_term(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_firewall_match_conditions")
def nautobot_cms_list_firewall_match_conditions(
    term_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List firewall match conditions (read-only), optionally by parent term.

    Args:
        term_id: Filter by parent firewall term UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_firewalls.list_firewall_match_conditions(client, term_id=term_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_firewall_match_condition")
def nautobot_cms_get_firewall_match_condition(id: str) -> dict:
    """Get a single firewall match condition by UUID."""
    try:
        client = get_client()
        result = cms_firewalls.get_firewall_match_condition(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_firewall_filter_actions")
def nautobot_cms_list_firewall_filter_actions(
    term_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List firewall filter actions (read-only), optionally by parent term.

    Args:
        term_id: Filter by parent firewall term UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_firewalls.list_firewall_filter_actions(client, term_id=term_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_firewall_filter_action")
def nautobot_cms_get_firewall_filter_action(id: str) -> dict:
    """Get a single firewall filter action by UUID."""
    try:
        client = get_client()
        result = cms_firewalls.get_firewall_filter_action(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_firewall_policer_actions")
def nautobot_cms_list_firewall_policer_actions(
    policer_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List firewall policer actions (read-only), optionally by parent policer.

    Args:
        policer_id: Filter by parent policer UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_firewalls.list_firewall_policer_actions(client, policer_id=policer_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_firewall_policer_action")
def nautobot_cms_get_firewall_policer_action(id: str) -> dict:
    """Get a single firewall policer action by UUID."""
    try:
        client = get_client()
        result = cms_firewalls.get_firewall_policer_action(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_firewall_match_condition_prefix_lists")
def nautobot_cms_list_firewall_match_condition_prefix_lists(
    match_condition_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List firewall match condition to prefix list associations (read-only).

    Args:
        match_condition_id: Filter by parent match condition UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_firewalls.list_firewall_match_condition_prefix_lists(
            client, match_condition_id=match_condition_id, limit=limit
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_firewall_match_condition_prefix_list")
def nautobot_cms_get_firewall_match_condition_prefix_list(id: str) -> dict:
    """Get a single firewall match condition to prefix list association by UUID."""
    try:
        client = get_client()
        result = cms_firewalls.get_firewall_match_condition_prefix_list(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# CMS POLICY TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_cms_list_policy_statements")
def nautobot_cms_list_policy_statements(
    device: str,
    limit: int = 50,
) -> dict:
    """List Juniper policy statements for a device.

    Args:
        device: Device name or UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (each statement has term_count).
    """
    try:
        client = get_client()
        result = cms_policies.list_policy_statements(client, device=device, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_policy_statement")
def nautobot_cms_get_policy_statement(id: str) -> dict:
    """Get a policy statement with inlined term summaries.

    Args:
        id: Policy statement UUID.

    Returns:
        Statement dict with term_count and terms list.
    """
    try:
        client = get_client()
        result = cms_policies.get_policy_statement(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_policy_statement")
def nautobot_cms_create_policy_statement(
    device: str,
    name: str,
    description: Optional[str] = None,
) -> dict:
    """Create a Juniper policy statement.

    Args:
        device: Device name or UUID.
        name: Statement name.
        description: Optional description.

    Returns:
        Created statement dict.
    """
    try:
        client = get_client()
        kwargs = {}
        if description is not None:
            kwargs["description"] = description
        result = cms_policies.create_policy_statement(client, device=device, name=name, **kwargs)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_update_policy_statement")
def nautobot_cms_update_policy_statement(
    id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Update a Juniper policy statement.

    Args:
        id: Statement UUID.
        name: New name (optional).
        description: New description (optional).

    Returns:
        Updated statement dict.
    """
    try:
        client = get_client()
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        result = cms_policies.update_policy_statement(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_policy_statement")
def nautobot_cms_delete_policy_statement(id: str) -> dict:
    """Delete a Juniper policy statement.

    Args:
        id: Statement UUID.

    Returns:
        Dict with success status.
    """
    try:
        client = get_client()
        return cms_policies.delete_policy_statement(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_policy_prefix_lists")
def nautobot_cms_list_policy_prefix_lists(
    device: str,
    limit: int = 50,
) -> dict:
    """List Juniper policy prefix lists for a device.

    Args:
        device: Device name or UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (each list has prefix_count).
    """
    try:
        client = get_client()
        result = cms_policies.list_policy_prefix_lists(client, device=device, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_policy_prefix_list")
def nautobot_cms_get_policy_prefix_list(id: str) -> dict:
    """Get a policy prefix list with inlined prefixes.

    Args:
        id: Prefix list UUID.

    Returns:
        Prefix list dict with prefix_count and prefixes list.
    """
    try:
        client = get_client()
        result = cms_policies.get_policy_prefix_list(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_policy_prefix_list")
def nautobot_cms_create_policy_prefix_list(
    device: str,
    name: str,
    description: Optional[str] = None,
) -> dict:
    """Create a Juniper policy prefix list.

    Args:
        device: Device name or UUID.
        name: Prefix list name.
        description: Optional description.

    Returns:
        Created prefix list dict.
    """
    try:
        client = get_client()
        kwargs = {}
        if description is not None:
            kwargs["description"] = description
        result = cms_policies.create_policy_prefix_list(client, device=device, name=name, **kwargs)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_update_policy_prefix_list")
def nautobot_cms_update_policy_prefix_list(
    id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Update a Juniper policy prefix list.

    Args:
        id: Prefix list UUID.
        name: New name (optional).
        description: New description (optional).

    Returns:
        Updated prefix list dict.
    """
    try:
        client = get_client()
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        result = cms_policies.update_policy_prefix_list(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_policy_prefix_list")
def nautobot_cms_delete_policy_prefix_list(id: str) -> dict:
    """Delete a Juniper policy prefix list.

    Args:
        id: Prefix list UUID.

    Returns:
        Dict with success status.
    """
    try:
        client = get_client()
        return cms_policies.delete_policy_prefix_list(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_policy_communities")
def nautobot_cms_list_policy_communities(
    device: str,
    limit: int = 50,
) -> dict:
    """List Juniper policy communities for a device.

    Args:
        device: Device name or UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_policy_communities(client, device=device, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_policy_community")
def nautobot_cms_get_policy_community(id: str) -> dict:
    """Get a single policy community by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_policy_community(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_policy_community")
def nautobot_cms_create_policy_community(
    device: str,
    name: str,
    members: str,
    description: Optional[str] = None,
) -> dict:
    """Create a Juniper policy community.

    Args:
        device: Device name or UUID.
        name: Community name.
        members: Community value string (e.g. '65000:100').
        description: Optional description.

    Returns:
        Created community dict.
    """
    try:
        client = get_client()
        kwargs = {}
        if description is not None:
            kwargs["description"] = description
        result = cms_policies.create_policy_community(client, device=device, name=name, members=members, **kwargs)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_update_policy_community")
def nautobot_cms_update_policy_community(
    id: str,
    name: Optional[str] = None,
    members: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Update a Juniper policy community.

    Args:
        id: Community UUID.
        name: New name (optional).
        members: New community value string (optional).
        description: New description (optional).

    Returns:
        Updated community dict.
    """
    try:
        client = get_client()
        updates = {}
        if name is not None:
            updates["name"] = name
        if members is not None:
            updates["members"] = members
        if description is not None:
            updates["description"] = description
        result = cms_policies.update_policy_community(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_policy_community")
def nautobot_cms_delete_policy_community(id: str) -> dict:
    """Delete a Juniper policy community."""
    try:
        client = get_client()
        return cms_policies.delete_policy_community(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_policy_as_paths")
def nautobot_cms_list_policy_as_paths(
    device: str,
    limit: int = 50,
) -> dict:
    """List Juniper policy AS paths for a device.

    Args:
        device: Device name or UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_policy_as_paths(client, device=device, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_policy_as_path")
def nautobot_cms_get_policy_as_path(id: str) -> dict:
    """Get a single policy AS path by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_policy_as_path(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_create_policy_as_path")
def nautobot_cms_create_policy_as_path(
    device: str,
    name: str,
    regex: str,
    description: Optional[str] = None,
) -> dict:
    """Create a Juniper policy AS path.

    Args:
        device: Device name or UUID.
        name: AS-path name.
        regex: AS-path regular expression.
        description: Optional description.

    Returns:
        Created AS path dict.
    """
    try:
        client = get_client()
        kwargs = {}
        if description is not None:
            kwargs["description"] = description
        result = cms_policies.create_policy_as_path(client, device=device, name=name, regex=regex, **kwargs)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_update_policy_as_path")
def nautobot_cms_update_policy_as_path(
    id: str,
    name: Optional[str] = None,
    regex: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Update a Juniper policy AS path.

    Args:
        id: AS path UUID.
        name: New name (optional).
        regex: New AS-path regex (optional).
        description: New description (optional).

    Returns:
        Updated AS path dict.
    """
    try:
        client = get_client()
        updates = {}
        if name is not None:
            updates["name"] = name
        if regex is not None:
            updates["regex"] = regex
        if description is not None:
            updates["description"] = description
        result = cms_policies.update_policy_as_path(client, id=id, **updates)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_delete_policy_as_path")
def nautobot_cms_delete_policy_as_path(id: str) -> dict:
    """Delete a Juniper policy AS path."""
    try:
        client = get_client()
        return cms_policies.delete_policy_as_path(client, id=id)
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_policy_prefixes")
def nautobot_cms_list_policy_prefixes(
    prefix_list_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List policy prefixes (read-only), optionally by parent prefix list.

    Args:
        prefix_list_id: Filter by parent prefix list UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_policy_prefixes(client, prefix_list_id=prefix_list_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_policy_prefix")
def nautobot_cms_get_policy_prefix(id: str) -> dict:
    """Get a single policy prefix by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_policy_prefix(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_jps_terms")
def nautobot_cms_list_jps_terms(
    statement_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List JPS terms (read-only), optionally by parent policy statement.

    Args:
        statement_id: Filter by parent policy statement UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with count and results (each term has match_count, action_count).
    """
    try:
        client = get_client()
        result = cms_policies.list_jps_terms(client, statement_id=statement_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_jps_term")
def nautobot_cms_get_jps_term(id: str) -> dict:
    """Get a JPS term with inlined match conditions and actions.

    Args:
        id: JPS term UUID.

    Returns:
        Term dict with match_conditions and actions lists.
    """
    try:
        client = get_client()
        result = cms_policies.get_jps_term(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_jps_match_conditions")
def nautobot_cms_list_jps_match_conditions(
    term_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List JPS match conditions (read-only), optionally by parent term.

    Args:
        term_id: Filter by parent JPS term UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_jps_match_conditions(client, term_id=term_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_jps_match_condition")
def nautobot_cms_get_jps_match_condition(id: str) -> dict:
    """Get a single JPS match condition by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_jps_match_condition(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_jps_match_condition_route_filters")
def nautobot_cms_list_jps_match_condition_route_filters(
    match_condition_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List JPS match condition route filters (read-only).

    Args:
        match_condition_id: Filter by parent match condition UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_jps_match_condition_route_filters(
            client, match_condition_id=match_condition_id, limit=limit
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_jps_match_condition_route_filter")
def nautobot_cms_get_jps_match_condition_route_filter(id: str) -> dict:
    """Get a single JPS match condition route filter by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_jps_match_condition_route_filter(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_jps_match_condition_prefix_lists")
def nautobot_cms_list_jps_match_condition_prefix_lists(
    match_condition_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List JPS match condition prefix list associations (read-only).

    Args:
        match_condition_id: Filter by parent match condition UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_jps_match_condition_prefix_lists(
            client, match_condition_id=match_condition_id, limit=limit
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_jps_match_condition_prefix_list")
def nautobot_cms_get_jps_match_condition_prefix_list(id: str) -> dict:
    """Get a single JPS match condition prefix list association by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_jps_match_condition_prefix_list(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_jps_match_condition_communities")
def nautobot_cms_list_jps_match_condition_communities(
    match_condition_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List JPS match condition community associations (read-only).

    Args:
        match_condition_id: Filter by parent match condition UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_jps_match_condition_communities(
            client, match_condition_id=match_condition_id, limit=limit
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_jps_match_condition_community")
def nautobot_cms_get_jps_match_condition_community(id: str) -> dict:
    """Get a single JPS match condition community association by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_jps_match_condition_community(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_jps_match_condition_as_paths")
def nautobot_cms_list_jps_match_condition_as_paths(
    match_condition_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List JPS match condition AS path associations (read-only).

    Args:
        match_condition_id: Filter by parent match condition UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_jps_match_condition_as_paths(
            client, match_condition_id=match_condition_id, limit=limit
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_jps_match_condition_as_path")
def nautobot_cms_get_jps_match_condition_as_path(id: str) -> dict:
    """Get a single JPS match condition AS path association by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_jps_match_condition_as_path(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_jps_actions")
def nautobot_cms_list_jps_actions(
    term_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List JPS actions (read-only), optionally by parent term.

    Args:
        term_id: Filter by parent JPS term UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_jps_actions(client, term_id=term_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_jps_action")
def nautobot_cms_get_jps_action(id: str) -> dict:
    """Get a single JPS action by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_jps_action(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_jps_action_communities")
def nautobot_cms_list_jps_action_communities(
    action_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List JPS action community associations (read-only).

    Args:
        action_id: Filter by parent JPS action UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_jps_action_communities(client, action_id=action_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_jps_action_community")
def nautobot_cms_get_jps_action_community(id: str) -> dict:
    """Get a single JPS action community association by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_jps_action_community(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_jps_action_as_paths")
def nautobot_cms_list_jps_action_as_paths(
    action_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List JPS action AS path associations (read-only).

    Args:
        action_id: Filter by parent JPS action UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_jps_action_as_paths(client, action_id=action_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_jps_action_as_path")
def nautobot_cms_get_jps_action_as_path(id: str) -> dict:
    """Get a single JPS action AS path association by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_jps_action_as_path(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_jps_action_load_balances")
def nautobot_cms_list_jps_action_load_balances(
    action_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List JPS action load balance configurations (read-only).

    Args:
        action_id: Filter by parent JPS action UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_jps_action_load_balances(client, action_id=action_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_jps_action_load_balance")
def nautobot_cms_get_jps_action_load_balance(id: str) -> dict:
    """Get a single JPS action load balance by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_jps_action_load_balance(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_list_jps_action_install_nexthops")
def nautobot_cms_list_jps_action_install_nexthops(
    action_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List JPS action install nexthop configurations (read-only).

    Args:
        action_id: Filter by parent JPS action UUID.
        limit: Max results (default 50, 0 = all).
    """
    try:
        client = get_client()
        result = cms_policies.list_jps_action_install_nexthops(client, action_id=action_id, limit=limit)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_jps_action_install_nexthop")
def nautobot_cms_get_jps_action_install_nexthop(id: str) -> dict:
    """Get a single JPS action install nexthop by UUID."""
    try:
        client = get_client()
        result = cms_policies.get_jps_action_install_nexthop(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# CMS ARP TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_cms_list_arp_entries")
def nautobot_cms_list_arp_entries(
    device: str,
    interface: Optional[str] = None,
    mac_address: Optional[str] = None,
    limit: int = 0,
) -> dict:
    """List ARP entries for a Juniper device.

    Queries the CMS juniper_arp_entries endpoint filtered by device.
    Optionally narrow by interface name/UUID or MAC address.

    Args:
        device: Device name or UUID (required — ARP is always device-scoped).
        interface: Filter by interface name or UUID.
        mac_address: Filter by exact MAC address.
        limit: Max results (0 = all).

    Returns:
        Dict with 'count' and 'results' (list of ARP entry dicts).
    """
    try:
        client = get_client()
        result = cms_arp.list_arp_entries(
            client,
            device=device,
            interface=interface,
            mac_address=mac_address,
            limit=limit,
        )
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_get_arp_entry")
def nautobot_cms_get_arp_entry(id: str) -> dict:
    """Get a single ARP entry by UUID.

    Args:
        id: ARP entry UUID.

    Returns:
        ARP entry dict with interface_id, interface_name, device_name, ip_address,
        mac_address, and hostname.
    """
    try:
        client = get_client()
        result = cms_arp.get_arp_entry(client, id=id)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ===========================================================================
# CMS DRIFT TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_cms_compare_bgp_neighbors")
def nautobot_cms_compare_bgp_neighbors(
    device_name: str,
    live_neighbors: list[dict],
) -> dict:
    """Compare live BGP neighbors against Nautobot CMS BGP model records.

    Accepts pre-fetched BGP neighbor data (e.g., from jmcp 'show bgp summary')
    and compares against Nautobot CMS records. Uses DiffSync for semantic comparison.

    Comparison fields: peer IP (identity), peer AS, local address, group name.
    Volatile fields (session state, prefix counts) are excluded.

    Args:
        device_name: Device hostname in Nautobot.
        live_neighbors: List of dicts, each with: peer_ip (str), peer_as (int),
            local_address (str), group_name (str).

    Returns:
        CMSDriftReport dict with bgp_neighbors section (missing/extra/changed)
        and summary with total drift count.
    """
    try:
        client = get_client()
        from nautobot_mcp.cms.cms_drift import compare_bgp_neighbors
        result = compare_bgp_neighbors(client, device_name, live_neighbors)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


@mcp.tool(name="nautobot_cms_compare_static_routes")
def nautobot_cms_compare_static_routes(
    device_name: str,
    live_routes: list[dict],
) -> dict:
    """Compare live static routes against Nautobot CMS static route records.

    Accepts pre-fetched static route data (e.g., from jmcp 'show route static')
    and compares against Nautobot CMS records. Uses DiffSync for semantic comparison.

    Comparison fields: destination (identity), next-hops, preference, metric,
    routing instance.

    Args:
        device_name: Device hostname in Nautobot.
        live_routes: List of dicts, each with: destination (str),
            nexthops (list[str]), preference (int), metric (int),
            routing_instance (str).

    Returns:
        CMSDriftReport dict with static_routes section (missing/extra/changed)
        and summary with total drift count.
    """
    try:
        client = get_client()
        from nautobot_mcp.cms.cms_drift import compare_static_routes
        result = compare_static_routes(client, device_name, live_routes)
        return result.model_dump()
    except Exception as e:
        handle_error(e)


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()

