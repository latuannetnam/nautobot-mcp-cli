"""Pydantic models for CMS plugin (netnam-cms-core) data objects.

Submodules per domain are added in subsequent phases:
- routing.py (Phase 9)
- interfaces.py (Phase 10)
- firewalls.py (Phase 11)
- policies.py (Phase 11)
- arp.py (Phase 12)
"""

from nautobot_mcp.models.cms.base import CMSBaseSummary
from nautobot_mcp.models.cms.interfaces import (
    InterfaceFamilyFilterSummary,
    InterfaceFamilyPolicerSummary,
    InterfaceFamilySummary,
    InterfaceUnitSummary,
    VRRPGroupSummary,
    VRRPTrackInterfaceSummary,
    VRRPTrackRouteSummary,
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
]
