"""Tests for the Workflow Registry and dispatch engine.

Validates:
- Registry keys match WORKFLOW_STUBS keys (sync guard)
- run_workflow() validates unknown workflow IDs
- run_workflow() validates required params
- run_workflow() maps agent-facing param names to function args
- run_workflow() returns standard response envelope
- Transforms are applied (config_data -> ParsedConfig)
- Successful dispatches return status='ok' envelopes
- Failed dispatches return status='error' with original exception message
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from nautobot_mcp.catalog.workflow_stubs import WORKFLOW_STUBS
from nautobot_mcp.exceptions import NautobotValidationError
from nautobot_mcp.workflows import WORKFLOW_REGISTRY, _build_envelope, _serialize_result, run_workflow


# ---------------------------------------------------------------------------
# Registry sync guard
# ---------------------------------------------------------------------------


class TestRegistryMatchesStubs:
    """Ensure WORKFLOW_REGISTRY and WORKFLOW_STUBS stay in sync."""

    def test_registry_keys_match_stubs(self):
        """WORKFLOW_REGISTRY must expose same IDs as WORKFLOW_STUBS."""
        assert set(WORKFLOW_REGISTRY.keys()) == set(WORKFLOW_STUBS.keys()), (
            f"Registry/Stubs mismatch!\n"
            f"  Registry only: {set(WORKFLOW_REGISTRY.keys()) - set(WORKFLOW_STUBS.keys())}\n"
            f"  Stubs only:    {set(WORKFLOW_STUBS.keys()) - set(WORKFLOW_REGISTRY.keys())}"
        )

    def test_registry_has_ten_entries(self):
        """Should have exactly 10 workflow entries."""
        assert len(WORKFLOW_REGISTRY) == 10

    def test_all_registry_entries_have_function(self):
        """Every entry must have a callable 'function'."""
        for wf_id, entry in WORKFLOW_REGISTRY.items():
            assert "function" in entry, f"{wf_id}: missing 'function' key"
            assert callable(entry["function"]), f"{wf_id}: 'function' is not callable"

    def test_all_registry_entries_have_required(self):
        """Every entry must have a 'required' list."""
        for wf_id, entry in WORKFLOW_REGISTRY.items():
            assert "required" in entry, f"{wf_id}: missing 'required' key"
            assert isinstance(entry["required"], list), f"{wf_id}: 'required' must be a list"

    def test_all_registry_entries_have_param_map(self):
        """Every entry must have a 'param_map' dict."""
        for wf_id, entry in WORKFLOW_REGISTRY.items():
            assert "param_map" in entry, f"{wf_id}: missing 'param_map' key"
            assert isinstance(entry["param_map"], dict), f"{wf_id}: 'param_map' must be a dict"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextmanager
def workflow_func_mock(workflow_id: str, return_value=None):
    """Context manager that temporarily replaces a registry entry's function with a mock.

    Because WORKFLOW_REGISTRY functions are bound at import time, we cannot use
    @patch('nautobot_mcp.workflows.func_name') — the registry already holds the
    original reference. Instead, we temporarily swap the registry slot.
    """
    mock_func = MagicMock(return_value=return_value)
    original = WORKFLOW_REGISTRY[workflow_id]["function"]
    WORKFLOW_REGISTRY[workflow_id]["function"] = mock_func
    try:
        yield mock_func
    finally:
        WORKFLOW_REGISTRY[workflow_id]["function"] = original


# ---------------------------------------------------------------------------
# run_workflow — validation
# ---------------------------------------------------------------------------


class TestRunWorkflowValidation:
    """Test parameter validation in run_workflow()."""

    def test_unknown_workflow_raises_validation_error(self):
        """Unknown workflow_id should raise NautobotValidationError."""
        client = MagicMock()
        with pytest.raises(NautobotValidationError, match="Unknown workflow"):
            run_workflow(client, workflow_id="nonexistent_workflow", params={"device": "rtr-01"})

    def test_missing_required_param_raises_validation_error(self):
        """Missing required params should raise NautobotValidationError."""
        client = MagicMock()
        with pytest.raises(NautobotValidationError, match="missing required params"):
            run_workflow(client, workflow_id="bgp_summary", params={})

    def test_missing_multiple_required_params(self):
        """Multiple missing params should raise validation error."""
        client = MagicMock()
        with pytest.raises(NautobotValidationError, match="missing required params"):
            run_workflow(client, workflow_id="compare_device", params={})

    def test_error_msg_lists_available_workflows(self):
        """Unknown workflow error should list available workflow IDs."""
        client = MagicMock()
        with pytest.raises(NautobotValidationError, match="bgp_summary"):
            run_workflow(client, workflow_id="bad_id", params={})


# ---------------------------------------------------------------------------
# run_workflow — dispatch
# ---------------------------------------------------------------------------


class TestRunWorkflowDispatch:
    """Test dispatch, param mapping, and envelope generation."""

    def test_bgp_summary_dispatches_correctly(self):
        """bgp_summary workflow should call the registry function with device param."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"groups": [], "neighbors": []}

        with workflow_func_mock("bgp_summary", return_value=mock_result) as mock_func:
            client = MagicMock()
            result = run_workflow(client, workflow_id="bgp_summary", params={"device": "core-rtr-01"})

            mock_func.assert_called_once_with(client, device="core-rtr-01")
            assert result["status"] == "ok"
            assert result["workflow"] == "bgp_summary"
            assert result["device"] == "core-rtr-01"
            assert result["data"] == {"groups": [], "neighbors": []}

    def test_routing_table_dispatches_correctly(self):
        """routing_table workflow should call registry function with device param."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"routes": []}

        with workflow_func_mock("routing_table", return_value=mock_result) as mock_func:
            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="routing_table",
                params={"device": "core-rtr-01", "detail": True},
            )
            mock_func.assert_called_once_with(client, device="core-rtr-01", detail=True)
            assert result["status"] == "ok"
            assert result["workflow"] == "routing_table"

    def test_firewall_summary_dispatches_correctly(self):
        """firewall_summary workflow should call registry function with device param."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"filters": []}

        with workflow_func_mock("firewall_summary", return_value=mock_result) as mock_func:
            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="firewall_summary",
                params={"device": "fw-01"},
            )
            mock_func.assert_called_once_with(client, device="fw-01")
            assert result["status"] == "ok"

    def test_interface_detail_dispatches_correctly(self):
        """interface_detail workflow should call registry function with device param."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"interfaces": []}

        with workflow_func_mock("interface_detail", return_value=mock_result) as mock_func:
            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="interface_detail",
                params={"device": "rtr-01", "include_arp": True},
            )
            mock_func.assert_called_once_with(client, device="rtr-01", include_arp=True)
            assert result["status"] == "ok"

    def test_compare_bgp_dispatches_correctly(self):
        """compare_bgp workflow maps device_name and live_neighbors correctly."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"bgp_neighbors": {}}

        with workflow_func_mock("compare_bgp", return_value=mock_result) as mock_func:
            client = MagicMock()
            live_neighbors = [{"peer_ip": "10.0.0.1", "peer_as": 65001}]
            result = run_workflow(
                client,
                workflow_id="compare_bgp",
                params={"device_name": "rtr-01", "live_neighbors": live_neighbors},
            )
            mock_func.assert_called_once_with(
                client, device_name="rtr-01", live_neighbors=live_neighbors
            )
            assert result["status"] == "ok"
            assert result["device"] == "rtr-01"

    def test_compare_routes_dispatches_correctly(self):
        """compare_routes workflow maps device_name and live_routes correctly."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"static_routes": {}}

        with workflow_func_mock("compare_routes", return_value=mock_result) as mock_func:
            client = MagicMock()
            live_routes = [{"destination": "0.0.0.0/0", "nexthops": ["10.0.0.1"]}]
            result = run_workflow(
                client,
                workflow_id="compare_routes",
                params={"device_name": "rtr-01", "live_routes": live_routes},
            )
            mock_func.assert_called_once_with(
                client, device_name="rtr-01", live_routes=live_routes
            )
            assert result["status"] == "ok"

    def test_verify_compliance_dispatches_correctly(self):
        """verify_compliance workflow calls the registry function with device_name."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"config_compliance": {}}

        with workflow_func_mock("verify_compliance", return_value=mock_result) as mock_func:
            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="verify_compliance",
                params={"device_name": "rtr-01"},
            )
            mock_func.assert_called_once_with(client, device_name="rtr-01")
            assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# run_workflow — transform
# ---------------------------------------------------------------------------


class TestRunWorkflowTransforms:
    """Test parameter transform logic (config_data -> ParsedConfig)."""

    @patch("nautobot_mcp.workflows.ParsedConfig")
    def test_onboard_config_transforms_config_data(self, mock_parsed_cls):
        """parsed_config dict should be transformed to ParsedConfig before dispatch."""
        config_dict = {
            "hostname": "test-rtr",
            "platform": "junos",
            "interfaces": [],
            "vlans": [],
        }
        mock_parsed = MagicMock()
        mock_parsed_cls.model_validate.return_value = mock_parsed

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"actions": []}

        with workflow_func_mock("onboard_config", return_value=mock_result) as mock_func:
            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="onboard_config",
                params={
                    "parsed_config": config_dict,
                    "device_name": "test-rtr",
                    "dry_run": True,
                },
            )

            # ParsedConfig.model_validate should have been called with config_dict
            mock_parsed_cls.model_validate.assert_called_once_with(config_dict)
            # onboard_config gets the transformed ParsedConfig object
            mock_func.assert_called_once_with(
                client,
                parsed_config=mock_parsed,
                device_name="test-rtr",
                dry_run=True,
            )
            assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# run_workflow — error handling
# ---------------------------------------------------------------------------


class TestRunWorkflowErrors:
    """Test envelope error handling."""

    def test_workflow_function_exception_returns_error_envelope(self):
        """If the workflow function raises, envelope should have status=error."""
        with workflow_func_mock("bgp_summary") as mock_func:
            mock_func.side_effect = RuntimeError("network timeout")

            client = MagicMock()
            result = run_workflow(
                client, workflow_id="bgp_summary", params={"device": "rtr-01"}
            )

        assert result["status"] == "error"
        assert result["data"] is None
        assert "network timeout" in result["error"]
        assert result["workflow"] == "bgp_summary"

    def test_unknown_workflow_does_not_return_envelope(self):
        """Unknown workflows raise NautobotValidationError (not envelope)."""
        client = MagicMock()
        with pytest.raises(NautobotValidationError):
            run_workflow(client, workflow_id="bad_workflow", params={"device": "x"})


# ---------------------------------------------------------------------------
# _serialize_result
# ---------------------------------------------------------------------------


class TestSerializeResult:
    """Test serialization helpers."""

    def test_serialize_pydantic_model(self):
        """Pydantic model with model_dump should be serialized."""
        mock_model = MagicMock()
        mock_model.model_dump.return_value = {"key": "value"}
        result = _serialize_result(mock_model)
        assert result == {"key": "value"}

    def test_serialize_dict_passthrough(self):
        """Dict should pass through without modification."""
        d = {"count": 5, "items": [1, 2, 3]}
        assert _serialize_result(d) == d

    def test_serialize_list(self):
        """List items should each be serialized."""
        mock1 = MagicMock()
        mock1.model_dump.return_value = {"a": 1}
        result = _serialize_result([mock1])
        assert result == [{"a": 1}]

    def test_serialize_unknown_falls_back_to_str(self):
        """Unknown types should fall back to str()."""

        class Weird:
            def __str__(self):
                return "weird_value"

        result = _serialize_result(Weird())
        assert result == "weird_value"


# ---------------------------------------------------------------------------
# _build_envelope
# ---------------------------------------------------------------------------


class TestBuildEnvelope:
    """Test envelope structure."""

    def test_ok_envelope_structure(self):
        """Successful envelope should have correct fields."""
        env = _build_envelope("bgp_summary", {"device": "rtr-01"}, data={"x": 1})
        assert env["workflow"] == "bgp_summary"
        assert env["device"] == "rtr-01"
        assert env["status"] == "ok"
        assert env["data"] == {"x": 1}
        assert env["error"] is None
        assert "timestamp" in env

    def test_error_envelope_structure(self):
        """Error envelope should have status=error and error message."""
        err = RuntimeError("connection refused")
        env = _build_envelope("bgp_summary", {"device": "rtr-01"}, error=err)
        assert env["status"] == "error"
        assert env["data"] is None
        assert "connection refused" in env["error"]

    def test_device_name_param_used_when_no_device(self):
        """Envelope should extract device_name if device param not present."""
        env = _build_envelope("compare_device", {"device_name": "rtr-01"}, data={})
        assert env["device"] == "rtr-01"


# ---------------------------------------------------------------------------
# WarningCollector
# ---------------------------------------------------------------------------


from nautobot_mcp.warnings import WarningCollector  # noqa: E402


class TestWarningCollector:
    """Test WarningCollector accumulation and summary."""

    def test_empty_collector_has_no_warnings(self):
        c = WarningCollector()
        assert c.warnings == []
        assert c.has_warnings is False

    def test_add_warning(self):
        c = WarningCollector()
        c.add("list_bgp_address_families", "404 Not Found")
        assert len(c.warnings) == 1
        assert c.warnings[0] == {"operation": "list_bgp_address_families", "error": "404 Not Found"}
        assert c.has_warnings is True

    def test_multiple_warnings_accumulated(self):
        c = WarningCollector()
        c.add("op1", "err1")
        c.add("op2", "err2")
        assert len(c.warnings) == 2

    def test_summary_message(self):
        c = WarningCollector()
        c.add("op1", "err1")
        c.add("op2", "err2")
        assert c.summary(4) == "2 of 4 enrichment queries failed"

    def test_warnings_returns_copy(self):
        c = WarningCollector()
        c.add("op1", "err1")
        copy = c.warnings
        copy.append({"operation": "fake", "error": "injected"})
        assert len(c.warnings) == 1  # original unchanged


# ---------------------------------------------------------------------------
# _build_envelope -- three-tier status (partial)
# ---------------------------------------------------------------------------


class TestBuildEnvelopePartial:
    """Test three-tier status in _build_envelope."""

    def test_ok_envelope_has_empty_warnings(self):
        env = _build_envelope("bgp_summary", {"device": "rtr-01"}, data={"x": 1})
        assert env["status"] == "ok"
        assert env["warnings"] == []
        assert env["error"] is None

    def test_partial_envelope_with_warnings(self):
        warnings = [{"operation": "list_af", "error": "timeout"}]
        env = _build_envelope(
            "bgp_summary",
            {"device": "rtr-01"},
            data={"x": 1},
            warnings=warnings,
            error="1 enrichment queries failed",
        )
        assert env["status"] == "partial"
        assert env["warnings"] == warnings
        assert "1 enrichment" in env["error"]

    def test_error_envelope_has_empty_warnings(self):
        err = RuntimeError("connection refused")
        env = _build_envelope("bgp_summary", {"device": "rtr-01"}, error=err)
        assert env["status"] == "error"
        assert env["warnings"] == []


# ---------------------------------------------------------------------------
# run_workflow -- partial failure tuple unpacking
# ---------------------------------------------------------------------------


class TestRunWorkflowPartial:
    """Test run_workflow with partial failure tuples."""

    def test_tuple_result_with_no_warnings_returns_ok(self):
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"groups": []}
        with workflow_func_mock("bgp_summary", return_value=(mock_result, [])):
            client = MagicMock()
            result = run_workflow(client, workflow_id="bgp_summary", params={"device": "rtr-01"})
            assert result["status"] == "ok"
            assert result["warnings"] == []

    def test_tuple_result_with_warnings_returns_partial(self):
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"groups": []}
        w = [{"operation": "list_af", "error": "timeout"}]
        with workflow_func_mock("bgp_summary", return_value=(mock_result, w)):
            client = MagicMock()
            result = run_workflow(client, workflow_id="bgp_summary", params={"device": "rtr-01"})
            assert result["status"] == "partial"
            assert result["warnings"] == w
            assert "enrichment" in result["error"]

    def test_bare_result_backward_compatible(self):
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"groups": []}
        with workflow_func_mock("bgp_summary", return_value=mock_result):
            client = MagicMock()
            result = run_workflow(client, workflow_id="bgp_summary", params={"device": "rtr-01"})
            assert result["status"] == "ok"
            assert result["warnings"] == []


# ---------------------------------------------------------------------------
# WFC-03: Registry self-check (import-time signature validation)
# ---------------------------------------------------------------------------


class TestRegistrySelfCheck:
    """Test _validate_registry() import-time signature validation (WFC-03)."""

    def test_validate_registry_passes_for_correct_entry(self):
        """verify_data_model entry should pass validation after WFC-01/WFC-02 fixes."""
        # _validate_registry() is called at module import time.
        # If this import succeeds, the self-check passed.
        # (NautobotValidationError raised at import time = test fails)
        import nautobot_mcp.workflows  # noqa: F401
        assert True  # import succeeded = no validation error

    def test_validate_registry_catches_missing_required(self):
        """Entry with required param not in function signature raises NautobotValidationError."""
        from nautobot_mcp.exceptions import NautobotValidationError
        import inspect

        # Temporarily break an entry to trigger the check
        # We use onboard_config (has a valid function) but add a fake required param
        from nautobot_mcp import workflows as wf_module
        import copy

        original = wf_module.WORKFLOW_REGISTRY["onboard_config"].copy()
        wf_module.WORKFLOW_REGISTRY["onboard_config"]["required"] = ["fake_missing_param"]
        # Also need param_map entry so it's in registry_params
        wf_module.WORKFLOW_REGISTRY["onboard_config"]["param_map"]["fake_missing_param"] = "fake_missing_param"

        try:
            with pytest.raises(NautobotValidationError, match="fake_missing_param"):
                wf_module._validate_registry()
        finally:
            wf_module.WORKFLOW_REGISTRY["onboard_config"] = original

    def test_validate_registry_catches_extra_func_param(self):
        """Entry where function accepts param not listed in required or param_map raises."""
        from nautobot_mcp.exceptions import NautobotValidationError
        from nautobot_mcp import workflows as wf_module

        original = wf_module.WORKFLOW_REGISTRY["bgp_summary"].copy()
        # bgp_summary function: get_device_bgp_summary(client, device, detail=None)
        # Add 'fake_extra' as required — not in function signature
        wf_module.WORKFLOW_REGISTRY["bgp_summary"]["required"] = ["device", "fake_extra"]

        try:
            with pytest.raises(NautobotValidationError, match="fake_extra"):
                wf_module._validate_registry()
        finally:
            wf_module.WORKFLOW_REGISTRY["bgp_summary"] = original


# ---------------------------------------------------------------------------
# verify_data_model transform test
# ---------------------------------------------------------------------------


class TestVerifyDataModelTransform:
    """Test that verify_data_model applies ParsedConfig.model_validate transform."""

    def test_verify_data_model_transforms_parsed_config(self):
        """parsed_config dict should be transformed to ParsedConfig via model_validate."""
        from nautobot_mcp.workflows import run_workflow, WORKFLOW_REGISTRY
        from nautobot_mcp.models.parser import ParsedConfig

        config_dict = {
            "hostname": "test-rtr",
            "platform": "junos",
            "interfaces": [],
            "ip_addresses": [],
            "vlans": [],
            "routing_instances": [],
            "protocols": [],
            "firewall_filters": [],
        }

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"interfaces": [], "ip_addresses": [], "vlans": []}

        # Save original
        orig = WORKFLOW_REGISTRY["verify_data_model"]["function"]

        def fake_verify(client, device_name, parsed_config):
            # parsed_config should be a ParsedConfig instance after transform
            assert isinstance(parsed_config, ParsedConfig)
            return mock_result

        WORKFLOW_REGISTRY["verify_data_model"]["function"] = fake_verify
        try:
            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="verify_data_model",
                params={"device_name": "test-rtr", "parsed_config": config_dict},
            )
            assert result["status"] == "ok"
        finally:
            WORKFLOW_REGISTRY["verify_data_model"]["function"] = orig


# ---------------------------------------------------------------------------
# ERR-03: Composite workflow exception -> warning entry in envelope
# ---------------------------------------------------------------------------


class TestRunWorkflowCompositeErrorOrigin:
    """Test that workflow exceptions surface as warning entries with origin field (ERR-03)."""

    def test_workflow_exception_includes_operation_in_warnings(self):
        """Exception from a workflow should appear in warnings with 'operation' key."""
        with workflow_func_mock("bgp_summary") as mock_func:
            mock_func.side_effect = RuntimeError("Nautobot API timeout during BGP query")

            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="bgp_summary",
                params={"device": "rtr-01"},
            )

        # ERR-03: envelope must have status=error (no data) AND warnings list with the exception
        assert result["status"] == "error"
        assert result["data"] is None
        assert "warnings" in result
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["operation"] == "bgp_summary"
        assert "Nautobot API timeout" in result["warnings"][0]["error"]

    def test_routing_table_exception_includes_operation_origin(self):
        """routing_table exception should include 'routing_table' as operation in warnings."""
        with workflow_func_mock("routing_table") as mock_func:
            mock_func.side_effect = ValueError("Invalid route data format")

            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="routing_table",
                params={"device": "rtr-01"},
            )

        assert result["status"] == "error"
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["operation"] == "routing_table"
        assert "Invalid route" in result["warnings"][0]["error"]

    def test_firewall_summary_exception_includes_operation_origin(self):
        """firewall_summary exception should include 'firewall_summary' as operation."""
        with workflow_func_mock("firewall_summary") as mock_func:
            mock_func.side_effect = Exception("Device not found in Nautobot")

            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="firewall_summary",
                params={"device": "fw-01"},
            )

        assert result["status"] == "error"
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["operation"] == "firewall_summary"
        assert "warnings" in result
        assert isinstance(result["warnings"], list)

    def test_interface_detail_exception_includes_operation_origin(self):
        """interface_detail exception should include 'interface_detail' as operation."""
        with workflow_func_mock("interface_detail") as mock_func:
            mock_func.side_effect = ConnectionError("Cannot reach Nautobot")

            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="interface_detail",
                params={"device": "dist-sw-01"},
            )

        assert result["status"] == "error"
        assert result["warnings"][0]["operation"] == "interface_detail"
        assert "Cannot reach Nautobot" in result["warnings"][0]["error"]

    def test_verify_data_model_exception_includes_operation_origin(self):
        """verify_data_model exception should include 'verify_data_model' as operation."""
        from nautobot_mcp.models.parser import ParsedConfig

        with workflow_func_mock("verify_data_model") as mock_func:
            mock_func.side_effect = RuntimeError("DiffSync comparison failed")

            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="verify_data_model",
                params={
                    "device_name": "test-rtr",
                    "parsed_config": {
                        "hostname": "test",
                        "platform": "junos",
                        "interfaces": [],
                        "ip_addresses": [],
                        "vlans": [],
                        "routing_instances": [],
                        "protocols": [],
                        "firewall_filters": [],
                    },
                },
            )

        assert result["status"] == "error"
        assert result["warnings"][0]["operation"] == "verify_data_model"
        assert "DiffSync comparison failed" in result["warnings"][0]["error"]

    def test_error_string_still_present_in_envelope(self):
        """Exception string should still appear in the 'error' field for backward compat."""
        with workflow_func_mock("bgp_summary") as mock_func:
            mock_func.side_effect = RuntimeError("connection refused")

            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="bgp_summary",
                params={"device": "rtr-01"},
            )

        assert result["error"] is not None
        assert "connection refused" in result["error"]
        # Also present in warnings
        assert "connection refused" in result["warnings"][0]["error"]

    def test_partial_failure_from_composite_still_returns_partial_not_error(self):
        """Phase 19 partial failures (tuple return with warnings) remain unchanged by ERR-03.

        This test ensures the Phase 19 behavior is preserved: composite functions that
        return (result, warnings) tuples still get status='partial', not status='error'.
        ERR-03 only modifies the except Exception handler.
        """
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"groups": ["core"]}
        warnings_from_composite = [
            {"operation": "list_bgp_address_families", "error": "404 Not Found"},
        ]
        with workflow_func_mock("bgp_summary", return_value=(mock_result, warnings_from_composite)):
            client = MagicMock()
            result = run_workflow(
                client,
                workflow_id="bgp_summary",
                params={"device": "rtr-01"},
            )

        # Phase 19 behavior: partial envelope (not error)
        assert result["status"] == "partial"
        assert result["data"] is not None
        assert result["warnings"] == warnings_from_composite
        # Error field contains summary string (not exception)
        assert "enrichment" in result["error"]


# ---------------------------------------------------------------------------
# RSP-02: response_size_bytes in envelope (run_workflow integration)
# ---------------------------------------------------------------------------


class TestResponseSizeBytes:
    """RSP-02: All composite workflow envelopes include response_size_bytes."""

    @pytest.mark.parametrize("workflow_id", [
        "bgp_summary",
        "routing_table",
        "firewall_summary",
        "interface_detail",
    ])
    def test_response_size_bytes_present_in_ok_envelope(self, workflow_id):
        """response_size_bytes must be in envelope for all composite workflows."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"key": "value"}

        with workflow_func_mock(workflow_id, return_value=mock_result):
            client = MagicMock()
            result = run_workflow(
                client, workflow_id=workflow_id, params={"device": "rtr-01"}
            )

        assert "response_size_bytes" in result, (
            f"{workflow_id}: missing response_size_bytes field"
        )
        assert isinstance(result["response_size_bytes"], int), (
            f"{workflow_id}: response_size_bytes must be int"
        )
        assert result["response_size_bytes"] > 0, (
            f"{workflow_id}: response_size_bytes should be > 0, got {result['response_size_bytes']}"
        )

    def test_response_size_bytes_in_partial_envelope(self):
        """response_size_bytes present and positive in partial status envelope."""
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"x": 1}
        w = [{"operation": "list_af", "error": "timeout"}]
        with workflow_func_mock("bgp_summary", return_value=(mock_result, w)):
            client = MagicMock()
            result = run_workflow(
                client, workflow_id="bgp_summary", params={"device": "rtr-01"}
            )

        assert result["status"] == "partial"
        assert "response_size_bytes" in result
        assert result["response_size_bytes"] > 0

    def test_response_size_bytes_equals_actual_json_bytes(self):
        """response_size_bytes equals len(json.dumps(data)) after serialization."""
        mock_result = MagicMock()
        payload = {"groups": [{"id": "1", "name": "test"}], "total_groups": 1}
        mock_result.model_dump.return_value = payload

        with workflow_func_mock("bgp_summary", return_value=mock_result):
            client = MagicMock()
            result = run_workflow(
                client, workflow_id="bgp_summary", params={"device": "rtr-01"}
            )

        import json
        expected = len(json.dumps(payload))
        assert result["response_size_bytes"] == expected, (
            f"Expected {expected}, got {result['response_size_bytes']}"
        )

    def test_response_size_bytes_zero_on_hard_error(self):
        """response_size_bytes is 0 when the workflow raises an exception."""
        with workflow_func_mock("bgp_summary") as mock_func:
            mock_func.side_effect = RuntimeError("connection refused")

            client = MagicMock()
            result = run_workflow(
                client, workflow_id="bgp_summary", params={"device": "rtr-01"}
            )

        assert result["status"] == "error"
        assert result["data"] is None
        assert result["response_size_bytes"] == 0
