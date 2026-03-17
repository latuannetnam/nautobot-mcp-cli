"""Pydantic models for Nautobot Interface objects."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from nautobot_mcp.models.base import RelatedObject, related_from_record


class InterfaceSummary(BaseModel):
    """Curated summary of a Nautobot Interface.

    Contains the most useful fields for network automation,
    including assigned IP addresses.
    """

    id: str = Field(description="UUID of the interface")
    name: str = Field(description="Interface name (e.g., ge-0/0/0)")
    type: str = Field(description="Interface type (e.g., 1000base-t)")
    device: RelatedObject = Field(description="Parent device")
    enabled: bool = Field(default=True, description="Interface admin state")
    description: Optional[str] = Field(default=None, description="Interface description")
    mac_address: Optional[str] = Field(default=None, description="MAC address")
    mtu: Optional[int] = Field(default=None, description="MTU size")
    ip_addresses: list[str] = Field(default_factory=list, description="Assigned IP addresses")

    @classmethod
    def from_nautobot(cls, record: object) -> InterfaceSummary:
        """Convert a pynautobot Interface Record to InterfaceSummary.

        Args:
            record: A pynautobot Record from dcim.interfaces.

        Returns:
            InterfaceSummary with extracted fields.
        """
        # Extract interface type
        iface_type = "unknown"
        if hasattr(record, "type") and record.type:
            iface_type = getattr(record.type, "display", str(record.type))

        # Extract IP addresses
        ip_addresses = []
        if hasattr(record, "ip_addresses") and record.ip_addresses:
            for ip in record.ip_addresses:
                addr = getattr(ip, "display", getattr(ip, "address", str(ip)))
                ip_addresses.append(str(addr))

        return cls(
            id=str(record.id),
            name=record.name,
            type=iface_type,
            device=related_from_record(record.device),
            enabled=getattr(record, "enabled", True),
            description=getattr(record, "description", None) or None,
            mac_address=getattr(record, "mac_address", None) or None,
            mtu=getattr(record, "mtu", None),
            ip_addresses=ip_addresses,
        )
