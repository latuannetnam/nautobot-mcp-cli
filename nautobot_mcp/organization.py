"""Organization operations: Tenants and Locations.

Location uses Nautobot v2's unified Location model with LocationType hierarchy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nautobot_mcp.exceptions import NautobotNotFoundError
from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.organization import LocationSummary, TenantSummary

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


# --- Tenant operations ---


def list_tenants(
    client: NautobotClient,
    q: Optional[str] = None,
    limit: int = 0,
    **extra_filters: str,
) -> ListResponse[TenantSummary]:
    """List tenants with optional filtering."""
    try:
        filters = {}
        if q:
            filters["q"] = q
        filters.update(extra_filters)

        if filters:
            records = list(client.api.tenancy.tenants.filter(**filters))
        else:
            records = list(client.api.tenancy.tenants.all())

        all_results = [TenantSummary.from_nautobot(r) for r in records]
        limited_results = all_results[:limit] if limit > 0 else all_results

        return ListResponse(count=len(all_results), results=limited_results)

    except Exception as e:
        client._handle_api_error(e, "list", "Tenant")
        raise


def get_tenant(
    client: NautobotClient,
    name: Optional[str] = None,
    id: Optional[str] = None,
) -> TenantSummary:
    """Get a single tenant by name or ID."""
    if not name and not id:
        raise ValueError("Either 'name' or 'id' must be provided")

    try:
        if id:
            record = client.api.tenancy.tenants.get(id=id)
        else:
            record = client.api.tenancy.tenants.get(name=name)

        if record is None:
            identifier = name or id
            raise NautobotNotFoundError(
                message=f"Tenant '{identifier}' not found",
            )

        return TenantSummary.from_nautobot(record)

    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "get", "Tenant")
        raise


def create_tenant(
    client: NautobotClient,
    name: str,
    **kwargs: str,
) -> TenantSummary:
    """Create a new tenant."""
    try:
        data = {"name": name}
        data.update(kwargs)
        record = client.api.tenancy.tenants.create(**data)
        return TenantSummary.from_nautobot(record)

    except Exception as e:
        client._handle_api_error(e, "create", "Tenant")
        raise


def update_tenant(
    client: NautobotClient,
    id: str,
    **updates: str,
) -> TenantSummary:
    """Update an existing tenant."""
    try:
        record = client.api.tenancy.tenants.get(id=id)
        if record is None:
            raise NautobotNotFoundError(message=f"Tenant '{id}' not found for update")

        for key, value in updates.items():
            setattr(record, key, value)
        record.save()

        return TenantSummary.from_nautobot(record)

    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "update", "Tenant")
        raise


# --- Location operations ---


def list_locations(
    client: NautobotClient,
    location_type: Optional[str] = None,
    parent: Optional[str] = None,
    tenant: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 0,
    **extra_filters: str,
) -> ListResponse[LocationSummary]:
    """List locations with optional filtering."""
    try:
        filters = {}
        if location_type:
            filters["location_type"] = location_type
        if parent:
            filters["parent"] = parent
        if tenant:
            filters["tenant"] = tenant
        if q:
            filters["q"] = q
        filters.update(extra_filters)

        if filters:
            records = list(client.api.dcim.locations.filter(**filters))
        else:
            records = list(client.api.dcim.locations.all())

        all_results = [LocationSummary.from_nautobot(r) for r in records]
        limited_results = all_results[:limit] if limit > 0 else all_results

        return ListResponse(count=len(all_results), results=limited_results)

    except Exception as e:
        client._handle_api_error(e, "list", "Location")
        raise


def get_location(
    client: NautobotClient,
    name: Optional[str] = None,
    id: Optional[str] = None,
) -> LocationSummary:
    """Get a single location by name or ID."""
    if not name and not id:
        raise ValueError("Either 'name' or 'id' must be provided")

    try:
        if id:
            record = client.api.dcim.locations.get(id=id)
        else:
            record = client.api.dcim.locations.get(name=name)

        if record is None:
            identifier = name or id
            raise NautobotNotFoundError(
                message=f"Location '{identifier}' not found",
            )

        return LocationSummary.from_nautobot(record)

    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "get", "Location")
        raise


def create_location(
    client: NautobotClient,
    name: str,
    location_type: str,
    status: str = "Active",
    **kwargs: str,
) -> LocationSummary:
    """Create a new location."""
    try:
        data = {
            "name": name,
            "location_type": {"name": location_type},
            "status": status,
        }
        data.update(kwargs)
        record = client.api.dcim.locations.create(**data)
        return LocationSummary.from_nautobot(record)

    except Exception as e:
        client._handle_api_error(e, "create", "Location")
        raise


def update_location(
    client: NautobotClient,
    id: str,
    **updates: str,
) -> LocationSummary:
    """Update an existing location."""
    try:
        record = client.api.dcim.locations.get(id=id)
        if record is None:
            raise NautobotNotFoundError(message=f"Location '{id}' not found for update")

        for key, value in updates.items():
            setattr(record, key, value)
        record.save()

        return LocationSummary.from_nautobot(record)

    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "update", "Location")
        raise
