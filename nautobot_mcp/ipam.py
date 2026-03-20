"""IPAM CRUD operations: Prefixes, IP Addresses, and VLANs.

All operations support Nautobot v2 Namespace model for prefix/IP uniqueness.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.ipam import DeviceIPEntry, DeviceIPsResponse, IPAddressSummary, PrefixSummary, VLANSummary

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


def list_prefixes(
    client: NautobotClient,
    location: Optional[str] = None,
    tenant: Optional[str] = None,
    namespace: Optional[str] = None,
    vrf: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 0,
    **extra_filters: str,
) -> ListResponse[PrefixSummary]:
    """List prefixes with optional filtering."""
    try:
        filters = {}
        if location:
            filters["location"] = location
        if tenant:
            filters["tenant"] = tenant
        if namespace:
            filters["namespace"] = namespace
        if vrf:
            filters["vrf"] = vrf
        if q:
            filters["q"] = q
        filters.update(extra_filters)

        if filters:
            records = list(client.api.ipam.prefixes.filter(**filters))
        else:
            records = list(client.api.ipam.prefixes.all())

        all_results = [PrefixSummary.from_nautobot(r) for r in records]
        limited_results = all_results[:limit] if limit > 0 else all_results

        return ListResponse(count=len(all_results), results=limited_results)

    except Exception as e:
        client._handle_api_error(e, "list", "Prefix")
        raise


def create_prefix(
    client: NautobotClient,
    prefix: str,
    namespace: str = "Global",
    status: str = "Active",
    **kwargs: str,
) -> PrefixSummary:
    """Create a new prefix. Nautobot v2 requires Namespace for uniqueness."""
    try:
        data = {
            "prefix": prefix,
            "namespace": {"name": namespace},
            "status": status,
        }
        data.update(kwargs)
        record = client.api.ipam.prefixes.create(**data)
        return PrefixSummary.from_nautobot(record)

    except Exception as e:
        client._handle_api_error(e, "create", "Prefix")
        raise


def list_ip_addresses(
    client: NautobotClient,
    device: Optional[str] = None,
    interface: Optional[str] = None,
    prefix: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 0,
    **extra_filters: str,
) -> ListResponse[IPAddressSummary]:
    """List IP addresses with optional filtering.

    When device is provided, uses the M2M ip_address_to_interface table
    to reliably resolve which IPs are assigned to device interfaces,
    since Nautobot's ip_addresses endpoint may not support direct device filtering.
    """
    try:
        if device:
            # Device filter: walk interfaces → M2M → IPs
            iface_records = list(client.api.dcim.interfaces.filter(device=device))
            seen_ip_ids: set[str] = set()
            all_results = []
            for iface in iface_records:
                m2m_records = list(
                    client.api.ipam.ip_address_to_interface.filter(
                        interface=str(iface.id)
                    )
                )
                for m2m in m2m_records:
                    ip_id = str(m2m.ip_address.id)
                    if ip_id not in seen_ip_ids:
                        seen_ip_ids.add(ip_id)
                        ip_record = client.api.ipam.ip_addresses.get(id=ip_id)
                        if ip_record:
                            all_results.append(IPAddressSummary.from_nautobot(ip_record))
        else:
            filters = {}
            if interface:
                filters["interface"] = interface
            if prefix:
                filters["prefix"] = prefix
            if q:
                filters["q"] = q
            filters.update(extra_filters)

            if filters:
                records = list(client.api.ipam.ip_addresses.filter(**filters))
            else:
                records = list(client.api.ipam.ip_addresses.all())

            all_results = [IPAddressSummary.from_nautobot(r) for r in records]

        limited_results = all_results[:limit] if limit > 0 else all_results
        return ListResponse(count=len(all_results), results=limited_results)

    except Exception as e:
        client._handle_api_error(e, "list", "IPAddress")
        raise


def create_ip_address(
    client: NautobotClient,
    address: str,
    namespace: str = "Global",
    status: str = "Active",
    **kwargs: str,
) -> IPAddressSummary:
    """Create a new IP address. Nautobot v2 requires Namespace."""
    try:
        data = {
            "address": address,
            "namespace": {"name": namespace},
            "status": status,
        }
        data.update(kwargs)
        record = client.api.ipam.ip_addresses.create(**data)
        return IPAddressSummary.from_nautobot(record)

    except Exception as e:
        client._handle_api_error(e, "create", "IPAddress")
        raise


def list_vlans(
    client: NautobotClient,
    location: Optional[str] = None,
    tenant: Optional[str] = None,
    vlan_group: Optional[str] = None,
    vid: Optional[int] = None,
    device: Optional[str] = None,
    limit: int = 0,
    **extra_filters: str,
) -> ListResponse[VLANSummary]:
    """List VLANs with optional filtering.

    When device is provided, gets VLANs via device interfaces (untagged_vlan
    and tagged_vlans) rather than a global VLAN list.
    """
    try:
        if device:
            # Device filter: walk interfaces → extract VLAN IDs → fetch each
            iface_records = list(client.api.dcim.interfaces.filter(device=device))
            vlan_ids: set[str] = set()
            for iface in iface_records:
                if hasattr(iface, "untagged_vlan") and iface.untagged_vlan:
                    vlan_ids.add(str(iface.untagged_vlan.id))
                if hasattr(iface, "tagged_vlans") and iface.tagged_vlans:
                    for vlan in iface.tagged_vlans:
                        vlan_ids.add(str(vlan.id) if hasattr(vlan, "id") else str(vlan))

            if not vlan_ids:
                return ListResponse(count=0, results=[])

            all_results = []
            for vlan_id in vlan_ids:
                record = client.api.ipam.vlans.get(id=vlan_id)
                if record:
                    all_results.append(VLANSummary.from_nautobot(record))
        else:
            filters = {}
            if location:
                filters["location"] = location
            if tenant:
                filters["tenant"] = tenant
            if vlan_group:
                filters["vlan_group"] = vlan_group
            if vid is not None:
                filters["vid"] = vid
            filters.update(extra_filters)

            if filters:
                records = list(client.api.ipam.vlans.filter(**filters))
            else:
                records = list(client.api.ipam.vlans.all())

            all_results = [VLANSummary.from_nautobot(r) for r in records]

        limited_results = all_results[:limit] if limit > 0 else all_results
        return ListResponse(count=len(all_results), results=limited_results)

    except Exception as e:
        client._handle_api_error(e, "list", "VLAN")
        raise


def get_device_ips(
    client: NautobotClient,
    device_name: str,
) -> DeviceIPsResponse:
    """Get all IPs assigned to a device's interfaces via the M2M table.

    Strategy:
    1. Get all interfaces for the device
    2. For each interface, fetch ip_address_to_interface M2M records
    3. Collect IP details for each assignment

    Args:
        client: NautobotClient instance.
        device_name: Device name to query.

    Returns:
        DeviceIPsResponse with interface_ips and unlinked_ips.
    """
    try:
        iface_records = list(client.api.dcim.interfaces.filter(device=device_name))

        interface_ips = []
        for iface in iface_records:
            m2m_records = list(
                client.api.ipam.ip_address_to_interface.filter(interface=str(iface.id))
            )
            for m2m in m2m_records:
                ip_record = client.api.ipam.ip_addresses.get(id=str(m2m.ip_address.id))
                if ip_record:
                    status = "Unknown"
                    if hasattr(ip_record, "status") and ip_record.status:
                        status = getattr(ip_record.status, "display", str(ip_record.status))
                    interface_ips.append(
                        DeviceIPEntry(
                            interface_name=iface.name,
                            interface_id=str(iface.id),
                            address=str(ip_record.address),
                            ip_id=str(ip_record.id),
                            status=status,
                        )
                    )

        return DeviceIPsResponse(
            device_name=device_name,
            total_ips=len(interface_ips),
            interface_ips=interface_ips,
            unlinked_ips=[],
        )

    except Exception as e:
        client._handle_api_error(e, "get_device_ips", "IPAddress")
        raise


def create_vlan(
    client: NautobotClient,
    vid: int,
    name: str,
    status: str = "Active",
    **kwargs: str,
) -> VLANSummary:
    """Create a new VLAN."""
    try:
        data = {
            "vid": vid,
            "name": name,
            "status": status,
        }
        data.update(kwargs)
        record = client.api.ipam.vlans.create(**data)
        return VLANSummary.from_nautobot(record)

    except Exception as e:
        client._handle_api_error(e, "create", "VLAN")
        raise
