"""Verification engine: compare device config against Nautobot using DiffSync.

Uses DiffSync for object-by-object comparison between live router state
(ParsedConfig) and Nautobot records. Produces structured drift reports
grouped by type (interfaces, IPs, VLANs) with missing/extra/changed categories.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from diffsync import Adapter, DiffSyncModel

from nautobot_mcp.golden_config import quick_diff_config
from nautobot_mcp.interfaces import list_interfaces
from nautobot_mcp.ipam import list_ip_addresses, list_vlans
from nautobot_mcp.models.parser import ParsedConfig
from nautobot_mcp.models.verification import DriftItem, DriftReport, DriftSection

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DiffSync models
# ---------------------------------------------------------------------------


class SyncInterface(DiffSyncModel):
    """DiffSync model for interface comparison."""

    _modelname = "interface"
    _identifiers = ("device_name", "name",)
    _attributes = ("description", "enabled",)

    device_name: str
    name: str
    description: str = ""
    enabled: bool = True


class SyncIPAddress(DiffSyncModel):
    """DiffSync model for IP address comparison."""

    _modelname = "ipaddress"
    _identifiers = ("address",)
    _attributes = ("interface_name", "family",)

    address: str
    interface_name: str = ""
    family: str = "inet"


class SyncVLAN(DiffSyncModel):
    """DiffSync model for VLAN comparison."""

    _modelname = "vlan"
    _identifiers = ("vlan_id",)
    _attributes = ("name", "description",)

    vlan_id: int
    name: str = ""
    description: str = ""


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


class ParsedConfigAdapter(Adapter):
    """DiffSync adapter that loads data from a ParsedConfig object."""

    interface = SyncInterface
    ipaddress = SyncIPAddress
    vlan = SyncVLAN
    top_level = ["interface", "ipaddress", "vlan"]

    parsed_config: ParsedConfig | None = None
    device_name: str = ""

    def load(self):
        """Load parsed config data into DiffSync models."""
        if not self.parsed_config:
            return
        for iface in self.parsed_config.interfaces:
            self.add(SyncInterface(
                device_name=self.device_name,
                name=iface.name,
                description=iface.description,
                enabled=iface.enabled,
            ))
            for unit in iface.units:
                for ip in unit.ip_addresses:
                    self.add(SyncIPAddress(
                        address=ip.address,
                        interface_name=f"{iface.name}.{unit.unit}",
                        family=ip.family,
                    ))
        for vlan in self.parsed_config.vlans:
            self.add(SyncVLAN(
                vlan_id=vlan.vlan_id,
                name=vlan.name,
                description=vlan.description,
            ))


class NautobotLiveAdapter(Adapter):
    """DiffSync adapter that loads data from Nautobot API."""

    interface = SyncInterface
    ipaddress = SyncIPAddress
    vlan = SyncVLAN
    top_level = ["interface", "ipaddress", "vlan"]

    client: Any = None  # NautobotClient
    device_name: str = ""

    def load(self):
        """Load Nautobot data into DiffSync models."""
        if not self.client:
            return
        # Load interfaces
        ifaces = list_interfaces(self.client, device_name=self.device_name)
        for iface in ifaces.results:
            self.add(SyncInterface(
                device_name=self.device_name,
                name=iface.name,
                description=iface.description or "",
                enabled=iface.enabled,
            ))

        # Load IPs for the device
        ips = list_ip_addresses(self.client, device=self.device_name)
        for ip in ips.results:
            # Determine interface name from the IP record
            iface_name = ""
            if hasattr(ip, "interface") and ip.interface:
                iface_name = ip.interface if isinstance(ip.interface, str) else ""
            self.add(SyncIPAddress(
                address=ip.address,
                interface_name=iface_name,
                family="inet" if "." in ip.address else "inet6",
            ))

        # Load VLANs
        vlans = list_vlans(self.client)
        for vlan in vlans.results:
            self.add(SyncVLAN(
                vlan_id=vlan.vid,
                name=vlan.name,
                description=vlan.description or "",
            ))


# ---------------------------------------------------------------------------
# Core verification functions
# ---------------------------------------------------------------------------


def verify_config_compliance(
    client: NautobotClient,
    device_name: str,
    live_config: str | None = None,
) -> DriftReport:
    """Compare device's intended vs backup config using Golden Config quick diff.

    Args:
        client: NautobotClient instance.
        device_name: Device name in Nautobot.
        live_config: Optional live config string (noted in report if provided).

    Returns:
        DriftReport with config_compliance field populated.
    """
    compliance_result = quick_diff_config(client, device_name)

    report = DriftReport(
        device=device_name,
        source="provided" if live_config else "golden-config",
        timestamp=datetime.now(timezone.utc).isoformat(),
        config_compliance=compliance_result.model_dump(),
    )
    report.summary = _build_summary(report)
    return report


def verify_data_model(
    client: NautobotClient,
    device_name: str,
    parsed_config: ParsedConfig,
) -> DriftReport:
    """Compare parsed device config against Nautobot data model records.

    Uses DiffSync for object-by-object comparison. Returns drift report
    grouped by interfaces, IPs, VLANs with missing/extra/changed sections.

    Args:
        client: NautobotClient instance.
        device_name: Device name.
        parsed_config: Parsed device configuration.

    Returns:
        DriftReport with interface, IP, and VLAN drift sections.
    """
    # Create adapters
    parsed_adapter = ParsedConfigAdapter()
    parsed_adapter.parsed_config = parsed_config
    parsed_adapter.device_name = device_name

    nautobot_adapter = NautobotLiveAdapter()
    nautobot_adapter.client = client
    nautobot_adapter.device_name = device_name

    # Load data
    parsed_adapter.load()
    nautobot_adapter.load()

    # Calculate diff: what needs to change in nautobot to match parsed
    diff = nautobot_adapter.diff_from(parsed_adapter)

    # Convert to our DriftReport
    report = _diffsync_to_drift_report(diff, device_name)
    report.summary = _build_summary(report)
    return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _diffsync_to_drift_report(diff, device_name: str) -> DriftReport:
    """Translate DiffSync Diff object into a DriftReport.

    Maps DiffSync operations:
    - "+" only → "missing_in_nautobot" (exists on device, not in Nautobot)
    - "-" only → "missing_on_device" (exists in Nautobot, not on device)
    - Both "+" and "-" → "changed" with changed_fields detail
    """
    report = DriftReport(
        device=device_name,
        source="provided",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # DiffSync diff structure: diff.dict() returns a nested dict
    diff_dict = diff.dict()

    # Process each model type
    model_section_map = {
        "interface": "interfaces",
        "ipaddress": "ip_addresses",
        "vlan": "vlans",
    }

    for model_name, section_attr in model_section_map.items():
        section = DriftSection()
        model_diffs = diff_dict.get(model_name, {})

        for obj_key, obj_diff in model_diffs.items():
            if not isinstance(obj_diff, dict):
                continue

            # DiffSync uses "+" for source (device) and "-" for dest (nautobot)
            src = obj_diff.get("+", {}) or {}  # device value
            dst = obj_diff.get("-", {}) or {}  # nautobot value

            if src and dst:
                # Both exist with different attributes → changed
                changed_fields = {}
                for field in set(list(src.keys()) + list(dst.keys())):
                    src_val = src.get(field)
                    dst_val = dst.get(field)
                    if src_val != dst_val:
                        changed_fields[field] = {
                            "device": src_val,
                            "nautobot": dst_val,
                        }
                if changed_fields:
                    section.changed.append(DriftItem(
                        name=str(obj_key),
                        status="changed",
                        device_value=src,
                        nautobot_value=dst,
                        changed_fields=changed_fields,
                    ))
            elif src and not dst:
                # Only in source (device) → missing in nautobot
                section.missing.append(DriftItem(
                    name=str(obj_key),
                    status="missing_in_nautobot",
                    device_value=src,
                ))
            elif dst and not src:
                # Only in dest (nautobot) → extra / missing on device
                section.extra.append(DriftItem(
                    name=str(obj_key),
                    status="missing_on_device",
                    nautobot_value=dst,
                ))

        setattr(report, section_attr, section)

    return report


def _build_summary(report: DriftReport) -> dict:
    """Count total drifts across all sections.

    Returns:
        Dict with total_drifts and per-type breakdown.
    """
    sections = {
        "interfaces": report.interfaces,
        "ip_addresses": report.ip_addresses,
        "vlans": report.vlans,
    }
    by_type = {}
    total = 0

    for type_name, section in sections.items():
        missing_count = len(section.missing)
        extra_count = len(section.extra)
        changed_count = len(section.changed)
        type_total = missing_count + extra_count + changed_count
        by_type[type_name] = {
            "missing": missing_count,
            "extra": extra_count,
            "changed": changed_count,
            "total": type_total,
        }
        total += type_total

    return {"total_drifts": total, "by_type": by_type}
