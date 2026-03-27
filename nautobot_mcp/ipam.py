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
    offset: int = 0,
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

        # Build limit/offset kwargs — only include if > 0 to let pynautobot auto-paginate when not set
        pagination_kwargs = {}
        if limit > 0:
            pagination_kwargs["limit"] = limit
        if offset > 0:
            pagination_kwargs["offset"] = offset

        if filters:
            records = list(client.api.ipam.prefixes.filter(**filters, **pagination_kwargs))
        else:
            records = list(client.api.ipam.prefixes.all(**pagination_kwargs))

        all_results = [PrefixSummary.from_nautobot(r) for r in records]
        # count reflects total matching records; limited_results is the server-returned slice
        return ListResponse(count=len(all_results), results=all_results)

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
    offset: int = 0,
    **extra_filters: str,
) -> ListResponse[IPAddressSummary]:
    """List IP addresses with optional filtering.

    When device is provided, uses the M2M ip_address_to_interface table
    to reliably resolve which IPs are assigned to device interfaces,
    since Nautobot's ip_addresses endpoint may not support direct device filtering.
    Server-side limit/offset are passed to pynautobot to reduce data transfer.
    """
    try:
        if device:
            # Device filter: walk interfaces → M2M → IPs
            # Build pagination kwargs — limit > 0 stops auto-pagination
            iface_kwargs: dict = {"device": device}
            if limit > 0:
                iface_kwargs["limit"] = limit
            iface_records = list(client.api.dcim.interfaces.filter(**iface_kwargs))
            seen_ip_ids: set[str] = set()
            all_results = []
            fetched_count = 0
            for iface in iface_records:
                # Stop if we've hit the limit (avoid fetching IPs for interfaces we don't need)
                if limit > 0 and fetched_count >= limit:
                    break
                # Fetch M2M records for this interface
                m2m_kwargs: dict = {"interface": str(iface.id)}
                if limit > 0:
                    m2m_kwargs["limit"] = limit
                m2m_records = list(client.api.ipam.ip_address_to_interface.filter(**m2m_kwargs))
                for m2m in m2m_records:
                    if limit > 0 and fetched_count >= limit:
                        break
                    ip_id = str(m2m.ip_address.id)
                    if ip_id not in seen_ip_ids:
                        seen_ip_ids.add(ip_id)
                        ip_record = client.api.ipam.ip_addresses.get(id=ip_id)
                        if ip_record:
                            all_results.append(IPAddressSummary.from_nautobot(ip_record))
                            fetched_count += 1
        else:
            filters = {}
            if interface:
                filters["interface"] = interface
            if prefix:
                filters["prefix"] = prefix
            if q:
                filters["q"] = q
            filters.update(extra_filters)

            pagination_kwargs = {}
            if limit > 0:
                pagination_kwargs["limit"] = limit
            if offset > 0:
                pagination_kwargs["offset"] = offset

            if filters:
                records = list(client.api.ipam.ip_addresses.filter(**filters, **pagination_kwargs))
            else:
                records = list(client.api.ipam.ip_addresses.all(**pagination_kwargs))

            all_results = [IPAddressSummary.from_nautobot(r) for r in records]

        return ListResponse(count=len(all_results), results=all_results)

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
    offset: int = 0,
    **extra_filters: str,
) -> ListResponse[VLANSummary]:
    """List VLANs with optional filtering.

    When device is provided, gets VLANs via device interfaces (untagged_vlan
    and tagged_vlans) rather than a global VLAN list.
    """
    try:
        if device:
            # Device filter: walk interfaces → extract VLAN IDs → fetch each
            iface_kwargs: dict = {"device": device}
            if limit > 0:
                iface_kwargs["limit"] = limit
            iface_records = list(client.api.dcim.interfaces.filter(**iface_kwargs))
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

            pagination_kwargs = {}
            if limit > 0:
                pagination_kwargs["limit"] = limit
            if offset > 0:
                pagination_kwargs["offset"] = offset

            if filters:
                records = list(client.api.ipam.vlans.filter(**filters, **pagination_kwargs))
            else:
                records = list(client.api.ipam.vlans.all(**pagination_kwargs))

            all_results = [VLANSummary.from_nautobot(r) for r in records]

        return ListResponse(count=len(all_results), results=all_results)

    except Exception as e:
        client._handle_api_error(e, "list", "VLAN")
        raise


def get_device_ips(
    client: NautobotClient,
    device_name: str,
    limit: int = 0,
) -> DeviceIPsResponse:
    """Get all IPs assigned to a device's interfaces via the M2M table.

    Strategy:
    1. Get all interfaces for the device (server-side limited if limit > 0)
    2. For each interface, fetch ip_address_to_interface M2M records
    3. Collect IP details for each assignment

    Args:
        client: NautobotClient instance.
        device_name: Device name to query.
        limit: Server-side limit on interfaces fetched (0 = no limit).

    Returns:
        DeviceIPsResponse with interface_ips and unlinked_ips.
    """
    try:
        iface_kwargs: dict = {"device": device_name}
        if limit > 0:
            iface_kwargs["limit"] = limit
        iface_records = list(client.api.dcim.interfaces.filter(**iface_kwargs))

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
