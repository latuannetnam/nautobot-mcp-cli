"""Pydantic models for CMS plugin (netnam-cms-core) data objects.

Submodules per domain are added in subsequent phases:
- routing.py (Phase 9)
- interfaces.py (Phase 10)
- firewalls.py (Phase 11)
- policies.py (Phase 11)
- arp.py (Phase 12)
- composites.py (Phase 12)
- cms_drift.py (Phase 13)
"""

from nautobot_mcp.models.cms.base import CMSBaseSummary
from nautobot_mcp.models.cms.firewalls import (
    FirewallFilterActionSummary,
    FirewallFilterSummary,
    FirewallMatchConditionSummary,
    FirewallMatchConditionToPrefixListSummary,
    FirewallPolicerActionSummary,
    FirewallPolicerSummary,
    FirewallTermSummary,
)
from nautobot_mcp.models.cms.interfaces import (
    InterfaceFamilyFilterSummary,
    InterfaceFamilyPolicerSummary,
    InterfaceFamilySummary,
    InterfaceUnitSummary,
    VRRPGroupSummary,
    VRRPTrackInterfaceSummary,
    VRRPTrackRouteSummary,
)
from nautobot_mcp.models.cms.policies import (
    JPSActionAsPathSummary,
    JPSActionCommunitySummary,
    JPSActionInstallNexthopSummary,
    JPSActionLoadBalanceSummary,
    JPSActionSummary,
    JPSMatchConditionAsPathSummary,
    JPSMatchConditionCommunitySummary,
    JPSMatchConditionPrefixListSummary,
    JPSMatchConditionRouteFilterSummary,
    JPSMatchConditionSummary,
    JPSTermSummary,
    PolicyAsPathSummary,
    PolicyCommunitySummary,
    PolicyPrefixListSummary,
    PolicyPrefixSummary,
    PolicyStatementSummary,
)
from nautobot_mcp.models.cms.routing import (
    BGPAddressFamilySummary,
    BGPGroupSummary,
    BGPNeighborSummary,
    BGPPolicyAssociationSummary,
    BGPReceivedRouteSummary,
    StaticRouteNexthopSummary,
    StaticRouteQualifiedNexthopSummary,
    StaticRouteSummary,
)
from nautobot_mcp.models.cms.arp import ArpEntrySummary
from nautobot_mcp.models.cms.cms_drift import CMSDriftReport
from nautobot_mcp.models.cms.composites import (
    BGPSummaryResponse,
    FirewallSummaryResponse,
    InterfaceDetailResponse,
    RoutingTableResponse,
)

__all__ = [
    "CMSBaseSummary",
    # Routing models (Phase 9)
    "StaticRouteSummary",
    "StaticRouteNexthopSummary",
    "StaticRouteQualifiedNexthopSummary",
    "BGPGroupSummary",
    "BGPNeighborSummary",
    "BGPAddressFamilySummary",
    "BGPPolicyAssociationSummary",
    "BGPReceivedRouteSummary",
    # Interface models (Phase 10)
    "InterfaceUnitSummary",
    "InterfaceFamilySummary",
    "InterfaceFamilyFilterSummary",
    "InterfaceFamilyPolicerSummary",
    "VRRPGroupSummary",
    "VRRPTrackRouteSummary",
    "VRRPTrackInterfaceSummary",
    # Firewall models (Phase 11)
    "FirewallFilterSummary",
    "FirewallTermSummary",
    "FirewallMatchConditionSummary",
    "FirewallMatchConditionToPrefixListSummary",
    "FirewallFilterActionSummary",
    "FirewallPolicerSummary",
    "FirewallPolicerActionSummary",
    # Policy models (Phase 11)
    "PolicyPrefixListSummary",
    "PolicyPrefixSummary",
    "PolicyCommunitySummary",
    "PolicyAsPathSummary",
    "PolicyStatementSummary",
    "JPSTermSummary",
    "JPSMatchConditionSummary",
    "JPSMatchConditionRouteFilterSummary",
    "JPSMatchConditionPrefixListSummary",
    "JPSMatchConditionCommunitySummary",
    "JPSMatchConditionAsPathSummary",
    "JPSActionSummary",
    "JPSActionCommunitySummary",
    "JPSActionAsPathSummary",
    "JPSActionLoadBalanceSummary",
    "JPSActionInstallNexthopSummary",
    # ARP model (Phase 12)
    "ArpEntrySummary",
    # Composite response models (Phase 12)
    "BGPSummaryResponse",
    "RoutingTableResponse",
    "InterfaceDetailResponse",
    "FirewallSummaryResponse",
    # Drift report model (Phase 13)
    "CMSDriftReport",
]
