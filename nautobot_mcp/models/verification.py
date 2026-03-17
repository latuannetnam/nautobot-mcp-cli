"""Pydantic models for verification drift reports.

Models represent the results of comparing live router state
(ParsedConfig) against Nautobot records, grouped by object type.
"""

from __future__ import annotations

from pydantic import BaseModel


class DriftItem(BaseModel):
    """Single drift between two systems.

    Represents one object that differs between the live device
    and Nautobot records.
    """

    name: str  # object identifier
    status: str  # "missing_in_nautobot", "missing_on_device", "changed"
    nautobot_value: dict | None = None
    device_value: dict | None = None
    changed_fields: dict = {}  # {"field": {"nautobot": x, "device": y}}


class DriftSection(BaseModel):
    """Grouped drifts for one object type.

    Contains lists of missing, extra, and changed items.
    """

    missing: list[DriftItem] = []  # on device but not in Nautobot
    extra: list[DriftItem] = []  # in Nautobot but not on device
    changed: list[DriftItem] = []  # exists in both but different


class DriftReport(BaseModel):
    """Full verification report comparing device vs Nautobot.

    Contains drift sections for each object type and an optional
    config compliance result from Golden Config quick diff.
    """

    device: str
    source: str = "provided"  # "jmcp" or "provided"
    timestamp: str = ""
    interfaces: DriftSection = DriftSection()
    ip_addresses: DriftSection = DriftSection()
    vlans: DriftSection = DriftSection()
    summary: dict = {}  # {"total_drifts": N, "by_type": {...}}
    config_compliance: dict | None = None  # quick_diff result if available
