"""Tests for pydantic models."""

from nautobot_mcp.models.base import ListResponse, RelatedObject
from nautobot_mcp.models.circuit import CircuitSummary
from nautobot_mcp.models.device import DeviceSummary
from nautobot_mcp.models.interface import InterfaceSummary
from nautobot_mcp.models.ipam import IPAddressSummary, PrefixSummary, VLANSummary
from nautobot_mcp.models.organization import LocationSummary, TenantSummary


def test_related_object_creation():
    """RelatedObject should be created with id and name."""
    obj = RelatedObject(id="abc-123", name="Test Object")
    assert obj.id == "abc-123"
    assert obj.name == "Test Object"


def test_related_object_optional_display():
    """RelatedObject display field should be optional."""
    obj = RelatedObject(id="abc-123", name="Test")
    assert obj.display is None

    obj_with_display = RelatedObject(id="abc-123", name="Test", display="Test Display")
    assert obj_with_display.display == "Test Display"


def test_list_response():
    """ListResponse should hold count and results."""
    items = [
        RelatedObject(id="1", name="First"),
        RelatedObject(id="2", name="Second"),
    ]
    response = ListResponse(count=2, results=items)
    assert response.count == 2
    assert len(response.results) == 2
    assert response.results[0].name == "First"


def test_device_summary_from_dict():
    """DeviceSummary should be created with all required fields."""
    device = DeviceSummary(
        id="dev-123",
        name="core-rtr-01",
        status="Active",
        device_type=RelatedObject(id="dt-1", name="MX204"),
        location=RelatedObject(id="loc-1", name="SGN-DC1"),
        tenant=RelatedObject(id="t-1", name="NetNam"),
        role=RelatedObject(id="r-1", name="Router"),
        platform="junos",
        serial="ABC123",
    )
    assert device.name == "core-rtr-01"
    assert device.device_type.name == "MX204"
    assert device.location.name == "SGN-DC1"
    assert device.tenant.name == "NetNam"
    assert device.platform == "junos"


def test_device_summary_optional_fields():
    """DeviceSummary optional fields should default to None."""
    device = DeviceSummary(
        id="dev-123",
        name="switch-01",
        status="Active",
        device_type=RelatedObject(id="dt-1", name="EX4300"),
        location=RelatedObject(id="loc-1", name="HAN-DC1"),
    )
    assert device.tenant is None
    assert device.role is None
    assert device.platform is None
    assert device.serial is None
    assert device.primary_ip is None


def test_device_summary_from_nautobot(mock_device_record):
    """DeviceSummary.from_nautobot should convert a mock record."""
    device = DeviceSummary.from_nautobot(mock_device_record)
    assert device.id == "aaaa-bbbb-cccc-dddd"
    assert device.name == "core-rtr-01"
    assert device.status == "Active"
    assert device.device_type.name == "MX204"
    assert device.location.name == "SGN-DC1"
    assert device.tenant.name == "NetNam"
    assert device.platform == "junos"


def test_interface_summary():
    """InterfaceSummary should be created with all fields."""
    iface = InterfaceSummary(
        id="iface-123",
        name="ge-0/0/0",
        type="1000BASE-T",
        device=RelatedObject(id="dev-1", name="core-rtr-01"),
        enabled=True,
        description="Uplink",
        mac_address="00:11:22:33:44:55",
        mtu=9000,
        ip_addresses=["10.0.0.1/30"],
    )
    assert iface.name == "ge-0/0/0"
    assert iface.device.name == "core-rtr-01"
    assert iface.mtu == 9000
    assert "10.0.0.1/30" in iface.ip_addresses


def test_interface_summary_from_nautobot(mock_interface_record):
    """InterfaceSummary.from_nautobot should convert a mock record."""
    iface = InterfaceSummary.from_nautobot(mock_interface_record)
    assert iface.id == "iiii-jjjj-kkkk-llll"
    assert iface.name == "ge-0/0/0"
    assert iface.type == "1000BASE-T"
    assert iface.enabled is True
    assert iface.mtu == 9000


def test_prefix_summary():
    """PrefixSummary should support namespace (Nautobot v2)."""
    prefix = PrefixSummary(
        id="pfx-123",
        prefix="10.0.0.0/24",
        status="Active",
        namespace=RelatedObject(id="ns-1", name="Global"),
        type="Network",
    )
    assert prefix.prefix == "10.0.0.0/24"
    assert prefix.namespace.name == "Global"
    assert prefix.type == "Network"


def test_ip_address_summary():
    """IPAddressSummary should be created with namespace."""
    ip = IPAddressSummary(
        id="ip-123",
        address="10.0.0.1/24",
        status="Active",
        namespace=RelatedObject(id="ns-1", name="Global"),
        dns_name="router.example.com",
    )
    assert ip.address == "10.0.0.1/24"
    assert ip.dns_name == "router.example.com"


def test_vlan_summary():
    """VLANSummary should be created with vid and name."""
    vlan = VLANSummary(
        id="vlan-123",
        vid=100,
        name="Management",
        status="Active",
    )
    assert vlan.vid == 100
    assert vlan.name == "Management"


def test_tenant_summary():
    """TenantSummary should be created with name."""
    tenant = TenantSummary(
        id="t-123",
        name="NetNam",
        description="Main tenant",
    )
    assert tenant.name == "NetNam"
    assert tenant.tenant_group is None


def test_location_summary():
    """LocationSummary should have location_type (Nautobot v2)."""
    location = LocationSummary(
        id="loc-123",
        name="SGN-DC1",
        location_type=RelatedObject(id="lt-1", name="Data Center"),
        status="Active",
    )
    assert location.name == "SGN-DC1"
    assert location.location_type.name == "Data Center"


def test_circuit_summary():
    """CircuitSummary should have provider and circuit_type."""
    circuit = CircuitSummary(
        id="cir-123",
        cid="VIETTEL-001",
        provider=RelatedObject(id="p-1", name="Viettel"),
        circuit_type=RelatedObject(id="ct-1", name="Internet"),
        status="Active",
    )
    assert circuit.cid == "VIETTEL-001"
    assert circuit.provider.name == "Viettel"
    assert circuit.circuit_type.name == "Internet"
