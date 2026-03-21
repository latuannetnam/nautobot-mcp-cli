"""Pydantic models for CMS routing plugin data objects.

Covers: StaticRoute, StaticRouteNexthop, StaticRouteQualifiedNexthop,
BGPGroup, BGPNeighbor, BGPAddressFamily, BGPPolicyAssociation, BGPReceivedRoute.
Static routes inline their next-hops. BGP queries are device-scoped.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from nautobot_mcp.models.cms.base import CMSBaseSummary


def _extract_nested_id_name(obj) -> tuple[Optional[str], Optional[str]]:
    """Extract (id, name/display) from a nested pynautobot FK object or dict."""
    if obj is None:
        return None, None
    if hasattr(obj, "id"):
        return str(obj.id), str(getattr(obj, "display", getattr(obj, "name", "")))
    if isinstance(obj, dict):
        return obj.get("id"), obj.get("display", obj.get("name"))
    return str(obj), None


def _str_val(obj, field: str, default: str = "") -> str:
    """Safely get a string value from an object or dict."""
    if obj is None:
        return default
    if hasattr(obj, field):
        v = getattr(obj, field, default)
        return str(v) if v is not None else default
    if isinstance(obj, dict):
        return str(obj.get(field, default) or default)
    return default


class StaticRouteNexthopSummary(CMSBaseSummary):
    """Pydantic model for a JuniperStaticRouteNexthop."""

    route_id: str = Field(description="UUID of the parent static route")
    ip_address: str = Field(default="", description="Next-hop IP address")
    is_active_nexthop: Optional[bool] = Field(default=None)
    weight: int = Field(default=1)
    lsp_name: str = Field(default="")
    mpls_label: str = Field(default="")
    nexthop_type: str = Field(default="")
    via_interface_name: Optional[str] = Field(default=None)

    @classmethod
    def from_nautobot(cls, record) -> "StaticRouteNexthopSummary":
        device_id, device_name = cls._extract_device(record)

        # route FK
        route_obj = getattr(record, "route", None)
        route_id_val, _ = _extract_nested_id_name(route_obj)
        route_id_val = route_id_val or ""

        # ip_address nested FK
        ip_obj = getattr(record, "ip_address", None)
        ip_display = _str_val(ip_obj, "address") or _str_val(ip_obj, "display")

        # via_interface nested FK
        iface_obj = getattr(record, "via_interface", None)
        iface_name: Optional[str] = None
        if iface_obj is not None:
            iface_name = _str_val(iface_obj, "display") or _str_val(iface_obj, "name") or None

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            route_id=route_id_val,
            ip_address=ip_display,
            is_active_nexthop=getattr(record, "is_active_nexthop", None),
            weight=int(getattr(record, "weight", 1) or 1),
            lsp_name=str(getattr(record, "lsp_name", "") or ""),
            mpls_label=str(getattr(record, "mpls_label", "") or ""),
            nexthop_type=str(getattr(record, "nexthop_type", "") or ""),
            via_interface_name=iface_name,
        )


class StaticRouteQualifiedNexthopSummary(CMSBaseSummary):
    """Pydantic model for a JuniperStaticRouteQualifiedNexthop."""

    route_id: str = Field(description="UUID of the parent static route")
    ip_address: str = Field(default="", description="Next-hop IP address")
    is_active_nexthop: Optional[bool] = Field(default=None)
    weight: int = Field(default=1)
    lsp_name: str = Field(default="")
    mpls_label: str = Field(default="")
    nexthop_type: str = Field(default="")
    via_interface_name: Optional[str] = Field(default=None)
    interface_name: Optional[str] = Field(default=None)

    @classmethod
    def from_nautobot(cls, record) -> "StaticRouteQualifiedNexthopSummary":
        device_id, device_name = cls._extract_device(record)

        route_obj = getattr(record, "route", None)
        route_id_val, _ = _extract_nested_id_name(route_obj)
        route_id_val = route_id_val or ""

        ip_obj = getattr(record, "ip_address", None)
        ip_display = _str_val(ip_obj, "address") or _str_val(ip_obj, "display")

        iface_obj = getattr(record, "via_interface", None)
        iface_name: Optional[str] = None
        if iface_obj is not None:
            iface_name = _str_val(iface_obj, "display") or _str_val(iface_obj, "name") or None

        intf_obj = getattr(record, "interface", None)
        interface_name: Optional[str] = None
        if intf_obj is not None:
            interface_name = _str_val(intf_obj, "display") or _str_val(intf_obj, "name") or None

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            route_id=route_id_val,
            ip_address=ip_display,
            is_active_nexthop=getattr(record, "is_active_nexthop", None),
            weight=int(getattr(record, "weight", 1) or 1),
            lsp_name=str(getattr(record, "lsp_name", "") or ""),
            mpls_label=str(getattr(record, "mpls_label", "") or ""),
            nexthop_type=str(getattr(record, "nexthop_type", "") or ""),
            via_interface_name=iface_name,
            interface_name=interface_name,
        )


class StaticRouteSummary(CMSBaseSummary):
    """Pydantic model for a JuniperStaticRoute with inlined next-hops."""

    destination: str = Field(description="Route destination prefix")
    routing_table: str = Field(default="inet.0")
    address_family: str = Field(default="")
    preference: int = Field(default=5)
    metric: int = Field(default=0)
    enabled: bool = Field(default=True)
    discarded: bool = Field(default=False)
    rejected: bool = Field(default=False)
    communities: str = Field(default="")
    routing_instance_name: Optional[str] = Field(default=None)
    routing_instance_id: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    route_state: Optional[str] = Field(default=None)
    # Inlined child records (populated by list_static_routes)
    nexthops: list[StaticRouteNexthopSummary] = Field(default_factory=list)
    qualified_nexthops: list[StaticRouteQualifiedNexthopSummary] = Field(default_factory=list)

    @classmethod
    def from_nautobot(cls, record) -> "StaticRouteSummary":
        device_id, device_name = cls._extract_device(record)

        ri_obj = getattr(record, "routing_instance", None)
        ri_id, ri_name = _extract_nested_id_name(ri_obj)

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            destination=str(getattr(record, "destination", "") or ""),
            routing_table=str(getattr(record, "routing_table", "inet.0") or "inet.0"),
            address_family=str(getattr(record, "address_family", "") or ""),
            preference=int(getattr(record, "preference", 5) or 5),
            metric=int(getattr(record, "metric", 0) or 0),
            enabled=bool(getattr(record, "enabled", True)),
            discarded=bool(getattr(record, "discarded", False)),
            rejected=bool(getattr(record, "rejected", False)),
            communities=str(getattr(record, "communities", "") or ""),
            routing_instance_name=ri_name,
            routing_instance_id=ri_id,
            is_active=getattr(record, "is_active", None),
            route_state=str(getattr(record, "route_state", "") or "") or None,
            nexthops=[],
            qualified_nexthops=[],
        )


class BGPGroupSummary(CMSBaseSummary):
    """Pydantic model for a JuniperBGPGroup."""

    name: str = Field(description="BGP group name")
    description: str = Field(default="")
    type: str = Field(default="", description="internal or external")
    local_address: Optional[str] = Field(default=None)
    cluster_id: str = Field(default="")
    authentication_algorithm: str = Field(default="")
    routing_instance_name: Optional[str] = Field(default=None)
    routing_instance_id: Optional[str] = Field(default=None)
    enabled: bool = Field(default=True)
    neighbor_count: Optional[int] = Field(default=None)

    @classmethod
    def from_nautobot(cls, record) -> "BGPGroupSummary":
        device_id, device_name = cls._extract_device(record)

        ri_obj = getattr(record, "routing_instance", None)
        ri_id, ri_name = _extract_nested_id_name(ri_obj)

        la_obj = getattr(record, "local_address", None)
        local_addr: Optional[str] = None
        if la_obj is not None:
            local_addr = _str_val(la_obj, "address") or _str_val(la_obj, "display") or None

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            name=str(getattr(record, "name", "") or ""),
            description=str(getattr(record, "description", "") or ""),
            type=str(getattr(record, "type", "") or ""),
            local_address=local_addr,
            cluster_id=str(getattr(record, "cluster_id", "") or ""),
            authentication_algorithm=str(getattr(record, "authentication_algorithm", "") or ""),
            routing_instance_name=ri_name,
            routing_instance_id=ri_id,
            enabled=bool(getattr(record, "enabled", True)),
            neighbor_count=getattr(record, "neighbor_count", None),
        )


class BGPNeighborSummary(CMSBaseSummary):
    """Pydantic model for a JuniperBGPNeighbor."""

    group_id: str = Field(description="UUID of the parent BGP group")
    group_name: Optional[str] = Field(default=None)
    peer_ip: Optional[str] = Field(default=None)
    description: str = Field(default="")
    peer_as: Optional[int] = Field(default=None)
    local_address: Optional[str] = Field(default=None)
    remove_private_as: bool = Field(default=False)
    as_override: bool = Field(default=False)
    enabled: bool = Field(default=True)
    session_state: str = Field(default="")
    received_prefix_count: Optional[int] = Field(default=None)
    sent_prefix_count: Optional[int] = Field(default=None)
    flap_count: Optional[int] = Field(default=None)

    @classmethod
    def from_nautobot(cls, record) -> "BGPNeighborSummary":
        device_id, device_name = cls._extract_device(record)

        grp_obj = getattr(record, "group", None)
        grp_id, grp_name = _extract_nested_id_name(grp_obj)
        grp_id = grp_id or ""

        peer_ip_obj = getattr(record, "peer_ip", None)
        peer_ip: Optional[str] = None
        if peer_ip_obj is not None:
            peer_ip = _str_val(peer_ip_obj, "address") or _str_val(peer_ip_obj, "display") or str(peer_ip_obj) or None

        la_obj = getattr(record, "local_address", None)
        local_addr: Optional[str] = None
        if la_obj is not None:
            local_addr = _str_val(la_obj, "address") or _str_val(la_obj, "display") or None

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            group_id=grp_id,
            group_name=grp_name,
            peer_ip=peer_ip,
            description=str(getattr(record, "description", "") or ""),
            peer_as=getattr(record, "peer_as", None),
            local_address=local_addr,
            remove_private_as=bool(getattr(record, "remove_private_as", False)),
            as_override=bool(getattr(record, "as_override", False)),
            enabled=bool(getattr(record, "enabled", True)),
            session_state=str(getattr(record, "session_state", "") or ""),
            received_prefix_count=getattr(record, "received_prefix_count", None),
            sent_prefix_count=getattr(record, "sent_prefix_count", None),
            flap_count=getattr(record, "flap_count", None),
        )


class BGPAddressFamilySummary(CMSBaseSummary):
    """Pydantic model for a JuniperBGPAddressFamily."""

    group_id: Optional[str] = Field(default=None)
    neighbor_id: Optional[str] = Field(default=None)
    address_family: str = Field(default="")
    sub_address_family: str = Field(default="")
    enabled: bool = Field(default=True)
    prefix_limit_max: Optional[int] = Field(default=None)
    prefix_limit_teardown: bool = Field(default=False)

    @classmethod
    def from_nautobot(cls, record) -> "BGPAddressFamilySummary":
        device_id, device_name = cls._extract_device(record)

        grp_obj = getattr(record, "group", None)
        grp_id, _ = _extract_nested_id_name(grp_obj)

        nbr_obj = getattr(record, "neighbor", None)
        nbr_id, _ = _extract_nested_id_name(nbr_obj)

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            group_id=grp_id,
            neighbor_id=nbr_id,
            address_family=str(getattr(record, "address_family", "") or ""),
            sub_address_family=str(getattr(record, "sub_address_family", "") or ""),
            enabled=bool(getattr(record, "enabled", True)),
            prefix_limit_max=getattr(record, "prefix_limit_max", None),
            prefix_limit_teardown=bool(getattr(record, "prefix_limit_teardown", False)),
        )


class BGPPolicyAssociationSummary(CMSBaseSummary):
    """Pydantic model for a JuniperBGPPolicyAssociation."""

    bgp_group_id: Optional[str] = Field(default=None)
    bgp_neighbor_id: Optional[str] = Field(default=None)
    policy_id: str = Field(description="UUID of the associated policy")
    policy_name: Optional[str] = Field(default=None)
    policy_type: str = Field(default="")
    order: int = Field(default=0)

    @classmethod
    def from_nautobot(cls, record) -> "BGPPolicyAssociationSummary":
        device_id, device_name = cls._extract_device(record)

        grp_obj = getattr(record, "bgp_group", None)
        grp_id, _ = _extract_nested_id_name(grp_obj)

        nbr_obj = getattr(record, "bgp_neighbor", None)
        nbr_id, _ = _extract_nested_id_name(nbr_obj)

        pol_obj = getattr(record, "policy", None)
        pol_id, pol_name = _extract_nested_id_name(pol_obj)
        pol_id = pol_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            bgp_group_id=grp_id,
            bgp_neighbor_id=nbr_id,
            policy_id=pol_id,
            policy_name=pol_name,
            policy_type=str(getattr(record, "policy_type", "") or ""),
            order=int(getattr(record, "order", 0) or 0),
        )


class BGPReceivedRouteSummary(CMSBaseSummary):
    """Pydantic model for a JuniperBGPReceivedRoute (read-only)."""

    neighbor_id: str = Field(description="UUID of the BGP neighbor")
    routing_table: str = Field(default="")
    prefix: str = Field(default="")
    is_active: bool = Field(default=False)
    as_path: str = Field(default="")
    local_preference: Optional[int] = Field(default=None)
    med: Optional[int] = Field(default=None)
    next_hop: Optional[str] = Field(default=None)
    origin: str = Field(default="")
    communities: str = Field(default="")

    @classmethod
    def from_nautobot(cls, record) -> "BGPReceivedRouteSummary":
        device_id, device_name = cls._extract_device(record)

        nbr_obj = getattr(record, "neighbor", None)
        nbr_id, _ = _extract_nested_id_name(nbr_obj)
        nbr_id = nbr_id or ""

        nh_obj = getattr(record, "next_hop", None)
        next_hop: Optional[str] = None
        if nh_obj is not None:
            next_hop = _str_val(nh_obj, "address") or _str_val(nh_obj, "display") or str(nh_obj) or None

        pfx_obj = getattr(record, "prefix", None)
        prefix_str: str = ""
        if pfx_obj is not None:
            prefix_str = _str_val(pfx_obj, "prefix") or _str_val(pfx_obj, "display") or str(pfx_obj)
        else:
            prefix_str = str(getattr(record, "prefix", "") or "")

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            neighbor_id=nbr_id,
            routing_table=str(getattr(record, "routing_table", "") or ""),
            prefix=prefix_str,
            is_active=bool(getattr(record, "is_active", False)),
            as_path=str(getattr(record, "as_path", "") or ""),
            local_preference=getattr(record, "local_preference", None),
            med=getattr(record, "med", None),
            next_hop=next_hop,
            origin=str(getattr(record, "origin", "") or ""),
            communities=str(getattr(record, "communities", "") or ""),
        )
