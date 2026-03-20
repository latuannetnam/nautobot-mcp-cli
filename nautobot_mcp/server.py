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
from nautobot_mcp.parsers import ParserRegistry

mcp = FastMCP("Nautobot MCP Server")

# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

_client: NautobotClient | None = None


def get_client() -> NautobotClient:
    """Return a lazily-initialized NautobotClient singleton."""
    global _client
    if _client is None:
        settings = NautobotSettings()
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


# ===========================================================================
# INTERFACE TOOLS
# ===========================================================================


@mcp.tool(name="nautobot_list_interfaces")
def nautobot_list_interfaces(
    device: Optional[str] = None,
    device_id: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List interfaces with optional device filtering.

    Args:
        device: Filter by parent device name.
        device_id: Filter by parent device UUID.
        limit: Max results (default 50, 0 = all).

    Returns:
        Dict with 'count' and 'results' (list of interface dicts).
    """
    try:
        client = get_client()
        result = interfaces.list_interfaces(
            client, device_name=device, device_id=device_id, limit=limit,
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


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
