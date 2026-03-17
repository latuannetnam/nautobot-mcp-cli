"""IPAM CRUD operations: Prefixes, IP Addresses, and VLANs.

All operations support Nautobot v2 Namespace model for prefix/IP uniqueness.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.ipam import IPAddressSummary, PrefixSummary, VLANSummary

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
    """List IP addresses with optional filtering."""
    try:
        filters = {}
        if device:
            filters["device"] = device
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
    limit: int = 0,
    **extra_filters: str,
) -> ListResponse[VLANSummary]:
    """List VLANs with optional filtering."""
    try:
        filters = {}
        if location:
            filters["location"] = location
        if tenant:
            filters["tenant"] = tenant
        if vlan_group:
            filters["vlan_group"] = vlan_group
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
