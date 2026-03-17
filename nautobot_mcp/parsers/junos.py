"""JunOS JSON configuration parser.

Parses the output of 'show configuration | display json' into structured
ParsedConfig models. Handles MX, EX, and SRX platform variants with
auto-detection. All JunOS JSON arrays are handled as lists even for
single elements.
"""

from __future__ import annotations

import json
import logging

from nautobot_mcp.models.parser import (
    ParsedConfig,
    ParsedFirewallFilter,
    ParsedIPAddress,
    ParsedInterface,
    ParsedInterfaceUnit,
    ParsedOSPFArea,
    ParsedProtocol,
    ParsedProtocolNeighbor,
    ParsedRoutingInstance,
    ParsedSystemSettings,
    ParsedVLAN,
)
from nautobot_mcp.parsers.base import ParserRegistry, VendorParser

logger = logging.getLogger(__name__)

KNOWN_SECTIONS = {
    "interfaces",
    "vlans",
    "routing-instances",
    "protocols",
    "firewall",
    "system",
    "routing-options",
    "policy-options",
    "class-of-service",
    "security",
    "ethernet-switching",
    "chassis",
    "snmp",
    "services",
    "applications",
    "groups",
    "apply-groups",
}


def _ensure_list(value) -> list:
    """Ensure a value is a list (JunOS JSON wraps single items in lists)."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


@ParserRegistry.register
class JunosJsonParser(VendorParser):
    """Parser for JunOS JSON config output (show configuration | display json)."""

    @property
    def network_os(self) -> str:
        return "juniper_junos"

    @property
    def vendor(self) -> str:
        return "juniper"

    def detect_platform(self, config_data: dict) -> str:
        """Auto-detect platform variant from config data.

        Returns "SRX" if security block present, "EX" if ethernet-switching
        found in interfaces, "MX" as default.
        """
        config = config_data.get("configuration", config_data)
        if "security" in config:
            return "SRX"
        interfaces = config.get("interfaces", {})
        for iface in _ensure_list(interfaces.get("interface", [])):
            if isinstance(iface, dict) and "ethernet-switching" in str(iface):
                return "EX"
        return "MX"

    def parse(self, config_data: dict | str) -> ParsedConfig:
        """Parse JunOS JSON config into structured data.

        Args:
            config_data: JSON dict or JSON string from
                         'show configuration | display json'

        Returns:
            ParsedConfig with all extracted network data.
        """
        if isinstance(config_data, str):
            config_data = json.loads(config_data)

        config = config_data.get("configuration", config_data)
        warnings = []

        # Detect platform
        platform = self.detect_platform(config_data)

        # Parse each section
        system = self._parse_system(config.get("system", {}))
        interfaces = self._parse_interfaces(config.get("interfaces", {}))
        ip_addresses = self._flatten_ip_addresses(interfaces)
        vlans = self._parse_vlans(config.get("vlans", {}))
        routing_instances = self._parse_routing_instances(
            config.get("routing-instances", {})
        )
        protocols = self._parse_protocols(config.get("protocols", {}))
        firewall_filters = self._parse_firewall(config.get("firewall", {}))

        # Record warnings for unrecognized sections
        for key in config:
            if key.startswith("@"):
                continue
            if key not in KNOWN_SECTIONS:
                warnings.append(f"Skipped unrecognized config section: {key}")

        return ParsedConfig(
            hostname=system.hostname,
            platform=platform,
            network_os=self.network_os,
            interfaces=interfaces,
            ip_addresses=ip_addresses,
            vlans=vlans,
            routing_instances=routing_instances,
            protocols=protocols,
            firewall_filters=firewall_filters,
            system=system,
            warnings=warnings,
        )

    def _parse_system(self, system_data: dict) -> ParsedSystemSettings:
        """Extract system settings from JunOS system block."""
        if not system_data:
            return ParsedSystemSettings()

        hostname = system_data.get("host-name", "")
        domain_name = system_data.get("domain-name", "")

        # Name servers
        name_servers = []
        for ns in _ensure_list(system_data.get("name-server", [])):
            if isinstance(ns, dict):
                name_servers.append(ns.get("name", ""))
            elif isinstance(ns, str):
                name_servers.append(ns)

        # NTP servers
        ntp_servers = []
        ntp_block = system_data.get("ntp", {})
        for srv in _ensure_list(ntp_block.get("server", [])):
            if isinstance(srv, dict):
                ntp_servers.append(srv.get("name", ""))
            elif isinstance(srv, str):
                ntp_servers.append(srv)

        # Syslog hosts
        syslog_hosts = []
        syslog_block = system_data.get("syslog", {})
        for host in _ensure_list(syslog_block.get("host", [])):
            if isinstance(host, dict):
                syslog_hosts.append(host.get("name", ""))
            elif isinstance(host, str):
                syslog_hosts.append(host)

        return ParsedSystemSettings(
            hostname=hostname,
            domain_name=domain_name,
            name_servers=name_servers,
            ntp_servers=ntp_servers,
            syslog_hosts=syslog_hosts,
        )

    def _parse_interfaces(self, iface_data: dict) -> list[ParsedInterface]:
        """Extract interfaces from JunOS interfaces block."""
        if not iface_data:
            return []

        interfaces = []
        for iface in _ensure_list(iface_data.get("interface", [])):
            if not isinstance(iface, dict):
                continue

            name = iface.get("name", "")
            description = iface.get("description", "")
            enabled = not iface.get("disable", False)

            # Determine interface type
            if name.startswith("lo"):
                iface_type = "loopback"
            elif name.startswith("irb") or name.startswith("vlan"):
                iface_type = "virtual"
            elif name.startswith("ae"):
                iface_type = "lag"
            elif "." in name:
                iface_type = "logical"
            else:
                iface_type = "physical"

            # Parse units
            units = []
            for unit_data in _ensure_list(iface.get("unit", [])):
                if not isinstance(unit_data, dict):
                    continue
                unit = self._parse_unit(unit_data)
                units.append(unit)

            interfaces.append(
                ParsedInterface(
                    name=name,
                    description=description,
                    enabled=enabled,
                    interface_type=iface_type,
                    units=units,
                )
            )

        return interfaces

    def _parse_unit(self, unit_data: dict) -> ParsedInterfaceUnit:
        """Parse a single interface unit with IP addresses."""
        unit_num = unit_data.get("name", 0)
        try:
            unit_num = int(unit_num)
        except (ValueError, TypeError):
            unit_num = 0

        description = unit_data.get("description", "")
        vlan_id = unit_data.get("vlan-id")
        if vlan_id is not None:
            try:
                vlan_id = int(vlan_id)
            except (ValueError, TypeError):
                vlan_id = None

        # Extract IP addresses from family inet/inet6
        ip_addresses = []
        family = unit_data.get("family", {})

        for family_name, af_key in [("inet", "inet"), ("inet6", "inet6")]:
            af_data = family.get(af_key, {})
            for addr in _ensure_list(af_data.get("address", [])):
                if isinstance(addr, dict):
                    addr_str = addr.get("name", "")
                elif isinstance(addr, str):
                    addr_str = addr
                else:
                    continue
                if addr_str:
                    ip_addresses.append(
                        ParsedIPAddress(address=addr_str, family=family_name)
                    )

        return ParsedInterfaceUnit(
            unit=unit_num,
            description=description,
            vlan_id=vlan_id,
            ip_addresses=ip_addresses,
        )

    def _flatten_ip_addresses(
        self, interfaces: list[ParsedInterface]
    ) -> list[ParsedIPAddress]:
        """Collect all IP addresses from all interface units."""
        ips = []
        for iface in interfaces:
            for unit in iface.units:
                ips.extend(unit.ip_addresses)
        return ips

    def _parse_vlans(self, vlan_data: dict) -> list[ParsedVLAN]:
        """Extract VLANs from JunOS vlans block."""
        if not vlan_data:
            return []

        vlans = []
        for vlan in _ensure_list(vlan_data.get("vlan", [])):
            if not isinstance(vlan, dict):
                continue
            name = vlan.get("name", "")
            vlan_id = vlan.get("vlan-id")
            if vlan_id is not None:
                try:
                    vlan_id = int(vlan_id)
                except (ValueError, TypeError):
                    continue
            else:
                continue  # skip vlans without an ID

            description = vlan.get("description", "")
            l3_interface = vlan.get("l3-interface", "")

            vlans.append(
                ParsedVLAN(
                    name=name,
                    vlan_id=vlan_id,
                    description=description,
                    l3_interface=l3_interface,
                )
            )

        return vlans

    def _parse_routing_instances(self, ri_data: dict) -> list[ParsedRoutingInstance]:
        """Extract routing instances from JunOS routing-instances block."""
        if not ri_data:
            return []

        instances = []
        for inst in _ensure_list(ri_data.get("instance", [])):
            if not isinstance(inst, dict):
                continue

            name = inst.get("name", "")
            instance_type = inst.get("instance-type", "")
            rd = inst.get("route-distinguisher", {})
            rd_value = rd.get("rd-type", "") if isinstance(rd, dict) else ""

            # Get interfaces from interface block
            iface_names = []
            for iface in _ensure_list(inst.get("interface", [])):
                if isinstance(iface, dict):
                    iface_names.append(iface.get("name", ""))
                elif isinstance(iface, str):
                    iface_names.append(iface)

            instances.append(
                ParsedRoutingInstance(
                    name=name,
                    instance_type=instance_type,
                    route_distinguisher=rd_value,
                    interfaces=iface_names,
                )
            )

        return instances

    def _parse_protocols(self, proto_data: dict) -> list[ParsedProtocol]:
        """Extract routing protocols from JunOS protocols block."""
        if not proto_data:
            return []

        protocols = []

        # BGP
        bgp_data = proto_data.get("bgp", {})
        if bgp_data:
            bgp = self._parse_bgp(bgp_data)
            protocols.append(bgp)

        # OSPF
        ospf_data = proto_data.get("ospf", {})
        if ospf_data:
            ospf = self._parse_ospf(ospf_data)
            protocols.append(ospf)

        # IS-IS
        isis_data = proto_data.get("isis", {})
        if isis_data:
            protocols.append(
                ParsedProtocol(
                    protocol="isis",
                    router_id="",
                )
            )

        # LDP
        ldp_data = proto_data.get("ldp", {})
        if ldp_data:
            protocols.append(ParsedProtocol(protocol="ldp"))

        # MPLS
        mpls_data = proto_data.get("mpls", {})
        if mpls_data:
            protocols.append(ParsedProtocol(protocol="mpls"))

        # LLDP
        lldp_data = proto_data.get("lldp", {})
        if lldp_data:
            protocols.append(ParsedProtocol(protocol="lldp"))

        return protocols

    def _parse_bgp(self, bgp_data: dict) -> ParsedProtocol:
        """Parse BGP protocol data."""
        local_as = None
        local_as_val = bgp_data.get("local-as", {})
        if isinstance(local_as_val, dict):
            as_num = local_as_val.get("as-number")
            if as_num is not None:
                try:
                    local_as = int(as_num)
                except (ValueError, TypeError):
                    pass

        router_id = bgp_data.get("router-id", "")

        neighbors = []
        for group in _ensure_list(bgp_data.get("group", [])):
            if not isinstance(group, dict):
                continue
            group_name = group.get("name", "")
            peer_as = group.get("peer-as")
            if peer_as is not None:
                try:
                    peer_as = int(peer_as)
                except (ValueError, TypeError):
                    peer_as = None

            for neighbor in _ensure_list(group.get("neighbor", [])):
                if isinstance(neighbor, dict):
                    addr = neighbor.get("name", "")
                    desc = neighbor.get("description", "")
                    # Neighbor-level peer-as overrides group-level
                    n_peer_as = neighbor.get("peer-as")
                    if n_peer_as is not None:
                        try:
                            n_peer_as = int(n_peer_as)
                        except (ValueError, TypeError):
                            n_peer_as = peer_as
                    else:
                        n_peer_as = peer_as

                    neighbors.append(
                        ParsedProtocolNeighbor(
                            address=addr,
                            remote_as=n_peer_as,
                            description=desc,
                            peer_group=group_name,
                        )
                    )

        return ParsedProtocol(
            protocol="bgp",
            local_as=local_as,
            router_id=router_id,
            neighbors=neighbors,
        )

    def _parse_ospf(self, ospf_data: dict) -> ParsedProtocol:
        """Parse OSPF protocol data."""
        router_id = ospf_data.get("router-id", "")

        areas = []
        for area in _ensure_list(ospf_data.get("area", [])):
            if not isinstance(area, dict):
                continue
            area_id = area.get("name", "")
            iface_names = []
            for iface in _ensure_list(area.get("interface", [])):
                if isinstance(iface, dict):
                    iface_names.append(iface.get("name", ""))
                elif isinstance(iface, str):
                    iface_names.append(iface)
            areas.append(ParsedOSPFArea(area_id=area_id, interfaces=iface_names))

        return ParsedProtocol(
            protocol="ospf",
            router_id=router_id,
            areas=areas,
        )

    def _parse_firewall(self, fw_data: dict) -> list[ParsedFirewallFilter]:
        """Extract firewall filters from JunOS firewall block."""
        if not fw_data:
            return []

        filters = []

        # Family-based filters (family inet { filter { ... }})
        for family_key in ["family", "inet", "inet6"]:
            family_block = fw_data.get(family_key, {})
            if isinstance(family_block, dict):
                for filt in _ensure_list(family_block.get("filter", [])):
                    if isinstance(filt, dict):
                        f = self._parse_single_filter(filt, family_key)
                        if f:
                            filters.append(f)

        # Top-level filters (filter { ... })
        for filt in _ensure_list(fw_data.get("filter", [])):
            if isinstance(filt, dict):
                f = self._parse_single_filter(filt, "inet")
                if f:
                    filters.append(f)

        return filters

    def _parse_single_filter(
        self, filt_data: dict, family: str
    ) -> ParsedFirewallFilter | None:
        """Parse a single firewall filter."""
        name = filt_data.get("name", "")
        if not name:
            return None

        terms = []
        for term in _ensure_list(filt_data.get("term", [])):
            if isinstance(term, dict):
                term_name = term.get("name", "")
                if term_name:
                    terms.append(term_name)

        return ParsedFirewallFilter(
            name=name,
            family=family,
            term_count=len(terms),
            terms=terms,
        )
