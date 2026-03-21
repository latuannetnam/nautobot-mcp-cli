"""CMS drift verification engine.

Compares live Juniper device state (agent-provided structured data) against
Nautobot CMS model records using DiffSync for semantic comparison.

Covers:
- BGP neighbor drift (DRIFT-01): peer IP, peer AS, local address, group name
- Static route drift (DRIFT-02): destination, nexthops, preference, metric, routing instance
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from diffsync import Adapter, DiffSyncModel

from nautobot_mcp.cms.routing import list_bgp_groups, list_bgp_neighbors, list_static_routes
from nautobot_mcp.models.cms.cms_drift import CMSDriftReport
from nautobot_mcp.models.verification import DriftItem, DriftSection

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DiffSync models
# ---------------------------------------------------------------------------


class SyncBGPNeighbor(DiffSyncModel):
    """DiffSync model for BGP neighbor comparison."""

    _modelname = "bgp_neighbor"
    _identifiers = ("peer_ip",)
    _attributes = ("peer_as", "local_address", "group_name")

    peer_ip: str
    peer_as: int = 0
    local_address: str = ""
    group_name: str = ""


class SyncStaticRoute(DiffSyncModel):
    """DiffSync model for static route comparison."""

    _modelname = "static_route"
    _identifiers = ("destination",)
    _attributes = ("nexthops_str", "preference", "metric", "routing_instance")

    destination: str
    nexthops_str: str = ""  # Serialized sorted nexthop list for comparison
    preference: int = 5
    metric: int = 0
    routing_instance: str = ""


# ---------------------------------------------------------------------------
# Adapters — BGP neighbors
# ---------------------------------------------------------------------------


class LiveBGPAdapter(Adapter):
    """DiffSync adapter that loads live BGP neighbor data (agent-provided dicts)."""

    bgp_neighbor = SyncBGPNeighbor
    top_level = ["bgp_neighbor"]

    live_data: list[Any] = []

    def load(self) -> None:
        """Load live BGP neighbor data into DiffSync models."""
        for item in self.live_data:
            if not isinstance(item, dict):
                continue
            peer_ip = str(item.get("peer_ip", "") or "").strip()
            if not peer_ip:
                continue
            peer_as_raw = item.get("peer_as", 0)
            try:
                peer_as = int(peer_as_raw or 0)
            except (TypeError, ValueError):
                peer_as = 0
            self.add(SyncBGPNeighbor(
                peer_ip=peer_ip,
                peer_as=peer_as,
                local_address=str(item.get("local_address", "") or "").strip(),
                group_name=str(item.get("group_name", "") or "").strip(),
            ))


class CMSBGPAdapter(Adapter):
    """DiffSync adapter that loads BGP neighbors from Nautobot CMS."""

    bgp_neighbor = SyncBGPNeighbor
    top_level = ["bgp_neighbor"]

    client: Any = None
    device_name: str = ""

    def load(self) -> None:
        """Load Nautobot CMS BGP neighbors into DiffSync models."""
        if not self.client:
            return

        # Build group_id -> group_name map
        groups_resp = list_bgp_groups(self.client, device=self.device_name, limit=0)
        group_id_to_name: dict[str, str] = {}
        for grp in groups_resp.results:
            group_id_to_name[grp.id] = grp.name or ""

        # Load neighbors via device-scoped query
        neighbors_resp = list_bgp_neighbors(self.client, device=self.device_name, limit=0)
        for nbr in neighbors_resp.results:
            peer_ip = str(nbr.peer_ip or "").strip()
            if not peer_ip:
                continue
            # Strip CIDR mask if present (CMS stores as IP/prefix like 10.0.0.1/32)
            if "/" in peer_ip:
                peer_ip = peer_ip.split("/")[0]
            try:
                peer_as = int(nbr.peer_as or 0)
            except (TypeError, ValueError):
                peer_as = 0
            local_address = str(nbr.local_address or "").strip()
            # Strip CIDR from local_address too
            if "/" in local_address:
                local_address = local_address.split("/")[0]
            group_name = group_id_to_name.get(nbr.group_id, "")
            self.add(SyncBGPNeighbor(
                peer_ip=peer_ip,
                peer_as=peer_as,
                local_address=local_address,
                group_name=group_name,
            ))


# ---------------------------------------------------------------------------
# Adapters — static routes
# ---------------------------------------------------------------------------


def _serialize_nexthops(nexthops: list) -> str:
    """Serialize a list of nexthop IPs to a sorted comma-joined string.

    Sorts alphabetically for consistent comparison regardless of order.
    Handles bare IP strings or dicts with 'ip_address' key.
    """
    ips = []
    for nh in nexthops:
        if isinstance(nh, str):
            ip = nh.strip()
        elif isinstance(nh, dict):
            ip = str(nh.get("ip_address", nh.get("address", "")) or "").strip()
        else:
            ip = str(nh).strip()
        if "/" in ip:
            ip = ip.split("/")[0]
        if ip:
            ips.append(ip)
    return ",".join(sorted(ips))


class LiveStaticRouteAdapter(Adapter):
    """DiffSync adapter that loads live static route data (agent-provided dicts)."""

    static_route = SyncStaticRoute
    top_level = ["static_route"]

    live_data: list[Any] = []

    def load(self) -> None:
        """Load live static route data into DiffSync models."""
        for item in self.live_data:
            if not isinstance(item, dict):
                continue
            destination = str(item.get("destination", "") or "").strip()
            if not destination:
                continue
            nexthops = item.get("nexthops", [])
            if not isinstance(nexthops, list):
                nexthops = []
            nexthops_str = _serialize_nexthops(nexthops)
            try:
                preference = int(item.get("preference", 5) or 5)
            except (TypeError, ValueError):
                preference = 5
            try:
                metric = int(item.get("metric", 0) or 0)
            except (TypeError, ValueError):
                metric = 0
            routing_instance = str(item.get("routing_instance", "") or "").strip()
            self.add(SyncStaticRoute(
                destination=destination,
                nexthops_str=nexthops_str,
                preference=preference,
                metric=metric,
                routing_instance=routing_instance,
            ))


class CMSStaticRouteAdapter(Adapter):
    """DiffSync adapter that loads static routes from Nautobot CMS."""

    static_route = SyncStaticRoute
    top_level = ["static_route"]

    client: Any = None
    device_name: str = ""

    def load(self) -> None:
        """Load Nautobot CMS static routes into DiffSync models."""
        if not self.client:
            return
        routes_resp = list_static_routes(self.client, device=self.device_name, limit=0)
        for route in routes_resp.results:
            destination = str(route.destination or "").strip()
            if not destination:
                continue
            # Serialize inlined nexthops from CMS records
            nexthop_ips = [nh.ip_address for nh in (route.nexthops or []) if nh.ip_address]
            qualified_ips = [qnh.ip_address for qnh in (route.qualified_nexthops or []) if qnh.ip_address]
            all_nexthops = nexthop_ips + qualified_ips
            nexthops_str = _serialize_nexthops(all_nexthops)
            routing_instance = str(route.routing_instance_name or "").strip()
            self.add(SyncStaticRoute(
                destination=destination,
                nexthops_str=nexthops_str,
                preference=int(route.preference or 5),
                metric=int(route.metric or 0),
                routing_instance=routing_instance,
            ))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _diffsync_to_cms_drift(diff, device_name: str, section_name: str) -> CMSDriftReport:
    """Translate a DiffSync Diff object into a CMSDriftReport.

    Maps DiffSync operations:
    - "+" only → "missing_in_nautobot" (exists on device, not in Nautobot)
    - "-" only → "missing_on_device" (exists in Nautobot, not on device)
    - Both "+" and "-" → "changed" with changed_fields detail

    Args:
        diff: DiffSync Diff object.
        device_name: Device hostname.
        section_name: "bgp_neighbors" or "static_routes".

    Returns:
        CMSDriftReport with the specified section populated.
    """
    report = CMSDriftReport(
        device=device_name,
        source="provided",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    section = DriftSection()

    # Map section_name to DiffSync model name
    model_name_map = {
        "bgp_neighbors": "bgp_neighbor",
        "static_routes": "static_route",
    }
    model_key = model_name_map.get(section_name, section_name)

    diff_dict = diff.dict()
    model_diffs = diff_dict.get(model_key, {})

    for obj_key, obj_diff in model_diffs.items():
        if not isinstance(obj_diff, dict):
            continue

        # DiffSync uses "+" for source (live/device) and "-" for dest (CMS/Nautobot)
        src = obj_diff.get("+", {}) or {}   # live device value
        dst = obj_diff.get("-", {}) or {}   # CMS Nautobot value

        if src and dst:
            # Both exist but different attributes → changed
            changed_fields = {}
            all_fields = set(list(src.keys()) + list(dst.keys()))
            for field in all_fields:
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
            # Only on live device → missing in Nautobot
            section.missing.append(DriftItem(
                name=str(obj_key),
                status="missing_in_nautobot",
                device_value=src,
            ))
        elif dst and not src:
            # Only in Nautobot → extra (missing on device)
            section.extra.append(DriftItem(
                name=str(obj_key),
                status="missing_on_device",
                nautobot_value=dst,
            ))

    setattr(report, section_name, section)
    return report


def _build_cms_summary(report: CMSDriftReport) -> dict:
    """Count total drifts across bgp_neighbors and static_routes sections.

    Returns:
        Dict with total_drifts and per-type breakdown.
    """
    sections = {
        "bgp_neighbors": report.bgp_neighbors,
        "static_routes": report.static_routes,
    }
    by_type: dict = {}
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


# ---------------------------------------------------------------------------
# Public comparison functions
# ---------------------------------------------------------------------------


def compare_bgp_neighbors(
    client: NautobotClient,
    device_name: str,
    live_neighbors: list[dict],
) -> CMSDriftReport:
    """Compare live BGP neighbors against Nautobot CMS BGP model records.

    Accepts pre-fetched BGP neighbor data (e.g., from jmcp 'show bgp summary')
    and compares against Nautobot CMS records using DiffSync semantic comparison.

    Comparison fields: peer IP (identity), peer AS, local address, group name.
    Volatile fields (session state, prefix counts, flap counts) are excluded.

    Args:
        client: NautobotClient instance.
        device_name: Device hostname in Nautobot.
        live_neighbors: List of dicts, each with:
            peer_ip (str), peer_as (int), local_address (str), group_name (str).

    Returns:
        CMSDriftReport with bgp_neighbors section populated.
    """
    live_adapter = LiveBGPAdapter()
    live_adapter.live_data = live_neighbors
    live_adapter.load()

    cms_adapter = CMSBGPAdapter()
    cms_adapter.client = client
    cms_adapter.device_name = device_name
    cms_adapter.load()

    # diff_from(source): what needs to change in cms_adapter to match live_adapter
    diff = cms_adapter.diff_from(live_adapter)
    report = _diffsync_to_cms_drift(diff, device_name, "bgp_neighbors")
    report.summary = _build_cms_summary(report)
    return report


def compare_static_routes(
    client: NautobotClient,
    device_name: str,
    live_routes: list[dict],
) -> CMSDriftReport:
    """Compare live static routes against Nautobot CMS static route records.

    Accepts pre-fetched static route data (e.g., from jmcp 'show route static')
    and compares against Nautobot CMS records using DiffSync semantic comparison.

    Comparison fields: destination (identity), next-hops, preference, metric,
    routing instance. Volatile route state fields are excluded.

    Args:
        client: NautobotClient instance.
        device_name: Device hostname in Nautobot.
        live_routes: List of dicts, each with:
            destination (str), nexthops (list[str]), preference (int),
            metric (int), routing_instance (str).

    Returns:
        CMSDriftReport with static_routes section populated.
    """
    live_adapter = LiveStaticRouteAdapter()
    live_adapter.live_data = live_routes
    live_adapter.load()

    cms_adapter = CMSStaticRouteAdapter()
    cms_adapter.client = client
    cms_adapter.device_name = device_name
    cms_adapter.load()

    diff = cms_adapter.diff_from(live_adapter)
    report = _diffsync_to_cms_drift(diff, device_name, "static_routes")
    report.summary = _build_cms_summary(report)
    return report
