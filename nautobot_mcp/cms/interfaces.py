"""CMS interface domain CRUD operations.

Provides domain-specific CRUD functions for all Juniper interface models:
- Interface units (full CRUD, device-scoped)
- Interface families (full CRUD)
- Interface family filter associations (list/get/create/delete, no update)
- Interface family policer associations (list/get/create/delete, no update)
- VRRP groups (full CRUD)
- VRRP track routes (list/get only, read-only)
- VRRP track interfaces (list/get only, read-only)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nautobot_mcp.cms.client import (
    cms_create,
    cms_delete,
    cms_get,
    cms_list,
    cms_update,
    resolve_device_id,
)
from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.cms.interfaces import (
    InterfaceFamilyFilterSummary,
    InterfaceFamilyPolicerSummary,
    InterfaceFamilySummary,
    InterfaceUnitSummary,
    VRRPGroupSummary,
    VRRPTrackInterfaceSummary,
    VRRPTrackRouteSummary,
)

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


# ---------------------------------------------------------------------------
# Interface Units (full CRUD, device-scoped)
# ---------------------------------------------------------------------------


def list_interface_units(
    client: NautobotClient,
    device: str,
    limit: int = 0,
) -> ListResponse[InterfaceUnitSummary]:
    """List Juniper interface units for a device (shallow — includes family_count).

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        limit: Maximum number of results (0 = all).

    Returns:
        ListResponse[InterfaceUnitSummary] with family_count populated.
    """
    try:
        device_id = resolve_device_id(client, device)
        units = cms_list(client, "juniper_interface_units", InterfaceUnitSummary, limit=0, device=device_id)

        if units.results:
            # Batch-fetch all families for all units on this device to compute family_count
            unit_ids = [u.id for u in units.results]
            try:
                all_families = cms_list(
                    client,
                    "juniper_interface_families",
                    InterfaceFamilySummary,
                    limit=0,
                    device=device_id,
                )
                # Build lookup: unit_id → family_count
                family_count_by_unit: dict[str, int] = {}
                for fam in all_families.results:
                    family_count_by_unit[fam.unit_id] = family_count_by_unit.get(fam.unit_id, 0) + 1

                for unit in units.results:
                    unit.family_count = family_count_by_unit.get(unit.id, 0)
            except Exception:
                # If batch fetch fails, leave family_count as 0
                pass

        all_results = units.results
        limited = all_results[:limit] if limit > 0 else all_results
        return ListResponse(count=len(all_results), results=limited)
    except Exception as e:
        client._handle_api_error(e, "list", "InterfaceUnit")
        raise


def get_interface_unit(client: NautobotClient, id: str) -> InterfaceUnitSummary:
    """Get a single interface unit by UUID, with inlined family details.

    The returned object includes related families (each with filter/policer names)
    as an extra attribute 'families' (not in the base Pydantic schema).

    Args:
        client: NautobotClient instance.
        id: Interface unit UUID.

    Returns:
        InterfaceUnitSummary with family_count set.
    """
    try:
        unit = cms_get(client, "juniper_interface_units", InterfaceUnitSummary, id=id)

        # Fetch families for this specific unit
        families = cms_list(
            client,
            "juniper_interface_families",
            InterfaceFamilySummary,
            limit=0,
            interface_unit=id,
        )
        unit.family_count = len(families.results)

        # Enrich families with filter/policer counts
        for fam in families.results:
            try:
                filters = cms_list(
                    client,
                    "juniper_interface_family_filters",
                    InterfaceFamilyFilterSummary,
                    limit=0,
                    interface_family=fam.id,
                )
                fam.filter_count = len(filters.results)
            except Exception:
                pass
            try:
                policers = cms_list(
                    client,
                    "juniper_interface_family_policers",
                    InterfaceFamilyPolicerSummary,
                    limit=0,
                    interface_family=fam.id,
                )
                fam.policer_count = len(policers.results)
            except Exception:
                pass

        # Attach families as extra attribute (not in schema, but useful for rich output)
        object.__setattr__(unit, "families", families.results)

        return unit
    except Exception as e:
        client._handle_api_error(e, "get", "InterfaceUnit")
        raise


def create_interface_unit(
    client: NautobotClient,
    interface_id: str,
    **kwargs,
) -> InterfaceUnitSummary:
    """Create a Juniper interface unit.

    Args:
        client: NautobotClient instance.
        interface_id: UUID of the parent interface.
        **kwargs: Additional fields (vlan_mode, encapsulation, description, etc.).

    Returns:
        InterfaceUnitSummary of the created unit.
    """
    try:
        return cms_create(
            client,
            "juniper_interface_units",
            InterfaceUnitSummary,
            interface=interface_id,
            **kwargs,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "InterfaceUnit")
        raise


def update_interface_unit(client: NautobotClient, id: str, **updates) -> InterfaceUnitSummary:
    """Update a Juniper interface unit.

    Args:
        client: NautobotClient instance.
        id: Interface unit UUID.
        **updates: Fields to update.

    Returns:
        Updated InterfaceUnitSummary.
    """
    try:
        return cms_update(client, "juniper_interface_units", InterfaceUnitSummary, id=id, **updates)
    except Exception as e:
        client._handle_api_error(e, "update", "InterfaceUnit")
        raise


def delete_interface_unit(client: NautobotClient, id: str) -> dict:
    """Delete a Juniper interface unit.

    Args:
        client: NautobotClient instance.
        id: Interface unit UUID.

    Returns:
        Dict with success status.
    """
    try:
        return cms_delete(client, "juniper_interface_units", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "InterfaceUnit")
        raise


# ---------------------------------------------------------------------------
# Interface Families (full CRUD)
# ---------------------------------------------------------------------------


def list_interface_families(
    client: NautobotClient,
    unit_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[InterfaceFamilySummary]:
    """List Juniper interface families, optionally filtered by unit.

    Args:
        client: NautobotClient instance.
        unit_id: Filter by parent interface unit UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[InterfaceFamilySummary].
    """
    try:
        filters: dict = {}
        if unit_id:
            filters["interface_unit"] = unit_id
        return cms_list(client, "juniper_interface_families", InterfaceFamilySummary, limit=limit, **filters)
    except Exception as e:
        client._handle_api_error(e, "list", "InterfaceFamily")
        raise


def get_interface_family(client: NautobotClient, id: str) -> InterfaceFamilySummary:
    """Get a single interface family by UUID."""
    try:
        return cms_get(client, "juniper_interface_families", InterfaceFamilySummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "InterfaceFamily")
        raise


def create_interface_family(
    client: NautobotClient,
    unit_id: str,
    family_type: str,
    **kwargs,
) -> InterfaceFamilySummary:
    """Create a Juniper interface family.

    Args:
        client: NautobotClient instance.
        unit_id: UUID of the parent interface unit.
        family_type: Address family type (inet, inet6, mpls, etc.).
        **kwargs: Additional fields (mtu, etc.).

    Returns:
        InterfaceFamilySummary of the created family.
    """
    try:
        return cms_create(
            client,
            "juniper_interface_families",
            InterfaceFamilySummary,
            interface_unit=unit_id,
            family_type=family_type,
            **kwargs,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "InterfaceFamily")
        raise


def update_interface_family(client: NautobotClient, id: str, **updates) -> InterfaceFamilySummary:
    """Update a Juniper interface family."""
    try:
        return cms_update(client, "juniper_interface_families", InterfaceFamilySummary, id=id, **updates)
    except Exception as e:
        client._handle_api_error(e, "update", "InterfaceFamily")
        raise


def delete_interface_family(client: NautobotClient, id: str) -> dict:
    """Delete a Juniper interface family."""
    try:
        return cms_delete(client, "juniper_interface_families", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "InterfaceFamily")
        raise


# ---------------------------------------------------------------------------
# Interface Family Filter Associations (list/get/create/delete — NO update)
# ---------------------------------------------------------------------------


def list_interface_family_filters(
    client: NautobotClient,
    family_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[InterfaceFamilyFilterSummary]:
    """List interface family filter associations, optionally by family.

    Args:
        client: NautobotClient instance.
        family_id: Filter by parent interface family UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[InterfaceFamilyFilterSummary].
    """
    try:
        filters: dict = {}
        if family_id:
            filters["interface_family"] = family_id
        return cms_list(
            client, "juniper_interface_family_filters", InterfaceFamilyFilterSummary, limit=limit, **filters
        )
    except Exception as e:
        client._handle_api_error(e, "list", "InterfaceFamilyFilter")
        raise


def get_interface_family_filter(client: NautobotClient, id: str) -> InterfaceFamilyFilterSummary:
    """Get a single interface family filter association by UUID."""
    try:
        return cms_get(client, "juniper_interface_family_filters", InterfaceFamilyFilterSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "InterfaceFamilyFilter")
        raise


def create_interface_family_filter(
    client: NautobotClient,
    family_id: str,
    filter_id: str,
    filter_type: str,
    enabled: bool = True,
) -> InterfaceFamilyFilterSummary:
    """Create an interface family filter association.

    Args:
        client: NautobotClient instance.
        family_id: UUID of the parent interface family.
        filter_id: UUID of the filter to associate.
        filter_type: Filter direction/type (input, output, etc.).
        enabled: Whether the association is active.

    Returns:
        InterfaceFamilyFilterSummary of the created association.
    """
    try:
        return cms_create(
            client,
            "juniper_interface_family_filters",
            InterfaceFamilyFilterSummary,
            interface_family=family_id,
            filter=filter_id,
            filter_type=filter_type,
            enabled=enabled,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "InterfaceFamilyFilter")
        raise


def delete_interface_family_filter(client: NautobotClient, id: str) -> dict:
    """Delete an interface family filter association."""
    try:
        return cms_delete(client, "juniper_interface_family_filters", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "InterfaceFamilyFilter")
        raise


# ---------------------------------------------------------------------------
# Interface Family Policer Associations (list/get/create/delete — NO update)
# ---------------------------------------------------------------------------


def list_interface_family_policers(
    client: NautobotClient,
    family_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[InterfaceFamilyPolicerSummary]:
    """List interface family policer associations, optionally by family.

    Args:
        client: NautobotClient instance.
        family_id: Filter by parent interface family UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[InterfaceFamilyPolicerSummary].
    """
    try:
        filters: dict = {}
        if family_id:
            filters["interface_family"] = family_id
        return cms_list(
            client, "juniper_interface_family_policers", InterfaceFamilyPolicerSummary, limit=limit, **filters
        )
    except Exception as e:
        client._handle_api_error(e, "list", "InterfaceFamilyPolicer")
        raise


def get_interface_family_policer(client: NautobotClient, id: str) -> InterfaceFamilyPolicerSummary:
    """Get a single interface family policer association by UUID."""
    try:
        return cms_get(client, "juniper_interface_family_policers", InterfaceFamilyPolicerSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "InterfaceFamilyPolicer")
        raise


def create_interface_family_policer(
    client: NautobotClient,
    family_id: str,
    policer_id: str,
    policer_type: str,
    enabled: bool = True,
) -> InterfaceFamilyPolicerSummary:
    """Create an interface family policer association.

    Args:
        client: NautobotClient instance.
        family_id: UUID of the parent interface family.
        policer_id: UUID of the policer to associate.
        policer_type: Policer direction/type (input, output, etc.).
        enabled: Whether the association is active.

    Returns:
        InterfaceFamilyPolicerSummary of the created association.
    """
    try:
        return cms_create(
            client,
            "juniper_interface_family_policers",
            InterfaceFamilyPolicerSummary,
            interface_family=family_id,
            policer=policer_id,
            policer_type=policer_type,
            enabled=enabled,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "InterfaceFamilyPolicer")
        raise


def delete_interface_family_policer(client: NautobotClient, id: str) -> dict:
    """Delete an interface family policer association."""
    try:
        return cms_delete(client, "juniper_interface_family_policers", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "InterfaceFamilyPolicer")
        raise


# ---------------------------------------------------------------------------
# VRRP Groups (full CRUD)
# ---------------------------------------------------------------------------


def list_vrrp_groups(
    client: NautobotClient,
    family_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[VRRPGroupSummary]:
    """List VRRP groups, optionally filtered by interface family.

    Args:
        client: NautobotClient instance.
        family_id: Filter by parent interface family UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[VRRPGroupSummary].
    """
    try:
        filters: dict = {}
        if family_id:
            filters["interface_family"] = family_id
        return cms_list(client, "juniper_vrrp_groups", VRRPGroupSummary, limit=limit, **filters)
    except Exception as e:
        client._handle_api_error(e, "list", "VRRPGroup")
        raise


def get_vrrp_group(client: NautobotClient, id: str) -> VRRPGroupSummary:
    """Get a single VRRP group by UUID."""
    try:
        return cms_get(client, "juniper_vrrp_groups", VRRPGroupSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "VRRPGroup")
        raise


def create_vrrp_group(
    client: NautobotClient,
    family_id: str,
    group_number: int,
    virtual_address_id: str,
    priority: int = 100,
    **kwargs,
) -> VRRPGroupSummary:
    """Create a VRRP group.

    Args:
        client: NautobotClient instance.
        family_id: UUID of the parent interface family.
        group_number: VRRP group number (1-255).
        virtual_address_id: UUID of the virtual IP address.
        priority: VRRP priority (1-254, default 100).
        **kwargs: Additional fields (preempt_hold_time, accept_data, etc.).

    Returns:
        VRRPGroupSummary of the created group.
    """
    try:
        return cms_create(
            client,
            "juniper_vrrp_groups",
            VRRPGroupSummary,
            interface_family=family_id,
            group_number=group_number,
            virtual_address=virtual_address_id,
            priority=priority,
            **kwargs,
        )
    except Exception as e:
        client._handle_api_error(e, "create", "VRRPGroup")
        raise


def update_vrrp_group(client: NautobotClient, id: str, **updates) -> VRRPGroupSummary:
    """Update a VRRP group."""
    try:
        return cms_update(client, "juniper_vrrp_groups", VRRPGroupSummary, id=id, **updates)
    except Exception as e:
        client._handle_api_error(e, "update", "VRRPGroup")
        raise


def delete_vrrp_group(client: NautobotClient, id: str) -> dict:
    """Delete a VRRP group."""
    try:
        return cms_delete(client, "juniper_vrrp_groups", id=id)
    except Exception as e:
        client._handle_api_error(e, "delete", "VRRPGroup")
        raise


# ---------------------------------------------------------------------------
# VRRP Track Routes (list/get only — read-only)
# ---------------------------------------------------------------------------


def list_vrrp_track_routes(
    client: NautobotClient,
    vrrp_group_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[VRRPTrackRouteSummary]:
    """List VRRP tracked routes, optionally filtered by VRRP group.

    Args:
        client: NautobotClient instance.
        vrrp_group_id: Filter by parent VRRP group UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[VRRPTrackRouteSummary].
    """
    try:
        filters: dict = {}
        if vrrp_group_id:
            filters["vrrp_group"] = vrrp_group_id
        return cms_list(client, "juniper_vrrp_track_routes", VRRPTrackRouteSummary, limit=limit, **filters)
    except Exception as e:
        client._handle_api_error(e, "list", "VRRPTrackRoute")
        raise


def get_vrrp_track_route(client: NautobotClient, id: str) -> VRRPTrackRouteSummary:
    """Get a single VRRP tracked route by UUID."""
    try:
        return cms_get(client, "juniper_vrrp_track_routes", VRRPTrackRouteSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "VRRPTrackRoute")
        raise


# ---------------------------------------------------------------------------
# VRRP Track Interfaces (list/get only — read-only)
# ---------------------------------------------------------------------------


def list_vrrp_track_interfaces(
    client: NautobotClient,
    vrrp_group_id: Optional[str] = None,
    limit: int = 0,
) -> ListResponse[VRRPTrackInterfaceSummary]:
    """List VRRP tracked interfaces, optionally filtered by VRRP group.

    Args:
        client: NautobotClient instance.
        vrrp_group_id: Filter by parent VRRP group UUID.
        limit: Maximum results (0 = all).

    Returns:
        ListResponse[VRRPTrackInterfaceSummary].
    """
    try:
        filters: dict = {}
        if vrrp_group_id:
            filters["vrrp_group"] = vrrp_group_id
        return cms_list(client, "juniper_vrrp_track_interfaces", VRRPTrackInterfaceSummary, limit=limit, **filters)
    except Exception as e:
        client._handle_api_error(e, "list", "VRRPTrackInterface")
        raise


def get_vrrp_track_interface(client: NautobotClient, id: str) -> VRRPTrackInterfaceSummary:
    """Get a single VRRP tracked interface by UUID."""
    try:
        return cms_get(client, "juniper_vrrp_track_interfaces", VRRPTrackInterfaceSummary, id=id)
    except Exception as e:
        client._handle_api_error(e, "get", "VRRPTrackInterface")
        raise


# ---------------------------------------------------------------------------
# Composite Summary Functions (Phase 12)
# ---------------------------------------------------------------------------

from nautobot_mcp.models.cms.composites import InterfaceDetailResponse  # noqa: E402
from nautobot_mcp.warnings import WarningCollector  # noqa: E402


def get_interface_detail(
    client: "NautobotClient",
    device: str,
    include_arp: bool = False,
) -> tuple[InterfaceDetailResponse, list]:
    """Get a composite interface detail summary for a device.

    Aggregates interface units with their families, VRRP groups, and
    optionally ARP entries into a single device-scoped response.
    VRRP and ARP enrichment failures are captured as warnings rather
    than silently discarded.

    Args:
        client: NautobotClient instance.
        device: Device name or UUID.
        include_arp: If True, fetch ARP entries for the device and inline
            them per interface unit by interface name matching.

    Returns:
        Tuple of (InterfaceDetailResponse, warnings_list).
    """
    collector = WarningCollector()
    try:
        # Fetch all interface units for device
        units_resp = list_interface_units(client, device=device, limit=0)
        units = units_resp.results

        # For each unit, fetch its families and VRRP groups
        enriched_units = []
        for unit in units:
            unit_dict = unit.model_dump()

            # Fetch families for the unit (critical — failure propagates)
            families = list_interface_families(client, unit_id=unit.id, limit=0)
            family_dicts = []
            for fam in families.results:
                fam_dict = fam.model_dump()
                # Add VRRP groups for each family (enrichment — captured as warning)
                try:
                    vrrp = list_vrrp_groups(client, family_id=fam.id, limit=0)
                    fam_dict["vrrp_groups"] = [v.model_dump() for v in vrrp.results]
                    fam_dict["vrrp_group_count"] = vrrp.count
                except Exception as e:
                    collector.add(f"list_vrrp_groups(family={fam.id})", str(e))
                    fam_dict["vrrp_groups"] = []
                    fam_dict["vrrp_group_count"] = 0
                family_dicts.append(fam_dict)

            unit_dict["families"] = family_dicts
            unit_dict["family_count"] = len(families.results)
            enriched_units.append(unit_dict)

        # Optionally include ARP entries (optional enrichment — captured as warning)
        arp_entries = []
        if include_arp:
            try:
                from nautobot_mcp.cms.arp import list_arp_entries
                arp_resp = list_arp_entries(client, device=device, limit=0)
                arp_entries = [e.model_dump() for e in arp_resp.results]
            except Exception as e:
                collector.add("list_arp_entries", str(e))

        result = InterfaceDetailResponse(
            device_name=device,
            units=enriched_units,
            total_units=len(units),
            arp_entries=arp_entries,
        )
        return result, collector.warnings
    except Exception as e:
        client._handle_api_error(e, "get_interface_detail", "InterfaceDetail")
        raise

