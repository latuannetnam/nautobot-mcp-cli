"""CRUD functions for CMS ARP plugin (JuniperArpEntry).

Provides read-only list and get operations for ARP table entries.
ARP entries are accessed via the juniper_arp_entries CMS endpoint.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nautobot_mcp.cms.client import cms_get, cms_list, resolve_device_id
from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.cms.arp import ArpEntrySummary

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


def list_arp_entries(
    client: "NautobotClient",
    device: Optional[str] = None,
    interface: Optional[str] = None,
    mac_address: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[ArpEntrySummary]:
    """List ARP entries, optionally filtered by device, interface, or MAC address.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID to filter ARP entries by.
        interface: Interface name or UUID to filter ARP entries by.
        mac_address: MAC address string to filter by.
        limit: Maximum number of results to return (0 = all).

    Returns:
        ListResponse[ArpEntrySummary] with count and results.
    """
    filters: dict = {}

    if device:
        device_id = resolve_device_id(client, device)
        filters["device"] = device_id

    if interface:
        filters["interface"] = interface

    if mac_address:
        filters["mac_address"] = mac_address

    return cms_list(client, "juniper_arp_entries", ArpEntrySummary, limit=limit, **filters)


def get_arp_entry(
    client: "NautobotClient",
    id: str,
) -> ArpEntrySummary:
    """Get a single ARP entry by UUID.

    Args:
        client: NautobotClient instance.
        id: UUID of the ARP entry.

    Returns:
        ArpEntrySummary instance.

    Raises:
        NautobotNotFoundError: If the ARP entry is not found.
    """
    return cms_get(client, "juniper_arp_entries", ArpEntrySummary, id=id)
