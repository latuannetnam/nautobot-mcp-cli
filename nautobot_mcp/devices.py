"""Device CRUD operations using the Nautobot API client.

Provides list/get/create/update/delete operations for Devices,
returning curated DeviceSummary pydantic models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nautobot_mcp.exceptions import NautobotNotFoundError
from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.device import DeviceSummary, DeviceSummaryResponse

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


def list_devices(
    client: NautobotClient,
    location: Optional[str] = None,
    tenant: Optional[str] = None,
    role: Optional[str] = None,
    platform: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 0,
    **extra_filters: str,
) -> ListResponse[DeviceSummary]:
    """List devices with optional filtering.

    Args:
        client: NautobotClient instance.
        location: Filter by location name.
        tenant: Filter by tenant name.
        role: Filter by device role name.
        platform: Filter by platform name.
        q: Full-text search query.
        limit: Max results to return. 0 = all.
        **extra_filters: Additional pynautobot filter parameters.

    Returns:
        ListResponse with count and DeviceSummary results.
    """
    try:
        filters = {}
        if location:
            filters["location"] = location
        if tenant:
            filters["tenant"] = tenant
        if role:
            filters["role"] = role
        if platform:
            filters["platform"] = platform
        if q:
            filters["q"] = q
        filters.update(extra_filters)

        if filters:
            records = list(client.api.dcim.devices.filter(**filters))
        else:
            records = list(client.api.dcim.devices.all())

        all_results = [DeviceSummary.from_nautobot(r) for r in records]

        if limit > 0:
            limited_results = all_results[:limit]
        else:
            limited_results = all_results

        return ListResponse(count=len(all_results), results=limited_results)

    except Exception as e:
        client._handle_api_error(e, "list", "Device")
        raise  # unreachable, _handle_api_error always raises


def get_device(
    client: NautobotClient,
    name: Optional[str] = None,
    id: Optional[str] = None,
) -> DeviceSummary:
    """Get a single device by name or ID.

    Args:
        client: NautobotClient instance.
        name: Device name to look up.
        id: Device UUID to look up.

    Returns:
        DeviceSummary for the found device.

    Raises:
        NautobotNotFoundError: If device not found.
        ValueError: If neither name nor id provided.
    """
    if not name and not id:
        raise ValueError("Either 'name' or 'id' must be provided")

    try:
        if id:
            record = client.api.dcim.devices.get(id=id)
        else:
            record = client.api.dcim.devices.get(name=name)

        if record is None:
            identifier = name or id
            raise NautobotNotFoundError(
                message=f"Device '{identifier}' not found",
                hint="Check the device name or ID, use list_devices to see available devices",
            )

        return DeviceSummary.from_nautobot(record)

    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "get", "Device")
        raise


def create_device(
    client: NautobotClient,
    name: str,
    device_type: str,
    location: str,
    role: str,
    status: str = "Active",
    **kwargs: str,
) -> DeviceSummary:
    """Create a new device in Nautobot.

    Args:
        client: NautobotClient instance.
        name: Device hostname.
        device_type: Device type name (must exist in Nautobot).
        location: Location name (must exist in Nautobot).
        role: Device role name (must exist in Nautobot).
        status: Device status. Default: "Active".
        **kwargs: Additional device fields.

    Returns:
        DeviceSummary for the created device.
    """
    try:
        data = {
            "name": name,
            "device_type": {"name": device_type},
            "location": {"name": location},
            "role": {"name": role},
            "status": status,
        }
        data.update(kwargs)
        record = client.api.dcim.devices.create(**data)
        return DeviceSummary.from_nautobot(record)

    except Exception as e:
        client._handle_api_error(e, "create", "Device")
        raise


def update_device(
    client: NautobotClient,
    id: str,
    **updates: str,
) -> DeviceSummary:
    """Update an existing device.

    Args:
        client: NautobotClient instance.
        id: Device UUID to update.
        **updates: Fields to update.

    Returns:
        DeviceSummary for the updated device.
    """
    try:
        record = client.api.dcim.devices.get(id=id)
        if record is None:
            raise NautobotNotFoundError(
                message=f"Device '{id}' not found for update",
                hint="Verify the device ID exists",
            )

        for key, value in updates.items():
            setattr(record, key, value)
        record.save()

        return DeviceSummary.from_nautobot(record)

    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "update", "Device")
        raise


def delete_device(
    client: NautobotClient,
    id: str,
) -> bool:
    """Delete a device from Nautobot.

    Args:
        client: NautobotClient instance.
        id: Device UUID to delete.

    Returns:
        True if deletion was successful.
    """
    try:
        record = client.api.dcim.devices.get(id=id)
        if record is None:
            raise NautobotNotFoundError(
                message=f"Device '{id}' not found for deletion",
            )
        record.delete()
        return True

    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "delete", "Device")
        raise


def get_device_summary(
    client: NautobotClient,
    name: str,
) -> DeviceSummaryResponse:
    """Get complete device overview: info + interfaces + IPs + VLANs + counts.

    Composes get_device, list_interfaces, get_device_ips, and list_vlans
    into a single response. Uses existing functions — no duplicate API logic.

    Args:
        client: NautobotClient instance.
        name: Device hostname.

    Returns:
        DeviceSummaryResponse with all device data and counts.
    """
    from nautobot_mcp import interfaces as iface_mod  # noqa: PLC0415
    from nautobot_mcp import ipam as ipam_mod  # noqa: PLC0415

    # Step 1: Get device info
    device = get_device(client, name=name)

    # Step 2: Get interfaces
    iface_result = iface_mod.list_interfaces(client, device_name=name, limit=0)
    iface_list = iface_result.results

    # Step 3: Get IPs via M2M
    ip_result = ipam_mod.get_device_ips(client, device_name=name)

    # Step 4: Get VLANs via interfaces
    vlan_result = ipam_mod.list_vlans(client, device=name, limit=0)

    # Step 5: Compute counts
    enabled_count = sum(1 for i in iface_list if i.enabled)
    disabled_count = len(iface_list) - enabled_count

    return DeviceSummaryResponse(
        device=device,
        interfaces=iface_list,
        interface_ips=ip_result.interface_ips,
        vlans=vlan_result.results,
        interface_count=len(iface_list),
        ip_count=ip_result.total_ips,
        vlan_count=vlan_result.count,
        enabled_count=enabled_count,
        disabled_count=disabled_count,
    )
