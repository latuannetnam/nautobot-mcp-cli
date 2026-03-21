"""Pydantic models for CMS drift comparison reports.

Represents the result of comparing live Juniper device state (agent-provided)
against Nautobot CMS model records. Covers BGP neighbor drift (DRIFT-01)
and static route drift (DRIFT-02).
"""

from __future__ import annotations

from pydantic import BaseModel

from nautobot_mcp.models.verification import DriftItem, DriftSection  # noqa: F401


class CMSDriftReport(BaseModel):
    """CMS drift report comparing live device state against Nautobot CMS records.

    Contains drift sections for BGP neighbors and static routes, with a summary
    of total drift count grouped by type.
    """

    device: str
    source: str = "provided"
    timestamp: str = ""
    bgp_neighbors: DriftSection = DriftSection()
    static_routes: DriftSection = DriftSection()
    summary: dict = {}  # {"total_drifts": N, "by_type": {...}}
    warnings: list[str] = []
