"""Pydantic models for file-free drift comparison results.

Per-interface drift detail + global summary, designed for agent consumption.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class InterfaceDrift(BaseModel):
    """Drift result for a single interface."""

    interface: str
    missing_ips: list[str] = Field(default_factory=list, description="IPs in input but not in Nautobot")
    extra_ips: list[str] = Field(default_factory=list, description="IPs in Nautobot but not in input")
    missing_vlans: list[int] = Field(default_factory=list, description="VLANs in input but not in Nautobot")
    extra_vlans: list[int] = Field(default_factory=list, description="VLANs in Nautobot but not in input")
    has_drift: bool = False


class DriftSummary(BaseModel):
    """Global drift counts across all interfaces."""

    total_drifts: int = 0
    interfaces_checked: int = 0
    interfaces_with_drift: int = 0
    missing_interfaces: list[str] = Field(default_factory=list, description="Input interfaces not found in Nautobot")
    extra_interfaces: list[str] = Field(default_factory=list, description="Nautobot interfaces not in input")
    by_type: dict = Field(default_factory=lambda: {
        "ips": {"missing": 0, "extra": 0},
        "vlans": {"missing": 0, "extra": 0},
        "interfaces": {"missing": 0, "extra": 0},
    })


class QuickDriftReport(BaseModel):
    """Complete file-free drift report: per-interface detail + global summary."""

    device: str
    source: str = "provided"
    timestamp: str = ""
    interface_drifts: list[InterfaceDrift] = Field(default_factory=list)
    summary: DriftSummary = Field(default_factory=DriftSummary)
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
