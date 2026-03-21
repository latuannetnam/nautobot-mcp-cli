"""Composite response Pydantic models for Phase 12 summary tools.

These are response wrapper models (not API object mirrors) that aggregate
data from multiple CRUD calls into a single structured response.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BGPSummaryResponse(BaseModel):
    """Composite response model for device BGP summary.

    Aggregates BGP groups and neighbors for a single device.
    """

    device_name: str = Field(description="Name of the device")
    groups: list[Any] = Field(
        default_factory=list,
        description="List of BGPGroupSummary dicts with nested neighbor info",
    )
    total_groups: int = Field(default=0, description="Total number of BGP groups")
    total_neighbors: int = Field(default=0, description="Total number of BGP neighbors")


class RoutingTableResponse(BaseModel):
    """Composite response model for device routing table.

    Aggregates static routes (and optionally next-hops) for a single device.
    """

    device_name: str = Field(description="Name of the device")
    routes: list[Any] = Field(
        default_factory=list,
        description="List of StaticRouteSummary dicts with optional next-hop info",
    )
    total_routes: int = Field(default=0, description="Total number of static routes")


class InterfaceDetailResponse(BaseModel):
    """Composite response model for interface unit detail.

    Aggregates interface unit, families, VRRP groups, and ARP entries.
    """

    unit: dict[str, Any] = Field(
        default_factory=dict,
        description="InterfaceUnitSummary data as dict",
    )
    families: list[Any] = Field(
        default_factory=list,
        description="List of InterfaceFamilySummary objects (with optional filters/policers)",
    )
    vrrp_groups: list[Any] = Field(
        default_factory=list,
        description="List of VRRPGroupSummary objects",
    )
    arp_entries: list[Any] = Field(
        default_factory=list,
        description="List of ArpEntrySummary objects for this interface",
    )
    family_count: int = Field(default=0, description="Number of address families")
    vrrp_count: int = Field(default=0, description="Number of VRRP groups")
    arp_count: int = Field(default=0, description="Number of ARP entries")


class FirewallSummaryResponse(BaseModel):
    """Composite response model for device firewall summary.

    Aggregates firewall filters and policers for a single device.
    """

    device_name: str = Field(description="Name of the device")
    filters: list[Any] = Field(
        default_factory=list,
        description="List of FirewallFilterSummary dicts with optional term info",
    )
    policers: list[Any] = Field(
        default_factory=list,
        description="List of FirewallPolicerSummary dicts",
    )
    total_filters: int = Field(default=0, description="Total number of firewall filters")
    total_policers: int = Field(default=0, description="Total number of firewall policers")
