"""CMS plugin client helpers shared across all CMS domain modules.

Provides device UUID resolution, endpoint registry, and common
query patterns for netnam-cms-core plugin operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nautobot_mcp.exceptions import NautobotNotFoundError
from nautobot_mcp.models.base import ListResponse

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


# Registry of all CMS endpoint names (pynautobot underscore style)
# mapped to human-readable model names for error messages
CMS_ENDPOINTS = {
    # Routing
    "juniper_static_routes": "JuniperStaticRoute",
    "juniper_static_route_nexthops": "JuniperStaticRouteNexthop",
    "juniper_static_route_qualified_nexthops": "JuniperStaticRouteQualifiedNexthop",
    "juniper_bgp_groups": "JuniperBGPGroup",
    "juniper_bgp_neighbors": "JuniperBGPNeighbor",
    "juniper_bgp_address_families": "JuniperBGPAddressFamily",
    "juniper_bgp_policy_associations": "JuniperBGPPolicyAssociation",
    "juniper_bgp_received_routes": "JuniperBGPReceivedRoute",
    # Interfaces
    "juniper_interface_units": "JuniperInterfaceUnit",
    "juniper_interface_families": "JuniperInterfaceFamily",
    "juniper_interface_family_filters": "JuniperInterfaceFamilyFilter",
    "juniper_interface_family_policers": "JuniperInterfaceFamilyPolicer",
    "juniper_interface_vrrp_groups": "JuniperInterfaceVRRPGroup",
    "vrrp_track_routes": "VRRPTrackRoute",
    "vrrp_track_interfaces": "VRRPTrackInterface",
    # Firewalls
    "juniper_firewall_filters": "JuniperFirewallFilter",
    "juniper_firewall_terms": "JuniperFirewallTerm",
    "juniper_firewall_match_conditions": "JuniperFirewallFilterMatchCondition",
    "juniper_firewall_actions": "JuniperFirewallFilterAction",
    "juniper_firewall_policers": "JuniperFirewallPolicer",
    "juniper_firewall_policer_actions": "JuniperFirewallPolicerAction",
    "juniper_firewall_match_condition_prefix_lists": "JuniperFirewallMatchConditionToPrefixList",
    # Policies
    "juniper_policy_statements": "JuniperPolicyStatement",
    "jps_terms": "JPSTerm",
    "jps_match_conditions": "JPSMatchCondition",
    "jps_match_condition_route_filters": "JPSMatchConditionRouteFilter",
    "jps_match_condition_prefix_lists": "JPSMatchConditionPrefixList",
    "jps_match_condition_communities": "JPSMatchConditionCommunity",
    "jps_match_condition_as_paths": "JPSMatchConditionAsPath",
    "jps_actions": "JPSAction",
    "jps_action_communities": "JPSActionCommunity",
    "jps_action_as_paths": "JPSActionAsPath",
    "jps_action_load_balances": "JPSActionLoadBalance",
    "jps_action_install_nexthops": "JPSActionInstallNexthop",
    "juniper_policy_as_paths": "JuniperPolicyAsPath",
    "juniper_policy_communities": "JuniperPolicyCommunity",
    "juniper_policy_prefix_lists": "JuniperPolicyPrefixList",
    "juniper_policy_prefixes": "JuniperPolicyPrefix",
    # ARP
    "juniper_arp_entries": "JuniperArpEntry",
}


def resolve_device_id(
    client: NautobotClient,
    device_name_or_id: str,
) -> str:
    """Resolve a device name or ID to its UUID.

    Accepts either a UUID string or a device name. If a name is given,
    looks up the device in Nautobot and returns its UUID.

    Args:
        client: NautobotClient instance.
        device_name_or_id: Device name or UUID string.

    Returns:
        Device UUID string.

    Raises:
        NautobotNotFoundError: If device name cannot be resolved.
    """
    # If it looks like a UUID (contains hyphens and is 36 chars), use directly
    if len(device_name_or_id) == 36 and device_name_or_id.count("-") == 4:
        return device_name_or_id

    # Otherwise look up by name
    try:
        device = client.api.dcim.devices.get(name=device_name_or_id)
        if device is None:
            raise NautobotNotFoundError(
                message=f"Device '{device_name_or_id}' not found",
                hint="Check the device name or use list_devices to see available devices",
            )
        return str(device.id)
    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "resolve_device_id", "Device")
        raise


def get_cms_endpoint(client: NautobotClient, endpoint_name: str):
    """Get a CMS plugin endpoint accessor by name.

    Args:
        client: NautobotClient instance.
        endpoint_name: Endpoint name in underscore format (e.g., 'juniper_static_routes').

    Returns:
        pynautobot endpoint accessor.

    Raises:
        ValueError: If endpoint_name is not in the CMS registry.
    """
    if endpoint_name not in CMS_ENDPOINTS:
        raise ValueError(
            f"Unknown CMS endpoint: {endpoint_name}. "
            f"Valid endpoints: {', '.join(sorted(CMS_ENDPOINTS.keys()))}"
        )
    return getattr(client.cms, endpoint_name)


def cms_list(client, endpoint_name, model_cls, limit=0, **filters):
    """Generic CMS list operation.

    Args:
        client: NautobotClient instance.
        endpoint_name: CMS endpoint name (underscore format).
        model_cls: Pydantic model class with from_nautobot() classmethod.
        limit: Max results. 0 = all.
        **filters: Query filters to pass to pynautobot.

    Returns:
        ListResponse[model_cls] with count and results.
    """
    model_name = CMS_ENDPOINTS.get(endpoint_name, endpoint_name)
    try:
        endpoint = get_cms_endpoint(client, endpoint_name)
        if filters:
            records = list(endpoint.filter(**filters))
        else:
            records = list(endpoint.all())

        all_results = [model_cls.from_nautobot(r) for r in records]

        if limit > 0:
            limited = all_results[:limit]
        else:
            limited = all_results

        return ListResponse(count=len(all_results), results=limited)
    except Exception as e:
        client._handle_api_error(e, "list", model_name)
        raise


def cms_get(client, endpoint_name, model_cls, id=None, **filters):
    """Generic CMS get-single-object operation.

    Args:
        client: NautobotClient instance.
        endpoint_name: CMS endpoint name (underscore format).
        model_cls: Pydantic model class with from_nautobot() classmethod.
        id: Object UUID (preferred).
        **filters: Additional filters for .get() lookup.

    Returns:
        model_cls instance.

    Raises:
        NautobotNotFoundError: If object not found.
    """
    model_name = CMS_ENDPOINTS.get(endpoint_name, endpoint_name)
    try:
        endpoint = get_cms_endpoint(client, endpoint_name)
        lookup = {"id": id} if id else filters
        record = endpoint.get(**lookup)

        if record is None:
            identifier = id or str(filters)
            raise NautobotNotFoundError(
                message=f"{model_name} '{identifier}' not found",
                hint=f"Verify the {model_name} exists in Nautobot CMS",
            )
        return model_cls.from_nautobot(record)
    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "get", model_name)
        raise


def cms_create(client, endpoint_name, model_cls, **data):
    """Generic CMS create operation.

    Args:
        client: NautobotClient instance.
        endpoint_name: CMS endpoint name (underscore format).
        model_cls: Pydantic model class with from_nautobot() classmethod.
        **data: Fields to create.

    Returns:
        model_cls instance of the created object.
    """
    model_name = CMS_ENDPOINTS.get(endpoint_name, endpoint_name)
    try:
        endpoint = get_cms_endpoint(client, endpoint_name)
        record = endpoint.create(**data)
        return model_cls.from_nautobot(record)
    except Exception as e:
        client._handle_api_error(e, "create", model_name)
        raise


def cms_update(client, endpoint_name, model_cls, id, **updates):
    """Generic CMS update operation.

    Args:
        client: NautobotClient instance.
        endpoint_name: CMS endpoint name (underscore format).
        model_cls: Pydantic model class with from_nautobot() classmethod.
        id: Object UUID.
        **updates: Fields to update.

    Returns:
        model_cls instance of the updated object.
    """
    model_name = CMS_ENDPOINTS.get(endpoint_name, endpoint_name)
    try:
        endpoint = get_cms_endpoint(client, endpoint_name)
        record = endpoint.get(id=id)
        if record is None:
            raise NautobotNotFoundError(
                message=f"{model_name} '{id}' not found for update",
                hint=f"Verify the {model_name} ID exists",
            )
        for key, value in updates.items():
            setattr(record, key, value)
        record.save()
        return model_cls.from_nautobot(record)
    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "update", model_name)
        raise


def cms_delete(client, endpoint_name, id):
    """Generic CMS delete operation.

    Args:
        client: NautobotClient instance.
        endpoint_name: CMS endpoint name (underscore format).
        id: Object UUID.

    Returns:
        dict with success status and message.
    """
    model_name = CMS_ENDPOINTS.get(endpoint_name, endpoint_name)
    try:
        endpoint = get_cms_endpoint(client, endpoint_name)
        record = endpoint.get(id=id)
        if record is None:
            raise NautobotNotFoundError(
                message=f"{model_name} '{id}' not found for deletion",
            )
        record.delete()
        return {"success": True, "message": f"{model_name} {id} deleted"}
    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "delete", model_name)
        raise
