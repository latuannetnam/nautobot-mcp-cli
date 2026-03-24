"""UAT smoke tests against live Nautobot dev server.

These tests hit the REAL Nautobot server and require:
- Network access to the UAT server
- Valid API token configured (NAUTOBOT_URL + NAUTOBOT_TOKEN env vars)

Run with: pytest tests/test_uat.py -m live -v
Skip during normal test runs: pytest tests/ -m "not live"
"""
from __future__ import annotations

import os

import pytest

from nautobot_mcp.client import NautobotClient
from nautobot_mcp.config import NautobotSettings
from nautobot_mcp.catalog.engine import get_catalog
from nautobot_mcp.bridge import call_nautobot
from nautobot_mcp.workflows import run_workflow

# All tests in this module require live server access
pytestmark = pytest.mark.live

# UAT constants
UAT_DEVICE = "HQV-PE-TestFake"
UAT_URL_DEFAULT = "http://101.96.85.93"


@pytest.fixture(scope="module")
def live_client():
    """Create a real NautobotClient for UAT tests.

    Reads NAUTOBOT_URL (overridden to NAUTOBOT_UAT_URL if set) and
    NAUTOBOT_TOKEN from the environment.
    """
    uat_url = os.environ.get("NAUTOBOT_UAT_URL", UAT_URL_DEFAULT)
    # Always override URL with UAT target
    os.environ.setdefault("NAUTOBOT_URL", uat_url)
    os.environ["NAUTOBOT_URL"] = uat_url
    settings = NautobotSettings.discover()
    return NautobotClient(settings=settings)


# ---------------------------------------------------------------------------
# Catalog UAT (TST-07)
# ---------------------------------------------------------------------------


class TestCatalogUAT:
    """Verify nautobot_api_catalog returns correct domain structure."""

    def test_catalog_returns_all_domains(self):
        """Full catalog contains all expected domain keys."""
        catalog = get_catalog()
        assert isinstance(catalog, dict)
        # Core domains must be present
        for domain in ("dcim", "ipam", "circuits", "tenancy"):
            assert domain in catalog, f"Expected domain '{domain}' in catalog"
        # CMS and workflows must be present
        assert "cms" in catalog, "Expected 'cms' domain in catalog"
        assert "workflows" in catalog, "Expected 'workflows' domain in catalog"

    def test_catalog_domain_filter_dcim(self):
        """Filtering by 'dcim' returns only dcim entries."""
        catalog = get_catalog(domain="dcim")
        assert isinstance(catalog, dict)
        assert "dcim" in catalog
        assert len(catalog) == 1, "Filtered catalog should contain exactly one domain"

    def test_catalog_has_workflows(self):
        """Workflows section is non-empty and contains known workflow IDs."""
        catalog = get_catalog(domain="workflows")
        assert "workflows" in catalog
        workflows = catalog["workflows"]
        assert len(workflows) > 0, "Workflow stubs should be non-empty"
        # Check a few well-known workflow IDs are present
        for wf_id in ("bgp_summary", "compare_bgp", "onboard_config"):
            assert wf_id in workflows, f"Expected workflow '{wf_id}' in catalog"


# ---------------------------------------------------------------------------
# Bridge UAT (TST-08)
# ---------------------------------------------------------------------------


class TestBridgeUAT:
    """Verify nautobot_call_nautobot routes and returns correct data from live server."""

    def test_get_devices(self, live_client):
        """GET /api/dcim/devices/ returns a non-empty list."""
        result = call_nautobot(live_client, endpoint="/api/dcim/devices/", method="GET")
        assert isinstance(result, dict)
        assert result["method"] == "GET"
        assert result["endpoint"] == "/api/dcim/devices/"
        assert result.get("count", 0) > 0, "Expected at least one device in Nautobot"
        assert isinstance(result.get("results"), list)
        assert len(result["results"]) > 0

    def test_get_specific_device(self, live_client):
        """GET with name filter returns exactly the UAT device."""
        result = call_nautobot(
            live_client,
            endpoint="/api/dcim/devices/",
            method="GET",
            params={"name": UAT_DEVICE},
        )
        assert result.get("count") == 1, (
            f"Expected exactly 1 device named '{UAT_DEVICE}', "
            f"got {result.get('count')}"
        )
        device = result["results"][0]
        assert device["name"] == UAT_DEVICE

    def test_get_cms_bgp_groups(self, live_client):
        """GET CMS BGP groups endpoint returns ok for UAT device."""
        result = call_nautobot(
            live_client,
            endpoint="cms:juniper_bgp_groups",
            method="GET",
            params={"device": UAT_DEVICE},
        )
        assert isinstance(result, dict)
        assert "results" in result, "Expected 'results' key in CMS response"


# ---------------------------------------------------------------------------
# Workflow UAT (TST-06)
# ---------------------------------------------------------------------------


class TestWorkflowUAT:
    """Verify nautobot_run_workflow dispatches and returns correct envelopes."""

    def test_bgp_summary_workflow(self, live_client):
        """bgp_summary workflow returns ok envelope with device set."""
        result = run_workflow(
            live_client,
            workflow_id="bgp_summary",
            params={"device": UAT_DEVICE},
        )
        assert result["workflow"] == "bgp_summary"
        assert result["status"] == "ok", f"Workflow failed: {result.get('error')}"
        assert result["device"] == UAT_DEVICE
        assert result.get("error") is None

    def test_routing_table_workflow(self, live_client):
        """routing_table workflow returns ok envelope."""
        result = run_workflow(
            live_client,
            workflow_id="routing_table",
            params={"device": UAT_DEVICE},
        )
        assert result["workflow"] == "routing_table"
        assert result["status"] == "ok", f"Workflow failed: {result.get('error')}"

    def test_firewall_summary_workflow(self, live_client):
        """firewall_summary workflow returns ok envelope."""
        result = run_workflow(
            live_client,
            workflow_id="firewall_summary",
            params={"device": UAT_DEVICE},
        )
        assert result["workflow"] == "firewall_summary"
        assert result["status"] == "ok", f"Workflow failed: {result.get('error')}"

    def test_interface_detail_workflow(self, live_client):
        """interface_detail workflow returns ok envelope."""
        result = run_workflow(
            live_client,
            workflow_id="interface_detail",
            params={"device": UAT_DEVICE},
        )
        assert result["workflow"] == "interface_detail"
        assert result["status"] == "ok", f"Workflow failed: {result.get('error')}"


# ---------------------------------------------------------------------------
# Idempotent Write UAT (TST-06)
# ---------------------------------------------------------------------------


class TestIdempotentWriteUAT:
    """Verify write workflows are safe to run with dry_run=True."""

    def test_onboard_config_dry_run(self, live_client):
        """onboard_config with dry_run=True returns ok without writing data."""
        # Minimal valid ParsedConfig dict — all optional lists empty
        minimal_config: dict = {
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
            live_client,
            workflow_id="onboard_config",
            params={
                "config_data": minimal_config,
                "device_name": UAT_DEVICE,
                "dry_run": True,
            },
        )
        assert result["workflow"] == "onboard_config"
        assert result["status"] == "ok", (
            f"Dry-run onboard failed: {result.get('error')}"
        )
        assert result["device"] == UAT_DEVICE
