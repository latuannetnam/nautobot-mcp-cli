"""Pydantic models for Nautobot Device objects."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from nautobot_mcp.models.base import RelatedObject, related_from_record, related_from_record_or_none
from nautobot_mcp.models.interface import InterfaceSummary
from nautobot_mcp.models.ipam import DeviceIPEntry, VLANSummary


class DeviceSummary(BaseModel):
    """Curated summary of a Nautobot Device.

    Contains the most useful fields for network automation agents,
    with related objects as inline summaries.
    """

    id: str = Field(description="UUID of the device")
    name: str = Field(description="Device hostname")
    status: str = Field(description="Device status (Active, Planned, etc.)")
    device_type: RelatedObject = Field(description="Device type/model")
    location: RelatedObject = Field(description="Physical location")
    tenant: Optional[RelatedObject] = Field(default=None, description="Owning tenant")
    role: Optional[RelatedObject] = Field(default=None, description="Device role")
    platform: Optional[str] = Field(default=None, description="OS platform")
    serial: Optional[str] = Field(default=None, description="Serial number")
    primary_ip: Optional[str] = Field(default=None, description="Primary IP address")

    @classmethod
    def from_nautobot(cls, record: object) -> DeviceSummary:
        """Convert a pynautobot Device Record to DeviceSummary.

        Args:
            record: A pynautobot Record from dcim.devices.

        Returns:
            DeviceSummary with extracted fields.
        """
        # Extract status display string
        status = "Unknown"
        if hasattr(record, "status") and record.status:
            status = getattr(record.status, "display", str(record.status))

        # Extract platform name
        platform = None
        if hasattr(record, "platform") and record.platform:
            platform = getattr(record.platform, "name", str(record.platform))

        # Extract primary IP
        primary_ip = None
        if hasattr(record, "primary_ip") and record.primary_ip:
            primary_ip = str(getattr(record.primary_ip, "display",
                                     getattr(record.primary_ip, "address", str(record.primary_ip))))

        return cls(
            id=str(record.id),
            name=record.name,
            status=status,
            device_type=related_from_record(record.device_type),
            location=related_from_record(record.location),
            tenant=related_from_record_or_none(getattr(record, "tenant", None)),
            role=related_from_record_or_none(getattr(record, "role", None)),
            platform=platform,
            serial=getattr(record, "serial", None) or None,
            primary_ip=primary_ip,
        )


class DeviceStatsResponse(BaseModel):
    """Stats-only device overview — fast, 4 API calls max."""

    device: DeviceSummary = Field(description="Core device info")
    interface_count: int = Field(default=0, description="Total interface count")
    ip_count: int = Field(default=0, description="Total IP count")
    vlan_count: Optional[int] = Field(
        default=None,
        description="Total VLAN count (null if unavailable due to server error)",
    )
    enabled_count: int = Field(default=0, description="Enabled interfaces")
    disabled_count: int = Field(default=0, description="Disabled interfaces")
    warnings: Optional[list[dict[str, str]]] = Field(
        default=None,
        description="Recoverable error warnings from data fetch",
    )


class DeviceInventoryResponse(BaseModel):
    """Full device inventory: interfaces, IPs, VLANs with pagination."""

    device: DeviceSummary = Field(description="Core device info")
    interfaces: list[InterfaceSummary] | None = Field(
        default=None,
        description="Interfaces on this device",
    )
    interface_ips: list[DeviceIPEntry] | None = Field(
        default=None,
        description="IPs assigned to interfaces via M2M",
    )
    vlans: list[VLANSummary] | None = Field(
        default=None,
        description="VLANs on device interfaces",
    )
    total_interfaces: Optional[int] = Field(default=None, description="Total interface count (null if count skipped)")
    total_ips: Optional[int] = Field(default=None, description="Total IP count (null if count skipped)")
    total_vlans: Optional[int] = Field(default=None, description="Total VLAN count (null if count skipped)")
    interfaces_latency_ms: Optional[float] = Field(
        default=None,
        description="Wall-clock ms for interfaces section fetch (null if section not fetched)"
    )
    ips_latency_ms: Optional[float] = Field(
        default=None,
        description="Wall-clock ms for IPs section fetch (null if section not fetched)"
    )
    vlans_latency_ms: Optional[float] = Field(
        default=None,
        description="Wall-clock ms for VLANs section fetch (null if section not fetched)"
    )
    total_latency_ms: Optional[float] = Field(
        default=None,
        description="Total wall-clock ms from first API call to response return"
    )
    limit: int = Field(default=0, description="Max results per page")
    offset: int = Field(default=0, description="Offset applied")
    has_more: bool = Field(default=False, description="More results available")
    warnings: Optional[list[dict[str, str]]] = Field(
        default=None,
        description="Recoverable error warnings from data fetch",
    )
