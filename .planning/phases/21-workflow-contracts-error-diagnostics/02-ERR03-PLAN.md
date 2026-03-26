# Plan 02: Composite Workflow Error → Origin Field (ERR-03)

## must_haves
- `run_workflow()` catches composite function exceptions and adds `{"operation": "<function_name>", "error": "<exception_string>"}` to `warnings` in the envelope (ERR-03)
- Envelope `status` remains `"error"` when exception was raised (no data) — partial failures from composite return tuples already handled by Phase 19
- Tests verify that exceptions from composite workflows surface as warning entries with `origin` field

## frontmatter
```yaml
wave: 2
depends_on:
  - 01-WFC-ERR01-ERR02-ERR04-PLAN.md
files_modified:
  - nautobot_mcp/workflows.py
  - tests/test_workflows.py
autonomous: false
```

**Note:** Wave 2 depends on Wave 1 because the ERR-03 code path in `run_workflow()` is at L284–285 of `workflows.py` — the same function being modified in Wave 1 (WFC-03 `_validate_registry` addition). Both changes live in `workflows.py`. They can be implemented in parallel if the executor carefully applies both diffs; otherwise, sequential execution ensures no merge conflicts.

---

## Context: What ERR-03 Means

**Requirement:** Composite workflow errors include `origin` field showing which child operation failed.

Phase 19 already implemented partial failure for composite workflows that **return** `(result, warnings)` tuples — where enrichment queries fail but primary queries succeed. Those produce `status: "partial"` envelopes with `warnings` list.

ERR-03 targets a **different code path**: when a composite workflow function **raises an exception** instead of returning. Currently (L284–285 of `workflows.py`):

```python
except Exception as e:
    return _build_envelope(workflow_id, params, error=e)
```

This produces `status: "error"` with `data: None` and the exception as a flat string. The `workflow_id` in the envelope is the **composite** workflow name (e.g., `bgp_summary`), but it gives no indication of **which internal step** (e.g., `list_bgp_groups`, `list_bgp_neighbors`) failed.

ERR-03 requirement: catch the exception at `run_workflow()` level and add it to `warnings` as `{"operation": "<workflow_id>", "error": "<exception_string>"}` — the same format as `WarningCollector` from Phase 19. This preserves the `status: "error"` semantics (no data returned) while giving the agent enough context to understand what failed.

---

## Task — Update `run_workflow()` exception handler for ERR-03

### Task E1 — Add composite workflow exception → warning conversion (ERR-03)
**File:** `nautobot_mcp/workflows.py`
**read_first:**
- `nautobot_mcp/workflows.py` L260–286 (`run_workflow` try/except block)
- `nautobot_mcp/warnings.py` L31–41 (`WarningCollector.add()` — format reference)

**Action:** Replace the `except Exception as e:` block at L284–285 with:
```python
    except Exception as e:
        # ERR-03: Composite workflow exceptions are captured as warnings in the
        # envelope rather than a bare error string. This gives agents visibility
        # into which child operation failed without losing the error status.
        #
        # Composite workflows are identified by the fact they live in WORKFLOW_REGISTRY
        # with the same workflow_id. We record the workflow_id as the "operation"
        # so the agent knows which top-level workflow encountered the failure.
        exception_warning = {
            "operation": workflow_id,
            "error": str(e),
        }
        return _build_envelope(
            workflow_id,
            params,
            error=e,
            warnings=[exception_warning],
        )
```

**acceptance_criteria:**
- `workflows.py` contains `exception_warning = {` in the `run_workflow()` except block
- `workflows.py` contains `"operation": workflow_id` in that dict
- `workflows.py` contains `"error": str(e)` in that dict
- `workflows.py` contains `warnings=[exception_warning]` in the `_build_envelope()` call in the except block
- The except block still passes `error=e` to `_build_envelope()` so `status: "error"` is preserved

---

### Task E2 — Add tests for ERR-03 (composite workflow exception → warning in envelope)
**File:** `tests/test_workflows.py`
**read_first:**
- `tests/test_workflows.py` L294–316 (TestRunWorkflowErrors)
- `tests/test_workflows.py` L70–84 (`workflow_func_mock` context manager)

**Action:** Append new test class to `test_workflows.py`:
```python
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
                    "parsed_config": {"hostname": "test", "platform": "junos", "interfaces": [], "ip_addresses": [], "vlans": [], "routing_instances": [], "protocols": [], "firewall_filters": []},
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
```

**acceptance_criteria:**
- `test_workflows.py` contains `class TestRunWorkflowCompositeErrorOrigin`
- `test_workflows.py` contains `workflow_id` as the `operation` value in warning assertions
- `pytest tests/test_workflows.py::TestRunWorkflowCompositeErrorOrigin -v` passes (all 7 tests green)
- `pytest tests/test_workflows.py::TestRunWorkflowPartial::test_tuple_result_with_warnings_returns_partial -v` still passes (Phase 19 behavior preserved)

---

## Verification
```bash
# ERR-03 tests
pytest tests/test_workflows.py::TestRunWorkflowCompositeErrorOrigin -v

# Verify Phase 19 partial failure behavior still works
pytest tests/test_workflows.py::TestRunWorkflowPartial -v

# Full workflow test suite (no regressions)
pytest tests/test_workflows.py -v

# Run all Phase 21 tests together
pytest tests/test_workflows.py tests/test_client.py tests/test_exceptions.py -v
```
