# Phase 1 Research: Core Foundation & Nautobot Client

## pynautobot SDK Patterns

### Initialization
```python
import pynautobot
nautobot = pynautobot.api(
    url="https://nautobot.netnam.vn",
    token="your-api-token",
    retries=3  # Built-in retry for 429, 500, 502, 503, 504
)
```

### App → Endpoint → Record Pattern
```python
# App access
devices_endpoint = nautobot.dcim.devices       # Endpoint object
interfaces_endpoint = nautobot.dcim.interfaces  # Endpoint object
prefixes_endpoint = nautobot.ipam.prefixes      # Endpoint object

# CRUD operations on Endpoints
all_devices = devices_endpoint.all()            # Returns RecordSet (all pages auto-fetched)
filtered = devices_endpoint.filter(location="SGN-DC1")  # Filter returns RecordSet
single = devices_endpoint.get(name="core-rtr-01")       # Returns single Record or None
created = devices_endpoint.create(name="new-device", ...) # Returns Record
```

### Record Object
```python
device = nautobot.dcim.devices.get(name="core-rtr-01")
device.id         # UUID string
device.name       # 'core-rtr-01'
device.location   # Nested Record object (has .id, .name, .display)
device.serialize() # Returns dict of all fields

# Update
device.description = "Updated"
device.save()

# Delete
device.delete()
```

### Key Pattern: Related objects are nested Records
```python
device.location        # Record object
device.location.name   # "SGN-DC1"
device.location.id     # UUID
device.device_type     # Record object
device.device_type.display  # "Juniper MX204"
```

### Built-in Retry
pynautobot has `retries` param — handles 429/500/502/503/504 automatically. Aligns with our CONTEXT.md decision for retry with backoff.

## Nautobot REST API v2 Key Details

### Endpoint Structure
```
/api/dcim/devices/          → Devices
/api/dcim/interfaces/       → Interfaces
/api/dcim/device-types/     → Device Types
/api/ipam/prefixes/         → Prefixes
/api/ipam/ip-addresses/     → IP Addresses
/api/ipam/vlans/            → VLANs
/api/ipam/ip-address-to-interface/  → IP-to-Interface M2M
/api/tenancy/tenants/       → Tenants
/api/dcim/locations/        → Locations
/api/circuits/circuits/     → Circuits
/api/circuits/providers/    → Circuit Providers
```

### Nautobot v2 Breaking Changes (from v1/NetBox)
1. **Namespaces** — IPAM now uses Namespaces for uniqueness boundaries. Prefixes and VRFs belong to Namespaces.
2. **IPAddressToInterface** — M2M through table. IP addresses can be assigned to multiple interfaces. Separate endpoint: `/api/ipam/ip-address-to-interface/`
3. **Aggregate → Prefix** — Aggregates removed, migrated to Prefix with `type="Container"`
4. **Unified Role** — `ipam.Role` consolidated into `extras.Role`
5. **Location replaces Site/Region** — Single Location model with LocationType hierarchy

### pynautobot App-to-Endpoint Mapping
```python
nautobot.dcim.devices          # /api/dcim/devices/
nautobot.dcim.interfaces       # /api/dcim/interfaces/
nautobot.dcim.device_types     # /api/dcim/device-types/
nautobot.dcim.locations        # /api/dcim/locations/
nautobot.ipam.prefixes         # /api/ipam/prefixes/
nautobot.ipam.ip_addresses     # /api/ipam/ip-addresses/
nautobot.ipam.vlans            # /api/ipam/vlans/
nautobot.tenancy.tenants       # /api/tenancy/tenants/
nautobot.circuits.circuits     # /api/circuits/circuits/
nautobot.circuits.providers    # /api/circuits/providers/
```

## Pydantic Model Design

### Approach: Curated pydantic models wrapping pynautobot Records
```python
from pydantic import BaseModel
from typing import Optional

class RelatedObject(BaseModel):
    id: str
    name: str
    display: Optional[str] = None

class DeviceSummary(BaseModel):
    id: str
    name: str
    status: str
    location: RelatedObject
    device_type: RelatedObject
    tenant: Optional[RelatedObject] = None
    platform: Optional[str] = None
    serial: Optional[str] = None

    @classmethod
    def from_nautobot(cls, record) -> "DeviceSummary":
        """Convert pynautobot Record to pydantic model"""
        return cls(
            id=str(record.id),
            name=record.name,
            status=record.status.display if record.status else "Unknown",
            location=RelatedObject(
                id=str(record.location.id),
                name=record.location.name,
                display=record.location.display
            ),
            # ... etc
        )
```

### List Response Pattern
```python
class ListResponse(BaseModel):
    count: int
    results: list[DeviceSummary]
```

## Architecture Implications

### Build Order for Phase 1
1. **Project structure** — Create `nautobot_mcp/` package with `__init__.py`
2. **Config + Auth** — Settings model (pydantic-settings), multi-profile support
3. **Base client** — pynautobot wrapper with retry, connection validation
4. **Pydantic models** — All data models with `from_nautobot()` converters
5. **Domain modules** — `devices.py`, `interfaces.py`, `ipam.py`, `organization.py`, `circuits.py`
6. **Custom exceptions** — Exception hierarchy with structured error info
7. **Tests** — Unit tests with mocked pynautobot responses

### Key Risk: Object Reference Resolution
Creating devices requires: DeviceType (→ Manufacturer), Location (→ LocationType), Role.
These must exist before creating the device. Need a "resolve or create" pattern.

## RESEARCH COMPLETE
