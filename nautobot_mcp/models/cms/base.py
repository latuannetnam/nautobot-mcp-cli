"""Base Pydantic models for CMS plugin data objects.

Provides the CMSBaseSummary base class that all CMS domain models extend.
Follows the same pattern as existing models (from_nautobot classmethod).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CMSBaseSummary(BaseModel):
    """Base model for all CMS plugin objects.

    Provides common fields present on every netnam-cms-core model:
    id, display, url, and device reference.
    """

    id: str = Field(description="UUID of the CMS object")
    display: str = Field(default="", description="Human-readable display string")
    url: Optional[str] = Field(default=None, description="API URL of the object")
    device_id: Optional[str] = Field(default=None, description="UUID of the associated device")
    device_name: Optional[str] = Field(default=None, description="Name of the associated device")

    @classmethod
    def _extract_device(cls, record) -> tuple[Optional[str], Optional[str]]:
        """Extract device ID and name from a pynautobot record.

        Handles both nested record objects and dict-style access.

        Args:
            record: pynautobot Record with optional device field.

        Returns:
            Tuple of (device_id, device_name), either may be None.
        """
        device = getattr(record, "device", None)
        if device is None:
            return None, None
        if hasattr(device, "id"):
            return str(device.id), str(getattr(device, "name", getattr(device, "display", "")))
        if isinstance(device, dict):
            return device.get("id"), device.get("display", device.get("name"))
        # device might be a UUID string
        return str(device), None

    @classmethod
    def _get_field(cls, record, field_name, default=None):
        """Safely get a field value from a pynautobot record.

        Args:
            record: pynautobot Record object.
            field_name: Name of the field to extract.
            default: Default value if field is missing.

        Returns:
            Field value or default.
        """
        value = getattr(record, field_name, default)
        if value is None:
            return default
        return value

    @classmethod
    def from_nautobot(cls, record) -> "CMSBaseSummary":
        """Create a CMSBaseSummary from a pynautobot record.

        Subclasses should override this to extract domain-specific fields.

        Args:
            record: pynautobot Record object.

        Returns:
            CMSBaseSummary instance.
        """
        device_id, device_name = cls._extract_device(record)
        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
        )

