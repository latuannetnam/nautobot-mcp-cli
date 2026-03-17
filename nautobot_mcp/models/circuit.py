"""Pydantic models for Nautobot Circuit objects."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from nautobot_mcp.models.base import RelatedObject, related_from_record, related_from_record_or_none


class CircuitSummary(BaseModel):
    """Curated summary of a Nautobot Circuit."""

    id: str = Field(description="UUID of the circuit")
    cid: str = Field(description="Circuit ID string")
    provider: RelatedObject = Field(description="Circuit provider")
    circuit_type: RelatedObject = Field(description="Circuit type")
    status: str = Field(description="Circuit status")
    tenant: Optional[RelatedObject] = Field(default=None, description="Owning tenant")
    description: Optional[str] = Field(default=None, description="Description")

    @classmethod
    def from_nautobot(cls, record: object) -> CircuitSummary:
        """Convert a pynautobot Circuit Record to CircuitSummary."""
        status = "Unknown"
        if hasattr(record, "status") and record.status:
            status = getattr(record.status, "display", str(record.status))

        return cls(
            id=str(record.id),
            cid=str(record.cid),
            provider=related_from_record(record.provider),
            circuit_type=related_from_record(record.circuit_type),
            status=status,
            tenant=related_from_record_or_none(getattr(record, "tenant", None)),
            description=getattr(record, "description", None) or None,
        )
