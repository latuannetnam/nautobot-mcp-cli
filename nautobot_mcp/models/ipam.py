"""Pydantic models for Nautobot IPAM objects."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from nautobot_mcp.models.base import RelatedObject, related_from_record, related_from_record_or_none


class PrefixSummary(BaseModel):
    """Curated summary of a Nautobot Prefix."""

    id: str = Field(description="UUID of the prefix")
    prefix: str = Field(description="Network prefix (e.g., 10.0.0.0/24)")
    status: str = Field(description="Prefix status")
    namespace: RelatedObject = Field(description="IPAM namespace (Nautobot v2)")
    location: Optional[RelatedObject] = Field(default=None, description="Associated location")
    tenant: Optional[RelatedObject] = Field(default=None, description="Owning tenant")
    vlan: Optional[RelatedObject] = Field(default=None, description="Associated VLAN")
    type: str = Field(default="Network", description="Prefix type (Container/Network/Pool)")
    description: Optional[str] = Field(default=None, description="Description")

    @classmethod
    def from_nautobot(cls, record: object) -> PrefixSummary:
        """Convert a pynautobot Prefix Record to PrefixSummary."""
        status = "Unknown"
        if hasattr(record, "status") and record.status:
            status = getattr(record.status, "display", str(record.status))

        prefix_type = "Network"
        if hasattr(record, "type") and record.type:
            prefix_type = getattr(record.type, "display", str(record.type))

        return cls(
            id=str(record.id),
            prefix=str(record.prefix),
            status=status,
            namespace=related_from_record(record.namespace),
            location=related_from_record_or_none(getattr(record, "location", None)),
            tenant=related_from_record_or_none(getattr(record, "tenant", None)),
            vlan=related_from_record_or_none(getattr(record, "vlan", None)),
            type=prefix_type,
            description=getattr(record, "description", None) or None,
        )


class IPAddressSummary(BaseModel):
    """Curated summary of a Nautobot IP Address."""

    id: str = Field(description="UUID of the IP address")
    address: str = Field(description="IP address with mask (e.g., 10.0.0.1/24)")
    status: str = Field(description="IP address status")
    namespace: Optional[RelatedObject] = Field(default=None, description="IPAM namespace")
    tenant: Optional[RelatedObject] = Field(default=None, description="Owning tenant")
    dns_name: Optional[str] = Field(default=None, description="DNS name")
    type: str = Field(default="Host", description="IP address type")

    @classmethod
    def from_nautobot(cls, record: object) -> IPAddressSummary:
        """Convert a pynautobot IP Address Record to IPAddressSummary."""
        status = "Unknown"
        if hasattr(record, "status") and record.status:
            status = getattr(record.status, "display", str(record.status))

        ip_type = "Host"
        if hasattr(record, "type") and record.type:
            ip_type = getattr(record.type, "display", str(record.type))

        return cls(
            id=str(record.id),
            address=str(getattr(record, "address", record)),
            status=status,
            namespace=related_from_record_or_none(getattr(record, "namespace", None)),
            tenant=related_from_record_or_none(getattr(record, "tenant", None)),
            dns_name=getattr(record, "dns_name", None) or None,
            type=ip_type,
        )


class VLANSummary(BaseModel):
    """Curated summary of a Nautobot VLAN."""

    id: str = Field(description="UUID of the VLAN")
    vid: int = Field(description="VLAN ID number")
    name: str = Field(description="VLAN name")
    status: str = Field(description="VLAN status")
    location: Optional[RelatedObject] = Field(default=None, description="Associated location")
    tenant: Optional[RelatedObject] = Field(default=None, description="Owning tenant")
    vlan_group: Optional[RelatedObject] = Field(default=None, description="VLAN group")

    @classmethod
    def from_nautobot(cls, record: object) -> VLANSummary:
        """Convert a pynautobot VLAN Record to VLANSummary."""
        status = "Unknown"
        if hasattr(record, "status") and record.status:
            status = getattr(record.status, "display", str(record.status))

        return cls(
            id=str(record.id),
            vid=int(record.vid),
            name=record.name,
            status=status,
            location=related_from_record_or_none(getattr(record, "location", None)),
            tenant=related_from_record_or_none(getattr(record, "tenant", None)),
            vlan_group=related_from_record_or_none(getattr(record, "vlan_group", None)),
        )
