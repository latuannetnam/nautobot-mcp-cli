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
            # Use direct HTTP to bypass pynautobot auto-pagination bug
            params: dict = {"device": device}
            if limit > 0:
                params["limit"] = limit
            resp = client.api.http_session.get(
                f"{client._profile.url}/api/dcim/interfaces/",
                params=params,
            )
            if not resp.ok:
                resp.raise_for_status()
            iface_data = resp.json()
            iface_records = [
                client.api.dcim.interfaces.return_obj(r, client.api, client.api.dcim.interfaces)
                for r in iface_data.get("results", [])
            ]
            seen_ip_ids: set[str] = set()
            all_results = []
            fetched_count = 0
            for iface in iface_records:
                # Stop if we've hit the limit (avoid fetching IPs for interfaces we don't need)
                if limit > 0 and fetched_count >= limit:
                    break
                # Fetch M2M records for this interface — also use direct HTTP
                m2m_resp = client.api.http_session.get(
                    f"{client._profile.url}/api/ipam/ip_address_to_interface/",
                    params={"interface": str(iface.id), **( {"limit": limit} if limit > 0 else {} )},
                )
                if not m2m_resp.ok:
                    m2m_resp.raise_for_status()
                m2m_data = m2m_resp.json()
                m2m_records = [
                    client.api.ipam.ip_address_to_interface.return_obj(r, client.api, client.api.ipam.ip_address_to_interface)
                    for r in m2m_data.get("results", [])
                ]
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

            if limit > 0 or offset > 0:
                # Bypass pynautobot auto-pagination: use direct http_session.get()
                params = {**filters, **pagination_kwargs}
                resp = client.api.http_session.get(
                    f"{client._profile.url}/api/ipam/ip_addresses/",
                    params=params,
                )
                if not resp.ok:
                    resp.raise_for_status()
                data = resp.json()
                records = [
                    client.api.ipam.ip_addresses.return_obj(r, client.api, client.api.ipam.ip_addresses)
                    for r in data.get("results", [])
                ]
            elif filters:
                records = list(client.api.ipam.ip_addresses.filter(**filters))
            else:
                records = list(client.api.ipam.ip_addresses.all())

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
            # Device filter: collect all VLAN IDs from interfaces (must fetch all for accuracy)
            # Use direct HTTP to bypass pynautobot auto-pagination bug
            resp = client.api.http_session.get(
                f"{client._profile.url}/api/dcim/interfaces/",
                params={"device": device},
            )
            if not resp.ok:
                resp.raise_for_status()
            iface_data = resp.json()
            # pynautobot Records from raw dicts: Record(raw_dict, api, endpoint)
            iface_records = [
                client.api.dcim.interfaces.return_obj(r, client.api, client.api.dcim.interfaces)
                for r in iface_data.get("results", [])
            ]
            vlan_ids: set[str] = set()
            for iface in iface_records:
                if hasattr(iface, "untagged_vlan") and iface.untagged_vlan:
                    vlan_ids.add(str(iface.untagged_vlan.id))
                if hasattr(iface, "tagged_vlans") and iface.tagged_vlans:
                    for vlan in iface.tagged_vlans:
                        vlan_ids.add(str(vlan.id) if hasattr(vlan, "id") else str(vlan))

            if not vlan_ids:
                return ListResponse(count=0, results=[])

            # Bulk fetch VLANs by ID — O(1) API calls instead of N
            from nautobot_mcp.utils import chunked
            vlan_ids_list = list(vlan_ids)
            total_count = len(vlan_ids_list)
            # Apply offset/limit at result level
            paginated_ids = vlan_ids_list[offset:offset + limit] if limit > 0 else vlan_ids_list
            all_results: list[VLANSummary] = []
            for chunk in chunked(paginated_ids, 500):
                for record in client.api.ipam.vlans.filter(id__in=chunk):
                    all_results.append(VLANSummary.from_nautobot(record))
            return ListResponse(count=total_count, results=all_results)
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

            if limit > 0 or offset > 0:
                # Bypass pynautobot auto-pagination: use direct http_session.get()
                params = {**filters, **pagination_kwargs}
                resp = client.api.http_session.get(
                    f"{client._profile.url}/api/ipam/vlans/",
                    params=params,
                )
                if not resp.ok:
                    resp.raise_for_status()
                data = resp.json()
                records = [
                    client.api.ipam.vlans.return_obj(r, client.api, client.api.ipam.vlans)
                    for r in data.get("results", [])
                ]
            elif filters:
                records = list(client.api.ipam.vlans.filter(**filters))
            else:
                records = list(client.api.ipam.vlans.all())

            all_results = [VLANSummary.from_nautobot(r) for r in records]

        return ListResponse(count=len(all_results), results=all_results)

    except Exception as e:
        client._handle_api_error(e, "list", "VLAN")
        raise


def get_device_ips(
    client: NautobotClient,
    device_name: str,
    limit: int = 0,
    offset: int = 0,
) -> DeviceIPsResponse:
    """Get all IPs assigned to a device's interfaces via the M2M table.

    Bulk strategy — O(3) API calls regardless of interface count:
    1. Collect all interface IDs for the device
    2. Bulk fetch all M2M records in one call (chunked if many interfaces)
    3. Bulk fetch all IP details in one call (chunked)

    Args:
        client: NautobotClient instance.
        device_name: Device name to query.
        limit: Max total entries to return (0 = all).
        offset: Skip N entries for pagination.

    Returns:
        DeviceIPsResponse with interface_ips and unlinked_ips.
    """
    from nautobot_mcp.utils import chunked

    try:
        # Pass 1: collect all interface IDs
        iface_records = list(client.api.dcim.interfaces.filter(device=device_name))
        iface_ids = [str(i.id) for i in iface_records]
        iface_map = {str(i.id): i.name for i in iface_records}

        if not iface_ids:
            return DeviceIPsResponse(
                device_name=device_name,
                total_ips=0,
                interface_ips=[],
                unlinked_ips=[],
            )

        # Pass 2: bulk M2M — try all IDs at once, chunk if too many
        CHUNK = 500
        m2m_records: list = []
        for chunk in chunked(iface_ids, CHUNK):
            chunk_records = list(
                client.api.ipam.ip_address_to_interface.filter(interface=chunk)
            )
            m2m_records.extend(chunk_records)

        # Collect all IP IDs from M2M results
        ip_ids = list({str(m.ip_address.id) for m in m2m_records})

        # Pass 3: bulk IP lookup — chunk if many IDs
        ip_map: dict = {}
        for chunk in chunked(ip_ids, CHUNK):
            for ip in client.api.ipam.ip_addresses.filter(id__in=chunk):
                ip_map[str(ip.id)] = ip

        # Build entries using O(1) lookups
        all_entries: list[DeviceIPEntry] = []
        for m2m in m2m_records:
            ip_id = str(m2m.ip_address.id)
            ip_record = ip_map.get(ip_id)
            if not ip_record:
                continue
            status = "Unknown"
            if hasattr(ip_record, "status") and ip_record.status:
                status = getattr(ip_record.status, "display", str(ip_record.status))
            all_entries.append(
                DeviceIPEntry(
                    interface_name=iface_map.get(str(m2m.interface.id), str(m2m.interface.id)),
                    interface_id=str(m2m.interface.id),
                    address=str(ip_record.address),
                    ip_id=ip_id,
                    status=status,
                )
            )

        total_ips = len(all_entries)
        # Apply offset/limit at the M2M result level
        paginated = all_entries[offset:offset + limit] if limit > 0 else all_entries[offset:]

        return DeviceIPsResponse(
            device_name=device_name,
            total_ips=total_ips,
            interface_ips=paginated,
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
