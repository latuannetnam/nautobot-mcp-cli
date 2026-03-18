"""Config onboarding engine: parse → match → create/update in Nautobot.

Takes a ParsedConfig (from Phase 3 parser) and creates/updates Nautobot
objects. Supports dry-run (default) and commit modes, idempotent matching
by name+device, and auto-resolution of prerequisites.
"""

from __future__ import annotations

import ipaddress
import logging
from typing import TYPE_CHECKING, Optional

from nautobot_mcp.devices import create_device, get_device
from nautobot_mcp.exceptions import NautobotNotFoundError
from nautobot_mcp.interfaces import create_interface, get_interface, update_interface
from nautobot_mcp.ipam import create_ip_address, create_prefix, create_vlan, list_vlans
from nautobot_mcp.models.onboarding import OnboardAction, OnboardResult, OnboardSummary
from nautobot_mcp.models.parser import ParsedConfig

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Interface type mapping
# ---------------------------------------------------------------------------

JUNOS_INTERFACE_TYPE_MAP = {
    "ge-": "1000base-t",
    "xe-": "10gbase-x-sfpp",
    "et-": "25gbase-x-sfp28",
    "ae": "lag",
    "lo": "virtual",
    "irb": "virtual",
    "vlan": "virtual",
    "me": "1000base-t",
    "fxp": "1000base-t",
    "em": "1000base-t",
}


def map_interface_type(interface_name: str) -> str:
    """Map JunOS interface name prefix to Nautobot interface type.

    Args:
        interface_name: JunOS interface name (e.g., "ge-0/0/0", "lo0").

    Returns:
        Nautobot interface type string.
    """
    for prefix, iface_type in JUNOS_INTERFACE_TYPE_MAP.items():
        if interface_name.startswith(prefix):
            return iface_type
    return "other"


# ---------------------------------------------------------------------------
# Core onboarding function
# ---------------------------------------------------------------------------


def onboard_config(
    client: NautobotClient,
    parsed_config: ParsedConfig,
    device_name: str,
    dry_run: bool = True,
    update_existing: bool = False,
    location: str | None = None,
    device_type: str | None = None,
    role: str = "Router",
    namespace: str = "Global",
) -> OnboardResult:
    """Onboard a parsed router config into Nautobot.

    Resolves device, interfaces, IP addresses, and VLANs from the parsed
    config. In dry-run mode (default), returns planned actions without
    committing. In commit mode, executes each action.

    Args:
        client: NautobotClient instance.
        parsed_config: Parsed device configuration from Phase 3 parser.
        device_name: Target device name in Nautobot.
        dry_run: If True, show planned changes without committing.
        update_existing: If True, update existing objects with new values.
        location: Device location name (auto-detected if possible).
        device_type: Device type name (auto-detected from platform).
        role: Device role name (default: "Router").
        namespace: IPAM namespace (default: "Global").

    Returns:
        OnboardResult with summary, actions, and warnings.
    """
    actions: list[OnboardAction] = []
    warnings: list[str] = []
    device_id: str | None = None

    # Step 1: Resolve device
    device_action, device_id = _resolve_device(
        client, device_name, parsed_config, location, device_type, role, dry_run,
    )
    actions.append(device_action)

    # Step 2: Resolve interfaces
    iface_actions = _resolve_interfaces(
        client, device_name, device_id, parsed_config, dry_run, update_existing,
    )
    actions.extend(iface_actions)

    # Step 3: Resolve IP addresses
    ip_actions = _resolve_ip_addresses(
        client, device_name, device_id, parsed_config, namespace, dry_run,
    )
    actions.extend(ip_actions)

    # Step 4: Resolve VLANs
    vlan_actions = _resolve_vlans(client, parsed_config, dry_run)
    actions.extend(vlan_actions)

    # Build summary
    summary = OnboardSummary(
        total=len(actions),
        created=sum(1 for a in actions if a.action == "create"),
        updated=sum(1 for a in actions if a.action == "update"),
        skipped=sum(1 for a in actions if a.action == "skip"),
        failed=sum(1 for a in actions if a.action == "failed"),
    )

    # If commit mode, execute actions
    if not dry_run:
        actions, summary, new_warnings = _execute_actions(
            client, actions, device_name, location, device_type, role, namespace,
        )
        warnings.extend(new_warnings)

    return OnboardResult(
        device=device_name,
        dry_run=dry_run,
        summary=summary,
        actions=actions,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Resolve helpers
# ---------------------------------------------------------------------------


def _resolve_device(
    client: NautobotClient,
    device_name: str,
    parsed_config: ParsedConfig,
    location: Optional[str],
    device_type: Optional[str],
    role: str,
    dry_run: bool,
) -> tuple[OnboardAction, str | None]:
    """Check if device exists, plan create or skip.

    Returns:
        Tuple of (OnboardAction, device_id or None).
    """
    try:
        existing = get_device(client, name=device_name)
        return (
            OnboardAction(
                action="skip",
                object_type="device",
                name=device_name,
                details={"id": existing.id},
                reason="Already exists in Nautobot",
            ),
            existing.id,
        )
    except NautobotNotFoundError:
        # Auto-detect device type from platform
        auto_type = device_type or _detect_device_type(parsed_config)
        return (
            OnboardAction(
                action="create",
                object_type="device",
                name=device_name,
                details={
                    "device_type": auto_type,
                    "location": location or "Unknown",
                    "role": role,
                },
                reason="Not found in Nautobot",
            ),
            None,
        )


def _detect_device_type(parsed_config: ParsedConfig) -> str:
    """Auto-detect device type from parsed config platform field."""
    platform_map = {
        "MX": "MX204",
        "EX": "EX4300",
        "SRX": "SRX345",
        "junos": "Juniper",
    }
    return platform_map.get(parsed_config.platform, "Generic")


def _resolve_interfaces(
    client: NautobotClient,
    device_name: str,
    device_id: str | None,
    parsed_config: ParsedConfig,
    dry_run: bool,
    update_existing: bool,
) -> list[OnboardAction]:
    """Compare parsed interfaces against Nautobot, plan create/update/skip."""
    actions: list[OnboardAction] = []

    for iface in parsed_config.interfaces:
        try:
            existing = get_interface(client, device_name=device_name, name=iface.name)
            # Check if update is needed
            needs_update = update_existing and (
                existing.description != iface.description
            )
            if needs_update:
                actions.append(OnboardAction(
                    action="update",
                    object_type="interface",
                    name=iface.name,
                    details={
                        "id": existing.id,
                        "description": iface.description,
                    },
                    reason="Description changed",
                ))
            else:
                actions.append(OnboardAction(
                    action="skip",
                    object_type="interface",
                    name=iface.name,
                    details={"id": existing.id},
                    reason="Already exists in Nautobot",
                ))
        except Exception:
            # NautobotNotFoundError: interface doesn't exist yet
            # Other errors (e.g. 400 when device doesn't exist): treat as not found
            iface_type = map_interface_type(iface.name)
            actions.append(OnboardAction(
                action="create",
                object_type="interface",
                name=iface.name,
                details={
                    "type": iface_type,
                    "description": iface.description,
                    "enabled": iface.enabled,
                },
                reason="Not found in Nautobot",
            ))

    return actions


def _resolve_ip_addresses(
    client: NautobotClient,
    device_name: str,
    device_id: str | None,
    parsed_config: ParsedConfig,
    namespace: str,
    dry_run: bool,
) -> list[OnboardAction]:
    """Compare parsed IPs against Nautobot, plan create/skip with auto-prefix."""
    actions: list[OnboardAction] = []

    for iface in parsed_config.interfaces:
        for unit in iface.units:
            for ip in unit.ip_addresses:
                # Auto-create prefix from IP
                try:
                    network = str(ipaddress.ip_interface(ip.address).network)
                    actions.append(OnboardAction(
                        action="create",
                        object_type="prefix",
                        name=network,
                        details={"namespace": namespace},
                        reason="Auto-created containing prefix",
                    ))
                except ValueError:
                    pass  # Invalid IP, skip prefix

                # Check if IP exists
                try:
                    existing_ip = client.api.ipam.ip_addresses.get(
                        address=ip.address,
                    )
                    if existing_ip:
                        actions.append(OnboardAction(
                            action="skip",
                            object_type="ip_address",
                            name=ip.address,
                            details={"id": str(existing_ip.id)},
                            reason="Already exists in Nautobot",
                        ))
                    else:
                        actions.append(OnboardAction(
                            action="create",
                            object_type="ip_address",
                            name=ip.address,
                            details={
                                "namespace": namespace,
                                "interface": f"{iface.name}.{unit.unit}",
                                "family": ip.family,
                            },
                            reason="Not found in Nautobot",
                        ))
                except Exception:
                    actions.append(OnboardAction(
                        action="create",
                        object_type="ip_address",
                        name=ip.address,
                        details={
                            "namespace": namespace,
                            "interface": f"{iface.name}.{unit.unit}",
                            "family": ip.family,
                        },
                        reason="Not found in Nautobot",
                    ))

    return actions


def _resolve_vlans(
    client: NautobotClient,
    parsed_config: ParsedConfig,
    dry_run: bool,
) -> list[OnboardAction]:
    """Compare parsed VLANs against Nautobot, plan create/skip."""
    actions: list[OnboardAction] = []

    for vlan in parsed_config.vlans:
        try:
            existing = client.api.ipam.vlans.get(vid=vlan.vlan_id)
            if existing:
                actions.append(OnboardAction(
                    action="skip",
                    object_type="vlan",
                    name=f"VLAN {vlan.vlan_id} ({vlan.name})",
                    details={"id": str(existing.id)},
                    reason="Already exists in Nautobot",
                ))
            else:
                actions.append(OnboardAction(
                    action="create",
                    object_type="vlan",
                    name=f"VLAN {vlan.vlan_id} ({vlan.name})",
                    details={
                        "vid": vlan.vlan_id,
                        "name": vlan.name,
                        "description": vlan.description,
                    },
                    reason="Not found in Nautobot",
                ))
        except Exception:
            actions.append(OnboardAction(
                action="create",
                object_type="vlan",
                name=f"VLAN {vlan.vlan_id} ({vlan.name})",
                details={
                    "vid": vlan.vlan_id,
                    "name": vlan.name,
                    "description": vlan.description,
                },
                reason="Not found in Nautobot",
            ))

    return actions


# ---------------------------------------------------------------------------
# Execution (commit mode)
# ---------------------------------------------------------------------------


def _execute_actions(
    client: NautobotClient,
    actions: list[OnboardAction],
    device_name: str,
    location: Optional[str],
    device_type: Optional[str],
    role: str,
    namespace: str,
) -> tuple[list[OnboardAction], OnboardSummary, list[str]]:
    """Execute planned actions in Nautobot (commit mode).

    Returns updated actions list, summary, and warnings.
    """
    executed_actions: list[OnboardAction] = []
    warnings: list[str] = []
    device_id: str | None = None

    for action in actions:
        if action.action == "skip":
            executed_actions.append(action)
            if action.object_type == "device" and action.details.get("id"):
                device_id = action.details["id"]
            continue

        try:
            if action.object_type == "device" and action.action == "create":
                result = create_device(
                    client,
                    name=device_name,
                    device_type=action.details.get("device_type", "Generic"),
                    location=action.details.get("location", "Unknown"),
                    role=action.details.get("role", role),
                )
                device_id = result.id
                action.details["id"] = result.id
                executed_actions.append(action)

            elif action.object_type == "interface" and action.action == "create":
                result = create_interface(
                    client,
                    device=device_name,
                    name=action.name,
                    type=action.details.get("type", "other"),
                    description=action.details.get("description", ""),
                )
                action.details["id"] = result.id
                executed_actions.append(action)

            elif action.object_type == "interface" and action.action == "update":
                update_interface(
                    client,
                    id=action.details["id"],
                    description=action.details.get("description", ""),
                )
                executed_actions.append(action)

            elif action.object_type == "prefix" and action.action == "create":
                try:
                    create_prefix(
                        client,
                        prefix=action.name,
                        namespace=action.details.get("namespace", namespace),
                    )
                except Exception:
                    # Prefix may already exist, that's fine
                    action = OnboardAction(
                        action="skip",
                        object_type="prefix",
                        name=action.name,
                        details=action.details,
                        reason="Already exists or auto-created",
                    )
                executed_actions.append(action)

            elif action.object_type == "ip_address" and action.action == "create":
                result = create_ip_address(
                    client,
                    address=action.name,
                    namespace=action.details.get("namespace", namespace),
                )
                action.details["id"] = result.id
                executed_actions.append(action)

            elif action.object_type == "vlan" and action.action == "create":
                result = create_vlan(
                    client,
                    vid=action.details.get("vid", 0),
                    name=action.details.get("name", ""),
                )
                action.details["id"] = result.id
                executed_actions.append(action)

            else:
                executed_actions.append(action)

        except Exception as e:
            warnings.append(f"Failed to {action.action} {action.object_type} "
                          f"'{action.name}': {e}")
            failed_action = OnboardAction(
                action="failed",
                object_type=action.object_type,
                name=action.name,
                details=action.details,
                reason=str(e),
            )
            executed_actions.append(failed_action)

    summary = OnboardSummary(
        total=len(executed_actions),
        created=sum(1 for a in executed_actions if a.action == "create"),
        updated=sum(1 for a in executed_actions if a.action == "update"),
        skipped=sum(1 for a in executed_actions if a.action == "skip"),
        failed=sum(1 for a in executed_actions if a.action == "failed"),
    )

    return executed_actions, summary, warnings
