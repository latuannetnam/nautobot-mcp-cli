"""Pydantic models for CMS policy plugin data objects.

Covers: PolicyPrefixList, PolicyPrefix, PolicyCommunity, PolicyAsPath,
PolicyStatement, JPSTerm, JPSMatchCondition, JPSMatchConditionRouteFilter,
JPSMatchConditionPrefixList, JPSMatchConditionCommunity, JPSMatchConditionAsPath,
JPSAction, JPSActionCommunity, JPSActionAsPath, JPSActionLoadBalance,
JPSActionInstallNexthop.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from nautobot_mcp.models.cms.base import CMSBaseSummary
from nautobot_mcp.models.cms.routing import _extract_nested_id_name, _str_val


class PolicyPrefixListSummary(CMSBaseSummary):
    """Pydantic model for a JuniperPolicyPrefixList (device-scoped)."""

    name: str = Field(description="Prefix list name")
    description: str = Field(default="")
    prefix_count: int = Field(default=0, description="Number of prefixes (populated by CRUD layer)")

    @classmethod
    def from_nautobot(cls, record) -> "PolicyPrefixListSummary":
        device_id, device_name = cls._extract_device(record)
        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            name=str(getattr(record, "name", "") or ""),
            description=str(getattr(record, "description", "") or ""),
            prefix_count=0,
        )


class PolicyPrefixSummary(CMSBaseSummary):
    """Pydantic model for a JuniperPolicyPrefix (child of prefix list)."""

    prefix_list_id: str = Field(description="UUID of the parent prefix list")
    prefix_list_name: Optional[str] = Field(default=None)
    prefix: str = Field(default="")
    prefix_length_min: Optional[int] = Field(default=None)
    prefix_length_max: Optional[int] = Field(default=None)

    @classmethod
    def from_nautobot(cls, record) -> "PolicyPrefixSummary":
        device_id, device_name = cls._extract_device(record)

        pl_obj = getattr(record, "prefix_list", None)
        pl_id, pl_name = _extract_nested_id_name(pl_obj)
        pl_id = pl_id or ""

        # prefix may be a nested IP prefix object
        pfx_obj = getattr(record, "prefix", None)
        if pfx_obj is not None and not isinstance(pfx_obj, str):
            prefix_str = _str_val(pfx_obj, "prefix") or _str_val(pfx_obj, "display") or str(pfx_obj)
        else:
            prefix_str = str(pfx_obj or "")

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            prefix_list_id=pl_id,
            prefix_list_name=pl_name,
            prefix=prefix_str,
            prefix_length_min=getattr(record, "prefix_length_min", None),
            prefix_length_max=getattr(record, "prefix_length_max", None),
        )


class PolicyCommunitySummary(CMSBaseSummary):
    """Pydantic model for a JuniperPolicyCommunity (device-scoped)."""

    name: str = Field(description="Community name")
    members: str = Field(default="", description="Community value string")
    description: str = Field(default="")

    @classmethod
    def from_nautobot(cls, record) -> "PolicyCommunitySummary":
        device_id, device_name = cls._extract_device(record)
        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            name=str(getattr(record, "name", "") or ""),
            members=str(getattr(record, "members", "") or ""),
            description=str(getattr(record, "description", "") or ""),
        )


class PolicyAsPathSummary(CMSBaseSummary):
    """Pydantic model for a JuniperPolicyAsPath (device-scoped)."""

    name: str = Field(description="AS-path name")
    regex: str = Field(default="", description="AS-path regular expression")
    description: str = Field(default="")

    @classmethod
    def from_nautobot(cls, record) -> "PolicyAsPathSummary":
        device_id, device_name = cls._extract_device(record)
        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            name=str(getattr(record, "name", "") or ""),
            regex=str(getattr(record, "regex", "") or ""),
            description=str(getattr(record, "description", "") or ""),
        )


class PolicyStatementSummary(CMSBaseSummary):
    """Pydantic model for a JuniperPolicyStatement (device-scoped)."""

    name: str = Field(description="Policy statement name")
    description: str = Field(default="")
    term_count: int = Field(default=0, description="Number of terms (populated by CRUD layer)")

    @classmethod
    def from_nautobot(cls, record) -> "PolicyStatementSummary":
        device_id, device_name = cls._extract_device(record)
        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            name=str(getattr(record, "name", "") or ""),
            description=str(getattr(record, "description", "") or ""),
            term_count=0,
        )


class JPSTermSummary(CMSBaseSummary):
    """Pydantic model for a JuniperPolicyStatementTerm (child of statement)."""

    statement_id: str = Field(description="UUID of the parent policy statement")
    statement_name: Optional[str] = Field(default=None)
    name: str = Field(default="")
    order: int = Field(default=0)
    enabled: bool = Field(default=True)
    match_count: int = Field(default=0, description="Number of match conditions (populated by CRUD layer)")
    action_count: int = Field(default=0, description="Number of actions (populated by CRUD layer)")

    @classmethod
    def from_nautobot(cls, record) -> "JPSTermSummary":
        device_id, device_name = cls._extract_device(record)

        # FK field on CMS model is policy_statement
        stmt_obj = getattr(record, "policy_statement", None)
        stmt_id, stmt_name = _extract_nested_id_name(stmt_obj)
        stmt_id = stmt_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            statement_id=stmt_id,
            statement_name=stmt_name,
            name=str(getattr(record, "name", "") or ""),
            order=int(getattr(record, "order", 0) or 0),
            enabled=bool(getattr(record, "enabled", True)),
            match_count=0,
            action_count=0,
        )


class JPSMatchConditionSummary(CMSBaseSummary):
    """Pydantic model for a JPSMatchCondition (child of term)."""

    term_id: str = Field(description="UUID of the parent JPS term")
    condition_type: str = Field(default="")
    value: str = Field(default="")
    negate: bool = Field(default=False)

    @classmethod
    def from_nautobot(cls, record) -> "JPSMatchConditionSummary":
        device_id, device_name = cls._extract_device(record)

        # FK field on CMS model is jps_term
        term_obj = getattr(record, "jps_term", None)
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


class JPSMatchConditionRouteFilterSummary(CMSBaseSummary):
    """Pydantic model for a JPSMatchConditionRouteFilter (child of match condition)."""

    match_condition_id: str = Field(description="UUID of the parent match condition")
    address: str = Field(default="")
    prefix_length_min: Optional[int] = Field(default=None)
    prefix_length_max: Optional[int] = Field(default=None)
    match_type: str = Field(default="", description="exact, orlonger, longer, upto, prefix-length-range, through")

    @classmethod
    def from_nautobot(cls, record) -> "JPSMatchConditionRouteFilterSummary":
        device_id, device_name = cls._extract_device(record)

        # FK field on CMS model is jps_match_condition
        mc_obj = getattr(record, "jps_match_condition", None)
        mc_id, _ = _extract_nested_id_name(mc_obj)
        mc_id = mc_id or ""

        # address may be a nested IP prefix object
        addr_obj = getattr(record, "address", None)
        if addr_obj is not None and not isinstance(addr_obj, str):
            address_str = _str_val(addr_obj, "prefix") or _str_val(addr_obj, "display") or str(addr_obj)
        else:
            address_str = str(addr_obj or "")

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            match_condition_id=mc_id,
            address=address_str,
            prefix_length_min=getattr(record, "prefix_length_min", None),
            prefix_length_max=getattr(record, "prefix_length_max", None),
            match_type=str(getattr(record, "match_type", "") or ""),
        )


class JPSMatchConditionPrefixListSummary(CMSBaseSummary):
    """Pydantic model for a JPSMatchConditionPrefixList junction (match condition + prefix list)."""

    match_condition_id: str = Field(description="UUID of the match condition")
    prefix_list_id: str = Field(description="UUID of the prefix list")
    prefix_list_name: Optional[str] = Field(default=None)

    @classmethod
    def from_nautobot(cls, record) -> "JPSMatchConditionPrefixListSummary":
        device_id, device_name = cls._extract_device(record)

        mc_obj = getattr(record, "jps_match_condition", None)
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


class JPSMatchConditionCommunitySummary(CMSBaseSummary):
    """Pydantic model for a JPSMatchConditionCommunity junction (match condition + community)."""

    match_condition_id: str = Field(description="UUID of the match condition")
    community_id: str = Field(description="UUID of the community")
    community_name: Optional[str] = Field(default=None)

    @classmethod
    def from_nautobot(cls, record) -> "JPSMatchConditionCommunitySummary":
        device_id, device_name = cls._extract_device(record)

        mc_obj = getattr(record, "jps_match_condition", None)
        mc_id, _ = _extract_nested_id_name(mc_obj)
        mc_id = mc_id or ""

        comm_obj = getattr(record, "community", None)
        comm_id, comm_name = _extract_nested_id_name(comm_obj)
        comm_id = comm_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            match_condition_id=mc_id,
            community_id=comm_id,
            community_name=comm_name,
        )


class JPSMatchConditionAsPathSummary(CMSBaseSummary):
    """Pydantic model for a JPSMatchConditionAsPath junction (match condition + as-path)."""

    match_condition_id: str = Field(description="UUID of the match condition")
    as_path_id: str = Field(description="UUID of the AS-path")
    as_path_name: Optional[str] = Field(default=None)

    @classmethod
    def from_nautobot(cls, record) -> "JPSMatchConditionAsPathSummary":
        device_id, device_name = cls._extract_device(record)

        mc_obj = getattr(record, "jps_match_condition", None)
        mc_id, _ = _extract_nested_id_name(mc_obj)
        mc_id = mc_id or ""

        asp_obj = getattr(record, "as_path", None)
        asp_id, asp_name = _extract_nested_id_name(asp_obj)
        asp_id = asp_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            match_condition_id=mc_id,
            as_path_id=asp_id,
            as_path_name=asp_name,
        )


class JPSActionSummary(CMSBaseSummary):
    """Pydantic model for a JPSAction (child of term)."""

    term_id: str = Field(description="UUID of the parent JPS term")
    action_type: str = Field(
        default="",
        description="accept, reject, next-term, next-policy, local-preference, metric, origin, etc.",
    )
    value: str = Field(default="")
    order: int = Field(default=0)

    @classmethod
    def from_nautobot(cls, record) -> "JPSActionSummary":
        device_id, device_name = cls._extract_device(record)

        # FK field on CMS model is jps_term
        term_obj = getattr(record, "jps_term", None)
        term_id, _ = _extract_nested_id_name(term_obj)
        term_id = term_id or ""

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
        )


class JPSActionCommunitySummary(CMSBaseSummary):
    """Pydantic model for a JPSActionCommunity (child of action)."""

    action_id: str = Field(description="UUID of the parent JPS action")
    community_id: str = Field(description="UUID of the community")
    community_name: Optional[str] = Field(default=None)
    operation: str = Field(default="", description="add, delete, or set")

    @classmethod
    def from_nautobot(cls, record) -> "JPSActionCommunitySummary":
        device_id, device_name = cls._extract_device(record)

        # FK field on CMS model is jps_action
        action_obj = getattr(record, "jps_action", None)
        action_id, _ = _extract_nested_id_name(action_obj)
        action_id = action_id or ""

        comm_obj = getattr(record, "community", None)
        comm_id, comm_name = _extract_nested_id_name(comm_obj)
        comm_id = comm_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            action_id=action_id,
            community_id=comm_id,
            community_name=comm_name,
            operation=str(getattr(record, "operation", "") or ""),
        )


class JPSActionAsPathSummary(CMSBaseSummary):
    """Pydantic model for a JPSActionAsPath (child of action)."""

    action_id: str = Field(description="UUID of the parent JPS action")
    as_path_id: str = Field(description="UUID of the AS-path")
    as_path_name: Optional[str] = Field(default=None)
    prepend_count: Optional[int] = Field(default=None)

    @classmethod
    def from_nautobot(cls, record) -> "JPSActionAsPathSummary":
        device_id, device_name = cls._extract_device(record)

        action_obj = getattr(record, "jps_action", None)
        action_id, _ = _extract_nested_id_name(action_obj)
        action_id = action_id or ""

        asp_obj = getattr(record, "as_path", None)
        asp_id, asp_name = _extract_nested_id_name(asp_obj)
        asp_id = asp_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            action_id=action_id,
            as_path_id=asp_id,
            as_path_name=asp_name,
            prepend_count=getattr(record, "prepend_count", None),
        )


class JPSActionLoadBalanceSummary(CMSBaseSummary):
    """Pydantic model for a JPSActionLoadBalance (child of action)."""

    action_id: str = Field(description="UUID of the parent JPS action")
    algorithm: str = Field(default="")
    per_packet: bool = Field(default=False)

    @classmethod
    def from_nautobot(cls, record) -> "JPSActionLoadBalanceSummary":
        device_id, device_name = cls._extract_device(record)

        action_obj = getattr(record, "jps_action", None)
        action_id, _ = _extract_nested_id_name(action_obj)
        action_id = action_id or ""

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            action_id=action_id,
            algorithm=str(getattr(record, "algorithm", "") or ""),
            per_packet=bool(getattr(record, "per_packet", False)),
        )


class JPSActionInstallNexthopSummary(CMSBaseSummary):
    """Pydantic model for a JPSActionInstallNexthop (child of action)."""

    action_id: str = Field(description="UUID of the parent JPS action")
    nexthop: str = Field(default="")
    strict: bool = Field(default=False)

    @classmethod
    def from_nautobot(cls, record) -> "JPSActionInstallNexthopSummary":
        device_id, device_name = cls._extract_device(record)

        action_obj = getattr(record, "jps_action", None)
        action_id, _ = _extract_nested_id_name(action_obj)
        action_id = action_id or ""

        # nexthop may be a nested IP object
        nh_obj = getattr(record, "nexthop", None)
        if nh_obj is not None and not isinstance(nh_obj, str):
            nexthop_str = _str_val(nh_obj, "address") or _str_val(nh_obj, "display") or str(nh_obj)
        else:
            nexthop_str = str(nh_obj or "")

        return cls(
            id=str(record.id),
            display=str(getattr(record, "display", "") or ""),
            url=str(getattr(record, "url", None) or "") or None,
            device_id=device_id,
            device_name=device_name,
            action_id=action_id,
            nexthop=nexthop_str,
            strict=bool(getattr(record, "strict", False)),
        )
