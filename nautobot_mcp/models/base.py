"""Base pydantic models for Nautobot data objects.

Provides foundational models used across all domain modules:
- RelatedObject: Inline summary of a related Nautobot object
- ListResponse: Generic paginated list response wrapper
- Helper functions for converting pynautobot Records
"""

from __future__ import annotations

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field


class RelatedObject(BaseModel):
    """Inline summary of a related Nautobot object.

    Used for foreign key fields (location, device_type, tenant, etc.)
    to avoid deeply nested responses while preserving key info.
    """

    id: str = Field(description="UUID of the related object")
    name: str = Field(description="Name/display of the related object")
    display: Optional[str] = Field(
        default=None,
        description="Human-readable display string",
    )
    url: Optional[str] = Field(
        default=None,
        description="API URL of the related object",
    )


T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    """Generic paginated list response.

    Wraps list results with count so consumers know the total
    without necessarily fetching all items.
    """

    count: int = Field(description="Total number of matching objects")
    results: list[T] = Field(description="List of result objects")


def related_from_record(record: object) -> RelatedObject:
    """Convert a pynautobot nested Record to a RelatedObject.

    Args:
        record: A pynautobot Record object with id, name, and optionally display.

    Returns:
        RelatedObject with extracted fields.

    Raises:
        ValueError: If record is None or missing required fields.
    """
    if record is None:
        raise ValueError("Cannot create RelatedObject from None")

    return RelatedObject(
        id=str(getattr(record, "id", "")),
        name=str(getattr(record, "name", getattr(record, "display", ""))),
        display=str(getattr(record, "display", "")) if hasattr(record, "display") else None,
        url=str(getattr(record, "url", "")) if hasattr(record, "url") else None,
    )


def related_from_record_or_none(record: object) -> Optional[RelatedObject]:
    """Convert a pynautobot Record to RelatedObject, returning None if empty.

    Args:
        record: A pynautobot Record object, or None.

    Returns:
        RelatedObject if record is not None, else None.
    """
    if record is None:
        return None
    try:
        return related_from_record(record)
    except (ValueError, AttributeError):
        return None
