"""Tests for the API catalog engine.

Validates catalog completeness, domain filtering, CMS auto-discovery,
and workflow stub entries.
"""

import pytest

from nautobot_mcp.catalog.engine import get_catalog
from nautobot_mcp.catalog.core_endpoints import CORE_ENDPOINTS
from nautobot_mcp.catalog.cms_discovery import discover_cms_endpoints
from nautobot_mcp.catalog.workflow_stubs import WORKFLOW_STUBS
from nautobot_mcp.cms.client import CMS_ENDPOINTS


class TestCatalogCompleteness:
    """Test that the catalog contains all expected domains and entries."""

    def test_full_catalog_has_all_domains(self):
        """Full catalog returns all domain groups."""
        catalog = get_catalog()
        assert "dcim" in catalog
        assert "ipam" in catalog
        assert "circuits" in catalog
        assert "tenancy" in catalog
        assert "cms" in catalog
        assert "workflows" in catalog

    def test_dcim_core_endpoints(self):
        """DCIM domain has essential network automation endpoints."""
        catalog = get_catalog(domain="dcim")
        dcim = catalog["dcim"]
        assert "devices" in dcim
        assert "interfaces" in dcim
        assert "locations" in dcim

    def test_ipam_core_endpoints(self):
        """IPAM domain has IP management endpoints."""
        catalog = get_catalog(domain="ipam")
        ipam = catalog["ipam"]
        assert "ip_addresses" in ipam
        assert "prefixes" in ipam
        assert "vlans" in ipam

    def test_circuits_core_endpoints(self):
        """Circuits domain has provider and circuit endpoints."""
        catalog = get_catalog(domain="circuits")
        circuits = catalog["circuits"]
        assert "circuits" in circuits
        assert "providers" in circuits

    def test_tenancy_core_endpoints(self):
        """Tenancy domain has tenant endpoints."""
        catalog = get_catalog(domain="tenancy")
        tenancy = catalog["tenancy"]
        assert "tenants" in tenancy

    def test_endpoint_entry_has_required_fields(self):
        """Every core endpoint entry has endpoint, methods, filters, description."""
        for domain, entries in CORE_ENDPOINTS.items():
            for name, entry in entries.items():
                assert "endpoint" in entry, f"{domain}.{name} missing 'endpoint'"
                assert "methods" in entry, f"{domain}.{name} missing 'methods'"
                assert "filters" in entry, f"{domain}.{name} missing 'filters'"
                assert "description" in entry, f"{domain}.{name} missing 'description'"
                assert entry["endpoint"].startswith("/api/"), (
                    f"{domain}.{name} endpoint should start with /api/"
                )
                assert isinstance(entry["methods"], list), (
                    f"{domain}.{name} methods should be a list"
                )

    def test_no_admin_endpoints_in_catalog(self):
        """Admin-only endpoints should not appear in the curated catalog."""
        all_endpoint_names = []
        for entries in CORE_ENDPOINTS.values():
            all_endpoint_names.extend(entries.keys())
        admin_endpoints = ["object_changes", "custom_fields", "job_results", "computed_fields"]
        for admin in admin_endpoints:
            assert admin not in all_endpoint_names, (
                f"Admin endpoint '{admin}' should not be in catalog"
            )


class TestCMSDiscovery:
    """Test dynamic CMS endpoint discovery from CMS_ENDPOINTS registry."""

    def test_cms_discovery_count_matches_registry(self):
        """CMS discovery produces same count as CMS_ENDPOINTS registry."""
        cms_catalog = discover_cms_endpoints()
        total_entries = sum(len(entries) for entries in cms_catalog.values())
        assert total_entries == len(CMS_ENDPOINTS), (
            f"CMS catalog has {total_entries} entries but CMS_ENDPOINTS has {len(CMS_ENDPOINTS)}"
        )

    def test_cms_has_expected_domains(self):
        """CMS catalog groups into expected sub-domains."""
        cms_catalog = discover_cms_endpoints()
        assert "routing" in cms_catalog
        assert "interfaces" in cms_catalog
        assert "firewalls" in cms_catalog
        assert "policies" in cms_catalog
        assert "arp" in cms_catalog

    def test_cms_entries_have_required_fields(self):
        """Every CMS entry has endpoint, display_name, methods, filters, description."""
        cms_catalog = discover_cms_endpoints()
        for domain, entries in cms_catalog.items():
            for name, entry in entries.items():
                assert "endpoint" in entry, f"cms.{domain}.{name} missing 'endpoint'"
                assert "display_name" in entry, f"cms.{domain}.{name} missing 'display_name'"
                assert "methods" in entry, f"cms.{domain}.{name} missing 'methods'"
                assert entry["endpoint"].startswith("cms:"), (
                    f"cms.{domain}.{name} endpoint should start with cms:"
                )

    def test_cms_entries_use_friendly_names(self):
        """CMS display names should not contain raw underscores."""
        cms_catalog = discover_cms_endpoints()
        for domain, entries in cms_catalog.items():
            for name, entry in entries.items():
                assert "_" not in entry["display_name"], (
                    f"cms.{domain}.{name} display_name '{entry['display_name']}' contains underscore"
                )


class TestDomainFiltering:
    """Test domain filter parameter on get_catalog."""

    @pytest.mark.parametrize("domain", ["dcim", "ipam", "circuits", "tenancy"])
    def test_core_domain_filter(self, domain):
        """Filtering by core domain returns only that domain."""
        catalog = get_catalog(domain=domain)
        assert list(catalog.keys()) == [domain]

    def test_cms_domain_filter(self):
        """Filtering by cms returns CMS sub-domains."""
        catalog = get_catalog(domain="cms")
        assert list(catalog.keys()) == ["cms"]
        assert isinstance(catalog["cms"], dict)
        assert len(catalog["cms"]) > 0

    def test_workflows_domain_filter(self):
        """Filtering by workflows returns workflow stubs."""
        catalog = get_catalog(domain="workflows")
        assert list(catalog.keys()) == ["workflows"]

    def test_invalid_domain_raises_error(self):
        """Invalid domain raises ValueError with available domains."""
        with pytest.raises(ValueError, match="Unknown catalog domain"):
            get_catalog(domain="invalid")

    def test_invalid_domain_lists_available(self):
        """Error message lists available domains."""
        with pytest.raises(ValueError, match="Available domains:"):
            get_catalog(domain="nonexistent")

    def test_domain_filter_case_insensitive(self):
        """Domain filter should be case-insensitive."""
        catalog = get_catalog(domain="DCIM")
        assert "dcim" in catalog


class TestWorkflowStubs:
    """Test workflow stub entries."""

    def test_workflow_count(self):
        """All 10 workflows are registered."""
        assert len(WORKFLOW_STUBS) == 10

    def test_expected_workflows_present(self):
        """All expected workflow names are present."""
        expected = [
            "bgp_summary",
            "routing_table",
            "firewall_summary",
            "interface_detail",
            "onboard_config",
            "compare_device",
            "verify_data_model",
            "verify_compliance",
            "compare_bgp",
            "compare_routes",
        ]
        for wf in expected:
            assert wf in WORKFLOW_STUBS, f"Workflow '{wf}' missing from WORKFLOW_STUBS"

    def test_workflow_entry_has_required_fields(self):
        """Every workflow entry has params, description, and aggregates."""
        for name, entry in WORKFLOW_STUBS.items():
            assert "params" in entry, f"Workflow '{name}' missing 'params'"
            assert "description" in entry, f"Workflow '{name}' missing 'description'"
            assert "aggregates" in entry, f"Workflow '{name}' missing 'aggregates'"
            assert isinstance(entry["params"], dict), f"Workflow '{name}' params should be dict"
            assert isinstance(entry["aggregates"], list), (
                f"Workflow '{name}' aggregates should be list"
            )


class TestCMSFilterAccuracy:
    """Test that CMS endpoints advertise correct per-endpoint filters."""

    def test_filter_registry_covers_all_endpoints(self):
        """CMS_ENDPOINT_FILTERS has entry for every CMS_ENDPOINTS key."""
        from nautobot_mcp.catalog.cms_discovery import CMS_ENDPOINT_FILTERS
        for endpoint_name in CMS_ENDPOINTS:
            assert endpoint_name in CMS_ENDPOINT_FILTERS, (
                f"CMS_ENDPOINT_FILTERS missing entry for '{endpoint_name}'"
            )

    def test_bgp_neighbors_filter_is_group(self):
        """BGP neighbors should filter by group, not device."""
        cms_catalog = discover_cms_endpoints()
        bgp_neighbors = cms_catalog["routing"]["bgp_neighbors"]
        assert bgp_neighbors["filters"] == ["group"], (
            f"BGP neighbors should have ['group'] filter, got {bgp_neighbors['filters']}"
        )

    def test_firewall_terms_filter_is_firewall_filter(self):
        """Firewall terms should filter by firewall_filter, not device."""
        cms_catalog = discover_cms_endpoints()
        fw_terms = cms_catalog["firewalls"]["firewall_terms"]
        assert fw_terms["filters"] == ["firewall_filter"]

    def test_device_scoped_endpoints_have_device_filter(self):
        """Top-level endpoints that are device-scoped must have device filter."""
        from nautobot_mcp.catalog.cms_discovery import CMS_ENDPOINT_FILTERS
        device_scoped = [
            "juniper_static_routes", "juniper_bgp_groups",
            "juniper_interface_units", "juniper_firewall_filters",
            "juniper_firewall_policers", "juniper_policy_statements",
            "juniper_policy_as_paths", "juniper_policy_communities",
            "juniper_policy_prefix_lists", "juniper_arp_entries",
        ]
        for ep in device_scoped:
            assert CMS_ENDPOINT_FILTERS[ep] == ["device"], (
                f"{ep} should have ['device'] filter, got {CMS_ENDPOINT_FILTERS[ep]}"
            )

    def test_child_endpoints_do_not_have_device_filter(self):
        """Child endpoints (FK to parent) should NOT have device as filter."""
        from nautobot_mcp.catalog.cms_discovery import CMS_ENDPOINT_FILTERS
        child_endpoints = [
            "juniper_bgp_neighbors", "juniper_firewall_terms",
            "jps_terms", "juniper_policy_prefixes",
            "juniper_static_route_nexthops",
        ]
        for ep in child_endpoints:
            assert "device" not in CMS_ENDPOINT_FILTERS[ep], (
                f"{ep} should NOT have 'device' filter, got {CMS_ENDPOINT_FILTERS[ep]}"
            )

    def test_catalog_entries_have_non_empty_filters(self):
        """Every CMS catalog entry should have at least one filter."""
        cms_catalog = discover_cms_endpoints()
        for domain, entries in cms_catalog.items():
            for name, entry in entries.items():
                assert len(entry.get("filters", [])) > 0, (
                    f"cms.{domain}.{name} has empty filters list"
                )

