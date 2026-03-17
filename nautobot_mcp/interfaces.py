"""Interface operations using the Nautobot API client.

Provides list/get/create/update operations for Interfaces and
IP address assignment via Nautobot v2 M2M through table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nautobot_mcp.exceptions import NautobotNotFoundError
from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.interface import InterfaceSummary

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


def list_interfaces(
    client: NautobotClient,
    device_name: Optional[str] = None,
    device_id: Optional[str] = None,
    limit: int = 0,
    **extra_filters: str,
) -> ListResponse[InterfaceSummary]:
    """List interfaces with optional device filtering.

    Args:
        client: NautobotClient instance.
        device_name: Filter by parent device name.
        device_id: Filter by parent device ID.
        limit: Max results to return. 0 = all.
        **extra_filters: Additional filter parameters.

    Returns:
        ListResponse with count and InterfaceSummary results.
    """
    try:
        filters = {}
        if device_name:
            filters["device"] = device_name
        if device_id:
            filters["device_id"] = device_id
        filters.update(extra_filters)

        if filters:
            records = list(client.api.dcim.interfaces.filter(**filters))
        else:
            records = list(client.api.dcim.interfaces.all())

        all_results = [InterfaceSummary.from_nautobot(r) for r in records]

        if limit > 0:
            limited_results = all_results[:limit]
        else:
            limited_results = all_results

        return ListResponse(count=len(all_results), results=limited_results)

    except Exception as e:
        client._handle_api_error(e, "list", "Interface")
        raise


def get_interface(
    client: NautobotClient,
    id: Optional[str] = None,
    device_name: Optional[str] = None,
    name: Optional[str] = None,
) -> InterfaceSummary:
    """Get a single interface.

    Args:
        client: NautobotClient instance.
        id: Interface UUID.
        device_name: Parent device name (used with name).
        name: Interface name (used with device_name).

    Returns:
        InterfaceSummary for the found interface.

    Raises:
        NautobotNotFoundError: If interface not found.
    """
    try:
        if id:
            record = client.api.dcim.interfaces.get(id=id)
        elif device_name and name:
            record = client.api.dcim.interfaces.get(device=device_name, name=name)
        else:
            raise ValueError("Either 'id' or both 'device_name' and 'name' must be provided")

        if record is None:
            identifier = id or f"{device_name}/{name}"
            raise NautobotNotFoundError(
                message=f"Interface '{identifier}' not found",
                hint="Check the interface name/ID, use list_interfaces to see available interfaces",
            )

        return InterfaceSummary.from_nautobot(record)

    except NautobotNotFoundError:
        raise
    except ValueError:
        raise
    except Exception as e:
        client._handle_api_error(e, "get", "Interface")
        raise


def create_interface(
    client: NautobotClient,
    device: str,
    name: str,
    type: str = "1000base-t",
    **kwargs: str,
) -> InterfaceSummary:
    """Create a new interface on a device.

    Args:
        client: NautobotClient instance.
        device: Parent device name.
        name: Interface name.
        type: Interface type. Default: "1000base-t".
        **kwargs: Additional interface fields.

    Returns:
        InterfaceSummary for the created interface.
    """
    try:
        data = {
            "device": {"name": device},
            "name": name,
            "type": type,
            "status": kwargs.pop("status", "Active"),
        }
        data.update(kwargs)
        record = client.api.dcim.interfaces.create(**data)
        return InterfaceSummary.from_nautobot(record)

    except Exception as e:
        client._handle_api_error(e, "create", "Interface")
        raise


def update_interface(
    client: NautobotClient,
    id: str,
    **updates: str,
) -> InterfaceSummary:
    """Update an existing interface.

    Args:
        client: NautobotClient instance.
        id: Interface UUID.
        **updates: Fields to update.

    Returns:
        InterfaceSummary for the updated interface.
    """
    try:
        record = client.api.dcim.interfaces.get(id=id)
        if record is None:
            raise NautobotNotFoundError(
                message=f"Interface '{id}' not found for update",
            )

        for key, value in updates.items():
            setattr(record, key, value)
        record.save()

        return InterfaceSummary.from_nautobot(record)

    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "update", "Interface")
        raise


def assign_ip_to_interface(
    client: NautobotClient,
    interface_id: str,
    ip_address_id: str,
) -> dict:
    """Assign an IP address to an interface via Nautobot v2 M2M through table.

    Uses the /api/ipam/ip-address-to-interface/ endpoint to create
    the IPAddressToInterface association.

    Args:
        client: NautobotClient instance.
        interface_id: UUID of the interface.
        ip_address_id: UUID of the IP address.

    Returns:
        Dict with the created association info.
    """
    try:
        result = client.api.ipam.ip_address_to_interface.create(
            interface=interface_id,
            ip_address=ip_address_id,
        )
        return {
            "id": str(result.id),
            "interface": interface_id,
            "ip_address": ip_address_id,
            "status": "assigned",
        }

    except Exception as e:
        client._handle_api_error(e, "assign_ip", "IPAddressToInterface")
        raise
