"""Pydantic models for CMS ARP plugin data objects.

Covers: JuniperArpEntry — read-only ARP table entries scoped to a device.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from nautobot_mcp.models.cms.base import CMSBaseSummary
from nautobot_mcp.models.cms.routing import _extract_nested_id_name, _str_val


class ArpEntrySummary(CMSBaseSummary):
    """Pydantic model for a JuniperArpEntry.

    ARP entries are accessed via interface FK and filtered at the API level
    by device UUID.
    """

    interface_id: str = Field(default="", description="UUID of the interface FK")
    interface_name: Optional[str] = Field(default=None, description="Display name of the interface")
    ip_address: str = Field(default="", description="IP address string (e.g., '10.0.0.1/24')")
    mac_address: str = Field(default="", description="MAC address")
    hostname: str = Field(default="", description="Resolved hostname for the ARP entry")

    @classmethod
    def from_nautobot(cls, record) -> "ArpEntrySummary":
        """Create an ArpEntrySummary from a pynautobot record."""
        device_id, device_name = cls._extract_device(record)

        # interface FK — id + display name
        iface_obj = getattr(record, "interface", None)
        iface_id, iface_name = _extract_nested_id_name(iface_obj)
        iface_id = iface_id or ""

        # device_name from interface.device if not already set
        if device_name is None and iface_obj is not None:
            dev_obj = getattr(iface_obj, "device", None)
            if dev_obj is not None:
                device_name = _str_val(dev_obj, "display") or _str_val(dev_obj, "name") or None
            elif isinstance(iface_obj, dict):
                dev_obj = iface_obj.get("device")
                if isinstance(dev_obj, dict):
                    device_name = dev_obj.get("display") or dev_obj.get("name") or None

        # ip_address nested FK — use display value
        ip_obj = getattr(record, "ip_address", None)
        ip_display: str = ""
        if ip_obj is not None:
            ip_display = (
                _str_val(ip_obj, "display")
                or _str_val(ip_obj, "address")
                or str(ip_obj)
            )

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            interface_id=iface_id,
            interface_name=iface_name,
            ip_address=ip_display,
            mac_address=str(getattr(record, "mac_address", "") or ""),
            hostname=str(getattr(record, "hostname", "") or ""),
        )
