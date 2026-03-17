"""Pydantic models for parsed device configuration data.

Models represent structured network data extracted from vendor-specific
configuration formats. Nautobot-aligned field names enable direct
mapping to Nautobot objects during onboarding.
"""

from __future__ import annotations

from pydantic import BaseModel


class ParsedIPAddress(BaseModel):
    """IP address from a device configuration."""

    address: str  # e.g., "10.0.0.1/30"
    family: str = "inet"  # "inet" or "inet6"


class ParsedInterfaceUnit(BaseModel):
    """Logical unit within an interface (JunOS subinterface)."""

    unit: int = 0
    description: str = ""
    vlan_id: int | None = None
    ip_addresses: list[ParsedIPAddress] = []


class ParsedInterface(BaseModel):
    """Network interface parsed from device config."""

    name: str  # e.g., "ge-0/0/0"
    description: str = ""
    enabled: bool = True
    interface_type: str = ""  # "physical", "logical", "loopback", etc.
    units: list[ParsedInterfaceUnit] = []


class ParsedVLAN(BaseModel):
    """VLAN definition from device config."""

    name: str
    vlan_id: int
    description: str = ""
    l3_interface: str = ""  # associated IRB/VLAN interface


class ParsedRoutingInstance(BaseModel):
    """Routing instance (VRF) from device config."""

    name: str
    instance_type: str = ""  # "vrf", "virtual-router", etc.
    route_distinguisher: str = ""
    interfaces: list[str] = []  # interface names assigned to this instance


class ParsedProtocolNeighbor(BaseModel):
    """Protocol neighbor/peer from device config."""

    address: str
    remote_as: int | None = None
    description: str = ""
    peer_group: str = ""


class ParsedOSPFArea(BaseModel):
    """OSPF area from device config."""

    area_id: str  # e.g., "0.0.0.0"
    interfaces: list[str] = []


class ParsedProtocol(BaseModel):
    """Routing protocol from device config."""

    protocol: str  # "bgp", "ospf", "isis", etc.
    local_as: int | None = None
    router_id: str = ""
    neighbors: list[ParsedProtocolNeighbor] = []
    areas: list[ParsedOSPFArea] = []


class ParsedFirewallFilter(BaseModel):
    """Firewall filter/ACL from device config."""

    name: str
    family: str = "inet"
    term_count: int = 0
    terms: list[str] = []  # term names


class ParsedSystemSettings(BaseModel):
    """System-level settings from device config."""

    hostname: str = ""
    domain_name: str = ""
    name_servers: list[str] = []
    ntp_servers: list[str] = []
    syslog_hosts: list[str] = []


class ParsedConfig(BaseModel):
    """Top-level container for all parsed configuration data.

    Returned by vendor parsers. Contains all extracted network data
    and warnings for sections that couldn't be parsed.
    """

    hostname: str = ""
    platform: str = ""  # auto-detected: "MX", "EX", "SRX", or "junos"
    network_os: str = "juniper_junos"  # netutils-compatible identifier
    interfaces: list[ParsedInterface] = []
    ip_addresses: list[ParsedIPAddress] = []  # flattened from all interfaces
    vlans: list[ParsedVLAN] = []
    routing_instances: list[ParsedRoutingInstance] = []
    protocols: list[ParsedProtocol] = []
    firewall_filters: list[ParsedFirewallFilter] = []
    system: ParsedSystemSettings = ParsedSystemSettings()
    warnings: list[str] = []
