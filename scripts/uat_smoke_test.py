#!/usr/bin/env python3
"""UAT Smoke Test — Nautobot API Bridge.

Quick validation of the 3-tool API against a live Nautobot server.
Runs all critical paths and prints pass/fail for each check.

Usage:
  python scripts/uat_smoke_test.py
  NAUTOBOT_UAT_URL=http://custom-server python scripts/uat_smoke_test.py

Environment:
  NAUTOBOT_UAT_URL — Target server URL (default: http://101.96.85.93)
  NAUTOBOT_URL     — Override for NautobotClient (set from NAUTOBOT_UAT_URL)
  NAUTOBOT_TOKEN   — API authentication token (required)
"""
from __future__ import annotations

import os
import sys

# Ensure project root is in path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nautobot_mcp.client import NautobotClient
from nautobot_mcp.config import NautobotSettings
from nautobot_mcp.catalog.engine import get_catalog
from nautobot_mcp.bridge import call_nautobot
from nautobot_mcp.workflows import run_workflow

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

UAT_DEVICE = "HQV-PE-TestFake"
UAT_URL_DEFAULT = "http://101.96.85.93"


def _make_client() -> NautobotClient:
    """Create a NautobotClient pointing at the UAT server."""
    uat_url = os.environ.get("NAUTOBOT_UAT_URL", UAT_URL_DEFAULT)
    os.environ["NAUTOBOT_URL"] = uat_url
    settings = NautobotSettings.discover()
    return NautobotClient(settings=settings)


# -------------------------------------------------------------------------
# Test runner helpers
# -------------------------------------------------------------------------


def _run(name: str, func) -> bool:
    """Execute a test function, print result, return True on pass."""
    try:
        func()
        print(f"  ✓  {name}")
        return True
    except AssertionError as e:
        print(f"  ✗  {name}")
        print(f"       AssertionError: {e}")
        return False
    except Exception as e:
        print(f"  ✗  {name}")
        print(f"       {type(e).__name__}: {e}")
        return False


# -------------------------------------------------------------------------
# Test definitions
# -------------------------------------------------------------------------


def test_catalog_all_domains():
    """Catalog returns all expected domain keys."""
    catalog = get_catalog()
    for domain in ("dcim", "ipam", "circuits", "tenancy", "cms", "workflows"):
        assert domain in catalog, f"Missing domain: '{domain}'"


def test_catalog_workflow_stubs():
    """Catalog workflows section contains known workflow IDs."""
    catalog = get_catalog(domain="workflows")
    workflows = catalog["workflows"]
    for wf_id in ("bgp_summary", "compare_bgp", "onboard_config", "verify_compliance"):
        assert wf_id in workflows, f"Missing workflow: '{wf_id}'"


def test_bridge_get_devices(client: NautobotClient):
    """Bridge GET /api/dcim/devices/ returns a non-empty list."""
    result = call_nautobot(client, endpoint="/api/dcim/devices/", method="GET")
    assert result.get("count", 0) > 0, "Expected at least one device"
    assert len(result.get("results", [])) > 0


def test_bridge_get_specific_device(client: NautobotClient):
    """Bridge GET with name filter returns exactly the UAT device."""
    result = call_nautobot(
        client,
        endpoint="/api/dcim/devices/",
        method="GET",
        params={"name": UAT_DEVICE},
    )
    assert result.get("count") == 1, (
        f"Expected 1 device named '{UAT_DEVICE}', got {result.get('count')}"
    )
    assert result["results"][0]["name"] == UAT_DEVICE


def test_bridge_get_cms_bgp_groups(client: NautobotClient):
    """Bridge GET CMS BGP groups returns a results list."""
    result = call_nautobot(
        client,
        endpoint="cms:juniper_bgp_groups",
        method="GET",
        params={"device": UAT_DEVICE},
    )
    assert "results" in result, "Expected 'results' key in CMS response"


def test_workflow_bgp_summary(client: NautobotClient):
    """bgp_summary workflow returns ok envelope."""
    result = run_workflow(client, workflow_id="bgp_summary", params={"device": UAT_DEVICE})
    assert result["status"] == "ok", f"bgp_summary failed: {result.get('error')}"
    assert result["workflow"] == "bgp_summary"


def test_workflow_routing_table(client: NautobotClient):
    """routing_table workflow returns ok envelope."""
    result = run_workflow(client, workflow_id="routing_table", params={"device": UAT_DEVICE})
    assert result["status"] == "ok", f"routing_table failed: {result.get('error')}"


def test_workflow_firewall_summary(client: NautobotClient):
    """firewall_summary workflow returns ok envelope."""
    result = run_workflow(client, workflow_id="firewall_summary", params={"device": UAT_DEVICE})
    assert result["status"] == "ok", f"firewall_summary failed: {result.get('error')}"


def test_workflow_onboard_dry_run(client: NautobotClient):
    """onboard_config with dry_run=True returns ok without writing data."""
    minimal_config = {
        "device_name": UAT_DEVICE,
        "location": "HQV",
        "role": "Router",
        "manufacturer": "Juniper",
        "device_type": "MX960",
        "serial": "",
        "interfaces": [],
        "ip_addresses": [],
        "vlans": [],
    }
    result = run_workflow(
        client,
        workflow_id="onboard_config",
        params={
            "config_data": minimal_config,
            "device_name": UAT_DEVICE,
            "dry_run": True,
        },
    )
    assert result["status"] == "ok", f"onboard dry-run failed: {result.get('error')}"


# -------------------------------------------------------------------------
# Main runner
# -------------------------------------------------------------------------


def run_tests() -> None:
    """Run all UAT smoke tests and print a summary."""
    uat_url = os.environ.get("NAUTOBOT_UAT_URL", UAT_URL_DEFAULT)

    print(f"\n{'=' * 60}")
    print(f"  Nautobot API Bridge — UAT Smoke Test")
    print(f"  Server : {uat_url}")
    print(f"  Device : {UAT_DEVICE}")
    print(f"{'=' * 60}\n")

    # Client-free tests (catalog does not need network)
    print("[ Catalog Tests ]")
    catalog_results = [
        _run("catalog returns all domains", test_catalog_all_domains),
        _run("catalog has known workflow stubs", test_catalog_workflow_stubs),
    ]

    # Client-dependent tests
    print("\nConnecting to server...")
    try:
        client = _make_client()
    except Exception as exc:
        print(f"  ✗  Cannot create client: {exc}")
        sys.exit(1)

    print("\n[ Bridge Tests ]")
    bridge_results = [
        _run("GET /api/dcim/devices/ non-empty", lambda: test_bridge_get_devices(client)),
        _run(f"GET devices?name={UAT_DEVICE}", lambda: test_bridge_get_specific_device(client)),
        _run("GET cms:juniper_bgp_groups", lambda: test_bridge_get_cms_bgp_groups(client)),
    ]

    print("\n[ Workflow Tests ]")
    workflow_results = [
        _run("bgp_summary workflow", lambda: test_workflow_bgp_summary(client)),
        _run("routing_table workflow", lambda: test_workflow_routing_table(client)),
        _run("firewall_summary workflow", lambda: test_workflow_firewall_summary(client)),
        _run("onboard_config dry-run", lambda: test_workflow_onboard_dry_run(client)),
    ]

    all_results = catalog_results + bridge_results + workflow_results
    passed = sum(all_results)
    failed = len(all_results) - passed

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed  ({len(all_results)} total)")
    print(f"{'=' * 60}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_tests()
