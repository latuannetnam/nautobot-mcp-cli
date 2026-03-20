"""File-free drift comparison: compare structured data against Nautobot.

Accepts two input shapes with auto-detection:
1. Flat map: {"ae0.0": {"ips": ["10.1.1.1/30"], "vlans": [100]}}
2. DeviceIPEntry list: [{"interface": "ae0", "address": "10.1.1.1/30"}]
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from nautobot_mcp.ipam import get_device_ips, list_vlans
from nautobot_mcp.interfaces import list_interfaces
from nautobot_mcp.models.drift import DriftSummary, InterfaceDrift, QuickDriftReport

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient

logger = logging.getLogger(__name__)


def _normalize_input(
    interfaces_data: dict | list,
) -> tuple[dict[str, dict[str, list]], list[str]]:
    """Normalize input to canonical form + collect warnings.

    Canonical form: {"iface_name": {"ips": ["10.1.1.1/30"], "vlans": [100]}}

    Accepts:
    - Flat map: {"ae0.0": {"ips": [...], "vlans": [...]}}
    - DeviceIPEntry list: [{"interface": "ae0", "address": "10.1.1.1/30"}, ...]
    - Legacy flat map: {"ae0.0": ["10.1.1.1/30"]} (list of IPs directly)

    Returns:
        Tuple of (normalized_dict, warnings_list)
    """
    warnings: list[str] = []

    # Auto-detect: list = DeviceIPEntry shape
    if isinstance(interfaces_data, list):
        normalized: dict[str, dict[str, list]] = {}
        for entry in interfaces_data:
            iface = entry.get("interface") or entry.get("interface_name", "")
            addr = entry.get("address", "")
            if not iface:
                warnings.append(f"Skipping entry with no interface: {entry}")
                continue
            if iface not in normalized:
                normalized[iface] = {"ips": [], "vlans": []}
            if addr:
                normalized[iface]["ips"].append(addr)
        return normalized, warnings

    # Dict shape: flat map
    normalized = {}
    for iface_name, iface_data in interfaces_data.items():
        if isinstance(iface_data, list):
            # Legacy: {"ae0.0": ["10.1.1.1/30"]}
            normalized[iface_name] = {"ips": list(iface_data), "vlans": []}
        elif isinstance(iface_data, dict):
            ips = iface_data.get("ips", [])
            vlans_raw = iface_data.get("vlans", [])
            # Normalize VLAN IDs to int
            vlans = []
            for v in vlans_raw:
                try:
                    vlans.append(int(v))
                except (ValueError, TypeError):
                    warnings.append(f"Invalid VLAN ID '{v}' on {iface_name}, skipping")
            normalized[iface_name] = {"ips": list(ips), "vlans": vlans}
        else:
            warnings.append(f"Unexpected data type for {iface_name}: {type(iface_data)}")

    return normalized, warnings


def _validate_ips(
    ips: list[str],
    interface_name: str,
) -> tuple[list[str], list[str]]:
    """Validate and normalize IP addresses. Lenient with warnings.

    Returns:
        Tuple of (validated_ips, warnings)
    """
    validated = []
    warnings = []
    for ip in ips:
        ip = ip.strip()
        if "/" not in ip:
            warnings.append(
                f"IP '{ip}' on {interface_name} has no prefix length, "
                "matching by host only"
            )
        validated.append(ip)
    return validated, warnings


def compare_device(
    client: NautobotClient,
    device_name: str,
    interfaces_data: dict | list,
) -> QuickDriftReport:
    """Compare structured interface data against Nautobot records.

    Accepts two input shapes (auto-detected):
    1. Flat map: {"ae0.0": {"ips": ["10.1.1.1/30"], "vlans": [100]}}
    2. DeviceIPEntry list: [{"interface": "ae0", "address": "10.1.1.1/30"}]

    Fetches Nautobot data via get_device_ips() and list_interfaces(),
    then compares per-interface.

    Args:
        client: NautobotClient instance.
        device_name: Device hostname in Nautobot.
        interfaces_data: Interface data to compare (auto-detected shape).

    Returns:
        QuickDriftReport with per-interface detail and global summary.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    all_warnings: list[str] = []

    # Step 1: Normalize input
    normalized, norm_warnings = _normalize_input(interfaces_data)
    all_warnings.extend(norm_warnings)

    # Step 2: Validate IPs
    for iface_name, iface_data in normalized.items():
        validated_ips, ip_warnings = _validate_ips(iface_data["ips"], iface_name)
        iface_data["ips"] = validated_ips
        all_warnings.extend(ip_warnings)

    # Step 3: Fetch Nautobot data
    # Get IPs per interface from Nautobot via M2M
    nb_ip_result = get_device_ips(client, device_name=device_name)
    # Build Nautobot IP map: {interface_name: [address, ...]}
    nb_ip_map: dict[str, list[str]] = {}
    for entry in nb_ip_result.interface_ips:
        iface = entry.interface_name
        if iface not in nb_ip_map:
            nb_ip_map[iface] = []
        nb_ip_map[iface].append(entry.address)

    # Get all Nautobot interfaces for this device
    nb_iface_result = list_interfaces(client, device_name=device_name, limit=0)
    nb_iface_names = {iface.name for iface in nb_iface_result.results}

    # Get VLANs per interface from Nautobot
    # Build map: {interface_name: [vlan_id, ...]}
    nb_vlan_map: dict[str, list[int]] = {}
    for iface_record in nb_iface_result.results:
        vlans_for_iface: list[int] = []
        if hasattr(iface_record, "untagged_vlan") and iface_record.untagged_vlan:
            vid = getattr(iface_record.untagged_vlan, "vid", None)
            if vid is not None:
                vlans_for_iface.append(int(vid))
        if hasattr(iface_record, "tagged_vlans") and iface_record.tagged_vlans:
            for vlan in iface_record.tagged_vlans:
                vid = getattr(vlan, "vid", None)
                if vid is not None:
                    vlans_for_iface.append(int(vid))
        if vlans_for_iface:
            nb_vlan_map[iface_record.name] = vlans_for_iface

    # Step 4: Compare per-interface
    interface_drifts: list[InterfaceDrift] = []
    input_iface_names = set(normalized.keys())

    for iface_name, iface_data in normalized.items():
        input_ips = set(iface_data["ips"])
        input_vlans = set(iface_data.get("vlans", []))

        nb_ips = set(nb_ip_map.get(iface_name, []))
        nb_vlans = set(nb_vlan_map.get(iface_name, []))

        # IP comparison: handle bare IPs (no prefix) by host matching
        missing_ips = []
        for ip in input_ips:
            if "/" not in ip:
                # Match by host part only
                if not any(nb_ip.startswith(ip + "/") or nb_ip == ip for nb_ip in nb_ips):
                    missing_ips.append(ip)
            else:
                if ip not in nb_ips:
                    missing_ips.append(ip)

        extra_ips = []
        for nb_ip in nb_ips:
            matched = False
            for in_ip in input_ips:
                if "/" not in in_ip:
                    if nb_ip.startswith(in_ip + "/") or nb_ip == in_ip:
                        matched = True
                        break
                else:
                    if nb_ip == in_ip:
                        matched = True
                        break
            if not matched:
                extra_ips.append(nb_ip)

        # VLAN comparison (only if VLANs were provided in input)
        missing_vlans = sorted(input_vlans - nb_vlans) if input_vlans else []
        extra_vlans = sorted(nb_vlans - input_vlans) if input_vlans else []

        has_drift = bool(missing_ips or extra_ips or missing_vlans or extra_vlans)

        interface_drifts.append(InterfaceDrift(
            interface=iface_name,
            missing_ips=sorted(missing_ips),
            extra_ips=sorted(extra_ips),
            missing_vlans=missing_vlans,
            extra_vlans=extra_vlans,
            has_drift=has_drift,
        ))

    # Step 5: Check for missing/extra interfaces
    missing_interfaces = sorted(input_iface_names - nb_iface_names)
    extra_interfaces = sorted(nb_iface_names - input_iface_names)

    # Step 6: Build summary
    total_missing_ips = sum(len(d.missing_ips) for d in interface_drifts)
    total_extra_ips = sum(len(d.extra_ips) for d in interface_drifts)
    total_missing_vlans = sum(len(d.missing_vlans) for d in interface_drifts)
    total_extra_vlans = sum(len(d.extra_vlans) for d in interface_drifts)
    total_drifts = (
        total_missing_ips + total_extra_ips
        + total_missing_vlans + total_extra_vlans
        + len(missing_interfaces) + len(extra_interfaces)
    )

    summary = DriftSummary(
        total_drifts=total_drifts,
        interfaces_checked=len(normalized),
        interfaces_with_drift=sum(1 for d in interface_drifts if d.has_drift),
        missing_interfaces=missing_interfaces,
        extra_interfaces=extra_interfaces,
        by_type={
            "ips": {"missing": total_missing_ips, "extra": total_extra_ips},
            "vlans": {"missing": total_missing_vlans, "extra": total_extra_vlans},
            "interfaces": {"missing": len(missing_interfaces), "extra": len(extra_interfaces)},
        },
    )

    return QuickDriftReport(
        device=device_name,
        source="provided",
        timestamp=timestamp,
        interface_drifts=interface_drifts,
        summary=summary,
        warnings=all_warnings,
    )
