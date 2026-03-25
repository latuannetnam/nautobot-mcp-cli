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
        """config_data dict should be transformed to ParsedConfig before dispatch."""
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
                    "config_data": config_dict,
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
