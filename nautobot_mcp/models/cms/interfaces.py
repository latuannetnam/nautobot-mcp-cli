"""Pydantic models for CMS interface plugin data objects.

Covers: InterfaceUnit, InterfaceFamily, InterfaceFamilyFilter,
InterfaceFamilyPolicer, VRRPGroup, VRRPTrackRoute, VRRPTrackInterface.

Hybrid inlining strategy:
- list_interface_units is shallow (includes family_count)
- get_interface_unit inlines families with filter/policer names
- VRRP tracking models are read-only
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from nautobot_mcp.models.cms.base import CMSBaseSummary
from nautobot_mcp.models.cms.routing import _extract_nested_id_name, _str_val


class InterfaceUnitSummary(CMSBaseSummary):
    """Pydantic model for a JuniperInterfaceUnit.

    Shallow representation used in list responses.
    Rich representation (get) adds inlined families.
    """

    interface_id: Optional[str] = Field(default=None, description="UUID of the parent interface")
    interface_name: Optional[str] = Field(default=None, description="Name of the parent interface")
    unit_number: Optional[int] = Field(default=None, description="Logical unit number (e.g. 0, 100)")
    vlan_mode: str = Field(default="", description="VLAN mode (access, trunk, etc.)")
    encapsulation: str = Field(default="", description="Encapsulation type")
    is_qinq_enabled: bool = Field(default=False, description="Whether Q-in-Q is enabled")
    outer_vlan_ids: list[str] = Field(default_factory=list, description="List of outer VLAN UUIDs")
    inner_vlan_ids: list[str] = Field(default_factory=list, description="List of inner VLAN UUIDs")
    router_tagged_vlan_id: Optional[str] = Field(default=None, description="UUID of the router-tagged VLAN")
    gigether_speed: str = Field(default="", description="GigE speed setting")
    lacp_active: bool = Field(default=False, description="Whether LACP is active")
    description: str = Field(default="")
    family_count: int = Field(default=0, description="Number of interface families on this unit")

    @classmethod
    def from_nautobot(cls, record) -> "InterfaceUnitSummary":
        device_id, device_name = cls._extract_device(record)

        # interface FK
        iface_obj = getattr(record, "interface", None)
        iface_id, iface_name = _extract_nested_id_name(iface_obj)

        # outer_vlans M2M → list of UUID strings
        outer_vlans_raw = getattr(record, "outer_vlans", None) or []
        outer_vlan_ids = [
            str(v.id) if hasattr(v, "id") else str(v.get("id", ""))
            for v in outer_vlans_raw
            if (hasattr(v, "id") and v.id) or (isinstance(v, dict) and v.get("id"))
        ]

        # inner_vlans M2M → list of UUID strings
        inner_vlans_raw = getattr(record, "inner_vlans", None) or []
        inner_vlan_ids = [
            str(v.id) if hasattr(v, "id") else str(v.get("id", ""))
            for v in inner_vlans_raw
            if (hasattr(v, "id") and v.id) or (isinstance(v, dict) and v.get("id"))
        ]

        # router_tagged_vlan FK → UUID string or None
        rt_vlan_obj = getattr(record, "router_tagged_vlan", None)
        router_tagged_vlan_id: Optional[str] = None
        if rt_vlan_obj is not None:
            rt_id, _ = _extract_nested_id_name(rt_vlan_obj)
            router_tagged_vlan_id = rt_id

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            interface_id=iface_id,
            interface_name=iface_name,
            unit_number=getattr(record, "unit_number", None),
            vlan_mode=str(getattr(record, "vlan_mode", "") or ""),
            encapsulation=str(getattr(record, "encapsulation", "") or ""),
            is_qinq_enabled=bool(getattr(record, "is_qinq_enabled", False)),
            outer_vlan_ids=outer_vlan_ids,
            inner_vlan_ids=inner_vlan_ids,
            router_tagged_vlan_id=router_tagged_vlan_id,
            gigether_speed=str(getattr(record, "gigether_speed", "") or ""),
            lacp_active=bool(getattr(record, "lacp_active", False)),
            description=str(getattr(record, "description", "") or ""),
            family_count=0,  # populated by CRUD layer after batch-fetching families
        )


class InterfaceFamilySummary(CMSBaseSummary):
    """Pydantic model for a JuniperInterfaceFamily."""

    unit_id: str = Field(description="UUID of the parent interface unit")
    unit_display: Optional[str] = Field(default=None)
    family_type: str = Field(default="", description="Address family type (inet, inet6, mpls, etc.)")
    mtu: Optional[int] = Field(default=None, description="MTU value")
    filter_count: int = Field(default=0, description="Number of filter associations")
    policer_count: int = Field(default=0, description="Number of policer associations")

    @classmethod
    def from_nautobot(cls, record) -> "InterfaceFamilySummary":
        device_id, device_name = cls._extract_device(record)

        unit_obj = getattr(record, "interface_unit", None)
        unit_id, unit_display = _extract_nested_id_name(unit_obj)
        unit_id = unit_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            unit_id=unit_id,
            unit_display=unit_display,
            family_type=str(getattr(record, "family_type", "") or ""),
            mtu=getattr(record, "mtu", None),
            filter_count=0,
            policer_count=0,
        )


class InterfaceFamilyFilterSummary(CMSBaseSummary):
    """Pydantic model for a JuniperInterfaceFamilyFilter association."""

    family_id: str = Field(description="UUID of the parent interface family")
    filter_id: str = Field(description="UUID of the associated filter")
    filter_name: Optional[str] = Field(default=None, description="Name of the filter")
    filter_type: str = Field(default="", description="Filter type/direction (input, output, etc.)")
    enabled: bool = Field(default=True)

    @classmethod
    def from_nautobot(cls, record) -> "InterfaceFamilyFilterSummary":
        device_id, device_name = cls._extract_device(record)

        family_obj = getattr(record, "interface_family", None)
        family_id, _ = _extract_nested_id_name(family_obj)
        family_id = family_id or ""

        filter_obj = getattr(record, "filter", None)
        filter_id, filter_name = _extract_nested_id_name(filter_obj)
        filter_id = filter_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            family_id=family_id,
            filter_id=filter_id,
            filter_name=filter_name,
            filter_type=str(getattr(record, "filter_type", "") or ""),
            enabled=bool(getattr(record, "enabled", True)),
        )


class InterfaceFamilyPolicerSummary(CMSBaseSummary):
    """Pydantic model for a JuniperInterfaceFamilyPolicer association."""

    family_id: str = Field(description="UUID of the parent interface family")
    policer_id: str = Field(description="UUID of the associated policer")
    policer_name: Optional[str] = Field(default=None, description="Name of the policer")
    policer_type: str = Field(default="", description="Policer type/direction (input, output, etc.)")
    enabled: bool = Field(default=True)

    @classmethod
    def from_nautobot(cls, record) -> "InterfaceFamilyPolicerSummary":
        device_id, device_name = cls._extract_device(record)

        family_obj = getattr(record, "interface_family", None)
        family_id, _ = _extract_nested_id_name(family_obj)
        family_id = family_id or ""

        policer_obj = getattr(record, "policer", None)
        policer_id, policer_name = _extract_nested_id_name(policer_obj)
        policer_id = policer_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            family_id=family_id,
            policer_id=policer_id,
            policer_name=policer_name,
            policer_type=str(getattr(record, "policer_type", "") or ""),
            enabled=bool(getattr(record, "enabled", True)),
        )


class VRRPGroupSummary(CMSBaseSummary):
    """Pydantic model for a JuniperVRRPGroup."""

    family_id: str = Field(description="UUID of the parent interface family")
    family_display: Optional[str] = Field(default=None)
    group_number: int = Field(description="VRRP group number (1-255)")
    virtual_address: Optional[str] = Field(default=None, description="Virtual IP address string")
    interface_address: Optional[str] = Field(default=None, description="Interface IP address string")
    priority: int = Field(default=100, description="VRRP priority (1-254, default 100)")
    accept_data: bool = Field(default=False, description="Whether to accept data packets for virtual IP")
    preempt_hold_time: Optional[int] = Field(default=None, description="Preempt hold time in seconds")
    fast_interval: Optional[int] = Field(default=None, description="Fast advertisement interval in ms")
    authentication_type: str = Field(default="")
    authentication_key_chain: str = Field(default="")
    track_route_count: int = Field(default=0, description="Number of tracked routes")
    track_interface_count: int = Field(default=0, description="Number of tracked interfaces")

    @classmethod
    def from_nautobot(cls, record) -> "VRRPGroupSummary":
        device_id, device_name = cls._extract_device(record)

        family_obj = getattr(record, "interface_family", None)
        family_id, family_display = _extract_nested_id_name(family_obj)
        family_id = family_id or ""

        # virtual_address FK → IP address string
        va_obj = getattr(record, "virtual_address", None)
        virtual_address: Optional[str] = None
        if va_obj is not None:
            virtual_address = _str_val(va_obj, "address") or _str_val(va_obj, "display") or None

        # interface_address FK → IP address string
        ia_obj = getattr(record, "interface_address", None)
        interface_address: Optional[str] = None
        if ia_obj is not None:
            interface_address = _str_val(ia_obj, "address") or _str_val(ia_obj, "display") or None

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            family_id=family_id,
            family_display=family_display,
            group_number=int(getattr(record, "group_number", 0) or 0),
            virtual_address=virtual_address,
            interface_address=interface_address,
            priority=int(getattr(record, "priority", 100) or 100),
            accept_data=bool(getattr(record, "accept_data", False)),
            preempt_hold_time=getattr(record, "preempt_hold_time", None),
            fast_interval=getattr(record, "fast_interval", None),
            authentication_type=str(getattr(record, "authentication_type", "") or ""),
            authentication_key_chain=str(getattr(record, "authentication_key_chain", "") or ""),
            track_route_count=0,
            track_interface_count=0,
        )


class VRRPTrackRouteSummary(CMSBaseSummary):
    """Pydantic model for a JuniperVRRPTrackRoute (read-only)."""

    vrrp_group_id: str = Field(description="UUID of the parent VRRP group")
    route_address: Optional[str] = Field(default=None, description="Tracked route IP prefix string")
    priority_cost: int = Field(default=10, description="Priority reduction cost when route is down")
    routing_instance: str = Field(default="", description="Name of the routing instance")

    @classmethod
    def from_nautobot(cls, record) -> "VRRPTrackRouteSummary":
        device_id, device_name = cls._extract_device(record)

        grp_obj = getattr(record, "vrrp_group", None)
        grp_id, _ = _extract_nested_id_name(grp_obj)
        grp_id = grp_id or ""

        # route_address FK → address string
        ra_obj = getattr(record, "route_address", None)
        route_address: Optional[str] = None
        if ra_obj is not None:
            route_address = _str_val(ra_obj, "address") or _str_val(ra_obj, "prefix") or _str_val(ra_obj, "display") or None

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            vrrp_group_id=grp_id,
            route_address=route_address,
            priority_cost=int(getattr(record, "priority_cost", 10) or 10),
            routing_instance=str(getattr(record, "routing_instance", "") or ""),
        )


class VRRPTrackInterfaceSummary(CMSBaseSummary):
    """Pydantic model for a JuniperVRRPTrackInterface (read-only)."""

    vrrp_group_id: str = Field(description="UUID of the parent VRRP group")
    tracked_interface_id: Optional[str] = Field(default=None, description="UUID of the tracked interface")
    tracked_interface_name: Optional[str] = Field(default=None, description="Name of the tracked interface")
    priority_cost: int = Field(default=10, description="Priority reduction cost when interface is down")

    @classmethod
    def from_nautobot(cls, record) -> "VRRPTrackInterfaceSummary":
        device_id, device_name = cls._extract_device(record)

        grp_obj = getattr(record, "vrrp_group", None)
        grp_id, _ = _extract_nested_id_name(grp_obj)
        grp_id = grp_id or ""

        ti_obj = getattr(record, "tracked_interface", None)
        ti_id, ti_name = _extract_nested_id_name(ti_obj)

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            vrrp_group_id=grp_id,
            tracked_interface_id=ti_id,
            tracked_interface_name=ti_name,
            priority_cost=int(getattr(record, "priority_cost", 10) or 10),
        )
