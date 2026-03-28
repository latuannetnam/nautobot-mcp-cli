"""Device CRUD operations using the Nautobot API client.

Provides list/get/create/update/delete operations for Devices,
returning curated DeviceSummary pydantic models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

from nautobot_mcp.exceptions import NautobotNotFoundError
from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.device import DeviceSummary, DeviceStatsResponse, DeviceInventoryResponse

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
    offset: int = 0,
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
        offset: Skip N results for pagination.
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

        pagination_kwargs = {}
        if limit > 0:
            pagination_kwargs["limit"] = limit
        if offset > 0:
            pagination_kwargs["offset"] = offset

        if filters:
            records = list(client.api.dcim.devices.filter(**filters, **pagination_kwargs))
        else:
            records = list(client.api.dcim.devices.all(**pagination_kwargs))

        all_results = [DeviceSummary.from_nautobot(r) for r in records]
        return ListResponse(count=len(all_results), results=all_results)

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
) -> DeviceStatsResponse:
    """Get device metadata + counts — fast, 4 API calls max.

    Does NOT fetch interface/IP/VLAN detail. Use get_device_inventory() for
    full inventory with pagination.

    Args:
        client: NautobotClient instance.
        name: Device hostname.

    Returns:
        DeviceStatsResponse with device info and 5 counts.
    """
    # Step 1: Get device info (1 API call)
    device = get_device(client, name=name)

    # Step 2: Interface count — .count(device=name) hits /count/?device=... (OK)
    interface_count = client.api.dcim.interfaces.count(device=name)

    # Step 3: IP count — .count(device_id=uuid) hits /count/?device_id=... (OK)
    device_uuid = device.id
    ip_count = client.api.ipam.ip_addresses.count(device_id=device_uuid)

    # Step 4: VLAN count — .count(device=...) is NOT supported on /ipam/vlans/count/.
    # VLANs don't track a device FK. Use the device's location as the closest proxy.
    device_location = device.location.name if device.location else None
    vlan_count = client.api.ipam.vlans.count(location=device_location) if device_location else 0

    return DeviceStatsResponse(
        device=device,
        interface_count=interface_count,
        ip_count=ip_count,
        vlan_count=vlan_count,
    )


def get_device_inventory(
    client: NautobotClient,
    name: Optional[str] = None,
    device: Optional[str] = None,
    detail: Literal["interfaces", "ips", "vlans", "all"] = "interfaces",
    limit: int = 50,
    offset: int = 0,
) -> DeviceInventoryResponse:
    """Get full device inventory with pagination.

    Uses bulk fetches for IPs and VLANs — no N+1.

    Args:
        client: NautobotClient instance.
        name: Device hostname (CLI style).
        device: Device hostname (workflow style alias of `name`).
        detail: Which data to fetch: 'interfaces', 'ips', 'vlans', or 'all'.
        limit: Max results per section (0 = all).
        offset: Skip N results for pagination.

    Returns:
        DeviceInventoryResponse with paginated device data.
    """
    from nautobot_mcp import interfaces as iface_mod  # noqa: PLC0415
    from nautobot_mcp import ipam as ipam_mod  # noqa: PLC0415

    device_name = device or name
    if not device_name:
        raise ValueError("Either 'name' or 'device' must be provided")

    if detail not in {"interfaces", "ips", "vlans", "all"}:
        raise ValueError("detail must be one of: interfaces, ips, vlans, all")
    if limit < 0 or offset < 0:
        raise ValueError("limit and offset must be >= 0")

    # Always get device info
    device_obj = get_device(client, name=device_name)

    # Only compute totals for the data being fetched — avoids O(N) API calls
    # when user only asked for one section (e.g. interfaces only).
    total_interfaces = 0
    total_ips = 0
    total_vlans = 0

    if detail in ("interfaces", "all"):
        total_interfaces = client.api.dcim.interfaces.count(device=device_name)

    if detail in ("ips", "all"):
        total_ips = ipam_mod.get_device_ips(client, device_name=device_name, limit=0, offset=0).total_ips

    if detail in ("vlans", "all"):
        # VLAN /count/ doesn't support device filter — use location as proxy
        device_location = device_obj.location.name if device_obj.location else None
        total_vlans = client.api.ipam.vlans.count(location=device_location) if device_location else 0

    interfaces_data: list | None = None
    interface_ips_data: list | None = None
    vlans_data: list | None = None

    if detail in ("interfaces", "all"):
        interfaces_data = iface_mod.list_interfaces(
            client, device_name=device_name, limit=limit, offset=offset
        ).results

    if detail in ("ips", "all"):
        interface_ips_data = ipam_mod.get_device_ips(
            client, device_name=device_name, limit=limit, offset=offset
        ).interface_ips

    if detail in ("vlans", "all"):
        vlans_data = ipam_mod.list_vlans(
            client, device=device_name, limit=limit, offset=offset
        ).results

    has_more = (
        (detail in ("interfaces", "all") and offset + (len(interfaces_data) if interfaces_data else 0) < total_interfaces)
        or (detail in ("ips", "all") and offset + (len(interface_ips_data) if interface_ips_data else 0) < total_ips)
        or (detail in ("vlans", "all") and offset + (len(vlans_data) if vlans_data else 0) < total_vlans)
    )

    return DeviceInventoryResponse(
        device=device_obj,
        interfaces=interfaces_data,
        interface_ips=interface_ips_data,
        vlans=vlans_data,
        total_interfaces=total_interfaces,
        total_ips=total_ips,
        total_vlans=total_vlans,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )

