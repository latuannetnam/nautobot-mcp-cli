"""Circuit CRUD operations using the Nautobot API client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nautobot_mcp.exceptions import NautobotNotFoundError
from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.circuit import CircuitSummary

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


def list_circuits(
    client: NautobotClient,
    provider: Optional[str] = None,
    circuit_type: Optional[str] = None,
    location: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 0,
    **extra_filters: str,
) -> ListResponse[CircuitSummary]:
    """List circuits with optional filtering."""
    try:
        filters = {}
        if provider:
            filters["provider"] = provider
        if circuit_type:
            filters["circuit_type"] = circuit_type
        if location:
            filters["location"] = location
        if q:
            filters["q"] = q
        filters.update(extra_filters)

        if filters:
            records = list(client.api.circuits.circuits.filter(**filters))
        else:
            records = list(client.api.circuits.circuits.all())

        all_results = [CircuitSummary.from_nautobot(r) for r in records]
        limited_results = all_results[:limit] if limit > 0 else all_results

        return ListResponse(count=len(all_results), results=limited_results)

    except Exception as e:
        client._handle_api_error(e, "list", "Circuit")
        raise


def get_circuit(
    client: NautobotClient,
    cid: Optional[str] = None,
    id: Optional[str] = None,
) -> CircuitSummary:
    """Get a single circuit by circuit ID or UUID."""
    if not cid and not id:
        raise ValueError("Either 'cid' or 'id' must be provided")

    try:
        if id:
            record = client.api.circuits.circuits.get(id=id)
        else:
            record = client.api.circuits.circuits.get(cid=cid)

        if record is None:
            identifier = cid or id
            raise NautobotNotFoundError(
                message=f"Circuit '{identifier}' not found",
            )

        return CircuitSummary.from_nautobot(record)

    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "get", "Circuit")
        raise


def create_circuit(
    client: NautobotClient,
    cid: str,
    provider: str,
    circuit_type: str,
    **kwargs: str,
) -> CircuitSummary:
    """Create a new circuit."""
    try:
        data = {
            "cid": cid,
            "provider": {"name": provider},
            "circuit_type": {"name": circuit_type},
            "status": kwargs.pop("status", "Active"),
        }
        data.update(kwargs)
        record = client.api.circuits.circuits.create(**data)
        return CircuitSummary.from_nautobot(record)

    except Exception as e:
        client._handle_api_error(e, "create", "Circuit")
        raise


def update_circuit(
    client: NautobotClient,
    id: str,
    **updates: str,
) -> CircuitSummary:
    """Update an existing circuit."""
    try:
        record = client.api.circuits.circuits.get(id=id)
        if record is None:
            raise NautobotNotFoundError(message=f"Circuit '{id}' not found for update")

        for key, value in updates.items():
            setattr(record, key, value)
        record.save()

        return CircuitSummary.from_nautobot(record)

    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "update", "Circuit")
        raise
