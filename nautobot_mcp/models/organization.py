"""Pydantic models for Nautobot Organization objects."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from nautobot_mcp.models.base import RelatedObject, related_from_record, related_from_record_or_none


class TenantSummary(BaseModel):
    """Curated summary of a Nautobot Tenant."""

    id: str = Field(description="UUID of the tenant")
    name: str = Field(description="Tenant name")
    tenant_group: Optional[RelatedObject] = Field(default=None, description="Parent tenant group")
    description: Optional[str] = Field(default=None, description="Description")

    @classmethod
    def from_nautobot(cls, record: object) -> TenantSummary:
        """Convert a pynautobot Tenant Record to TenantSummary."""
        return cls(
            id=str(record.id),
            name=record.name,
            tenant_group=related_from_record_or_none(getattr(record, "tenant_group", None)),
            description=getattr(record, "description", None) or None,
        )


class LocationSummary(BaseModel):
    """Curated summary of a Nautobot Location.

    Nautobot v2 uses a unified Location model with LocationType hierarchy,
    replacing the old Site/Region model.
    """

    id: str = Field(description="UUID of the location")
    name: str = Field(description="Location name")
    location_type: RelatedObject = Field(description="Location type (Region, Site, etc.)")
    parent: Optional[RelatedObject] = Field(default=None, description="Parent location")
    tenant: Optional[RelatedObject] = Field(default=None, description="Owning tenant")
    status: str = Field(description="Location status")

    @classmethod
    def from_nautobot(cls, record: object) -> LocationSummary:
        """Convert a pynautobot Location Record to LocationSummary."""
        status = "Unknown"
        if hasattr(record, "status") and record.status:
            status = getattr(record.status, "display", str(record.status))

        return cls(
            id=str(record.id),
            name=record.name,
            location_type=related_from_record(record.location_type),
            parent=related_from_record_or_none(getattr(record, "parent", None)),
            tenant=related_from_record_or_none(getattr(record, "tenant", None)),
            status=status,
        )
