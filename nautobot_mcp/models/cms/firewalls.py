"""Pydantic models for CMS firewall plugin data objects.

Covers: FirewallFilter, FirewallTerm, FirewallMatchCondition,
FirewallMatchConditionToPrefixList, FirewallFilterAction,
FirewallPolicer, FirewallPolicerAction.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from nautobot_mcp.models.cms.base import CMSBaseSummary
from nautobot_mcp.models.cms.routing import _extract_nested_id_name, _str_val


class FirewallFilterSummary(CMSBaseSummary):
    """Pydantic model for a JuniperFirewallFilter."""

    name: str = Field(description="Firewall filter name")
    family: str = Field(default="", description="Address family: inet, inet6, vpls, etc.")
    description: str = Field(default="")
    term_count: int = Field(default=0, description="Number of terms (populated by CRUD layer)")

    @classmethod
    def from_nautobot(cls, record) -> "FirewallFilterSummary":
        device_id, device_name = cls._extract_device(record)
        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            name=str(getattr(record, "name", "") or ""),
            family=str(getattr(record, "family", "") or ""),
            description=str(getattr(record, "description", "") or ""),
            term_count=0,
        )


class FirewallTermSummary(CMSBaseSummary):
    """Pydantic model for a JuniperFirewallTerm (child of filter)."""

    filter_id: str = Field(description="UUID of the parent firewall filter")
    filter_name: Optional[str] = Field(default=None)
    name: str = Field(default="")
    order: int = Field(default=0)
    enabled: bool = Field(default=True)
    match_count: int = Field(default=0, description="Number of match conditions (populated by CRUD layer)")
    action_count: int = Field(default=0, description="Number of actions (populated by CRUD layer)")

    @classmethod
    def from_nautobot(cls, record) -> "FirewallTermSummary":
        device_id, device_name = cls._extract_device(record)

        filter_obj = getattr(record, "filter", None)
        filter_id, filter_name = _extract_nested_id_name(filter_obj)
        filter_id = filter_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            filter_id=filter_id,
            filter_name=filter_name,
            name=str(getattr(record, "name", "") or ""),
            order=int(getattr(record, "order", 0) or 0),
            enabled=bool(getattr(record, "enabled", True)),
            match_count=0,
            action_count=0,
        )


class FirewallMatchConditionSummary(CMSBaseSummary):
    """Pydantic model for a JuniperFirewallFilterMatchCondition (child of term)."""

    term_id: str = Field(description="UUID of the parent firewall term")
    condition_type: str = Field(default="", description="e.g. source-address, destination-port, protocol")
    value: str = Field(default="")
    negate: bool = Field(default=False)

    @classmethod
    def from_nautobot(cls, record) -> "FirewallMatchConditionSummary":
        device_id, device_name = cls._extract_device(record)

        term_obj = getattr(record, "term", None)
        term_id, _ = _extract_nested_id_name(term_obj)
        term_id = term_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            term_id=term_id,
            condition_type=str(getattr(record, "condition_type", "") or ""),
            value=str(getattr(record, "value", "") or ""),
            negate=bool(getattr(record, "negate", False)),
        )


class FirewallMatchConditionToPrefixListSummary(CMSBaseSummary):
    """Pydantic model for a FirewallMatchConditionToPrefixList junction table."""

    match_condition_id: str = Field(description="UUID of the match condition")
    prefix_list_id: str = Field(description="UUID of the prefix list")
    prefix_list_name: Optional[str] = Field(default=None)

    @classmethod
    def from_nautobot(cls, record) -> "FirewallMatchConditionToPrefixListSummary":
        device_id, device_name = cls._extract_device(record)

        mc_obj = getattr(record, "match_condition", None)
        mc_id, _ = _extract_nested_id_name(mc_obj)
        mc_id = mc_id or ""

        pl_obj = getattr(record, "prefix_list", None)
        pl_id, pl_name = _extract_nested_id_name(pl_obj)
        pl_id = pl_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            match_condition_id=mc_id,
            prefix_list_id=pl_id,
            prefix_list_name=pl_name,
        )


class FirewallFilterActionSummary(CMSBaseSummary):
    """Pydantic model for a JuniperFirewallFilterAction (child of term)."""

    term_id: str = Field(description="UUID of the parent firewall term")
    action_type: str = Field(default="", description="e.g. accept, discard, reject, count, policer")
    value: str = Field(default="")
    order: int = Field(default=0)
    policer_id: Optional[str] = Field(default=None)
    policer_name: Optional[str] = Field(default=None)

    @classmethod
    def from_nautobot(cls, record) -> "FirewallFilterActionSummary":
        device_id, device_name = cls._extract_device(record)

        term_obj = getattr(record, "term", None)
        term_id, _ = _extract_nested_id_name(term_obj)
        term_id = term_id or ""

        policer_obj = getattr(record, "policer", None)
        policer_id, policer_name = _extract_nested_id_name(policer_obj)

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            term_id=term_id,
            action_type=str(getattr(record, "action_type", "") or ""),
            value=str(getattr(record, "value", "") or ""),
            order=int(getattr(record, "order", 0) or 0),
            policer_id=policer_id,
            policer_name=policer_name,
        )


class FirewallPolicerSummary(CMSBaseSummary):
    """Pydantic model for a JuniperFirewallPolicer (top-level, device-scoped)."""

    name: str = Field(description="Policer name")
    description: str = Field(default="")
    bandwidth_limit: Optional[int] = Field(default=None)
    bandwidth_unit: str = Field(default="")
    burst_limit: Optional[int] = Field(default=None)
    burst_unit: str = Field(default="")
    logical_interface_policer: bool = Field(default=False)
    action_count: int = Field(default=0, description="Number of actions (populated by CRUD layer)")

    @classmethod
    def from_nautobot(cls, record) -> "FirewallPolicerSummary":
        device_id, device_name = cls._extract_device(record)
        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            name=str(getattr(record, "name", "") or ""),
            description=str(getattr(record, "description", "") or ""),
            bandwidth_limit=getattr(record, "bandwidth_limit", None),
            bandwidth_unit=str(getattr(record, "bandwidth_unit", "") or ""),
            burst_limit=getattr(record, "burst_limit", None),
            burst_unit=str(getattr(record, "burst_unit", "") or ""),
            logical_interface_policer=bool(getattr(record, "logical_interface_policer", False)),
            action_count=0,
        )


class FirewallPolicerActionSummary(CMSBaseSummary):
    """Pydantic model for a JuniperFirewallPolicerAction (child of policer)."""

    policer_id: str = Field(description="UUID of the parent policer")
    policer_name: Optional[str] = Field(default=None)
    action_type: str = Field(default="")
    value: str = Field(default="")
    order: int = Field(default=0)

    @classmethod
    def from_nautobot(cls, record) -> "FirewallPolicerActionSummary":
        device_id, device_name = cls._extract_device(record)

        policer_obj = getattr(record, "policer", None)
        policer_id, policer_name = _extract_nested_id_name(policer_obj)
        policer_id = policer_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            policer_id=policer_id,
            policer_name=policer_name,
            action_type=str(getattr(record, "action_type", "") or ""),
            value=str(getattr(record, "value", "") or ""),
            order=int(getattr(record, "order", 0) or 0),
        )
