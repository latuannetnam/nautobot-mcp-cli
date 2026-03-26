# Phase 21: Workflow Contracts & Error Diagnostics - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix workflow parameter contract bugs (WFC) and enrich error messages with actionable context (ERR) in the API Bridge MCP server. Affects `workflows.py`, `workflow_stubs.py`, `client.py`, and `exceptions.py`.

</domain>

<decisions>
## Implementation Decisions

### Workflow Param Contracts (WFC)

- **D-01:** `verify_data_model` registry entry in `workflows.py`: add `"parsed_config"` to `required` list (currently only `"device_name"`).
- **D-02:** `verify_data_model` registry entry: add `"transforms"` entry mapping `"parsed_config"` to `ParsedConfig.model_validate` — mirroring the `onboard_config` pattern.
- **D-03:** `workflow_stubs.py` `verify_data_model` stub: update `params` from `{"device_name": "str (required)"}` to also include `"parsed_config": "dict (required, ParsedConfig schema)"`.
- **D-04:** Registry startup self-check (WFC-03): import-time validation — when `workflows.py` is first imported, walk `WORKFLOW_REGISTRY` and verify each function's signature against its `required` + `param_map`. Raise `NautobotValidationError` on mismatch (e.g., `parsed_config` missing from `required` for `verify_data_model`). Fails fast, consistent with existing exception hierarchy.

### Error Diagnostics (ERR)

- **D-05:** 400 body parsing (ERR-01): in `_handle_api_error()` in `client.py`, when `status_code == 400`, parse `error.req.text` as JSON and extract DRF field-level errors (typically `{"app_label__field": ["error message"]}`). Pass the parsed errors list to `NautobotValidationError.errors`. Falls back to the existing generic message if parsing fails.
- **D-06:** Per-endpoint hint map (ERR-02): add `ERROR_HINTS = {endpoint_pattern: hint_string, ...}` dict in `client.py`. Keyed by endpoint path prefix (e.g., `"/api/dcim/devices/"`). Covers ~10-15 high-value endpoints with precise guidance (e.g., "device filter expects UUID not name", "interface filter requires interface_id not name"). Default fallback for unknown endpoints: derived from operation + model name.
- **D-07:** Composite error origin (ERR-03): `run_workflow()` in `workflows.py` catches composite function exceptions and adds `{"operation": "<function_name>", "error": "<exception_string>"}` to the `warnings` list in the envelope. Reuses the existing `WarningCollector` format from Phase 19 — no new exception class needed. Error is caught at the `run_workflow()` level, not inside composite functions.
- **D-08:** `NautobotAPIError` hints (ERR-04): apply the per-endpoint hint map (D-06) to `NautobotAPIError` for known endpoints. For unknown status codes (500, 429, etc.), use status-code-based fallback hints (e.g., "500 — Nautobot server error, check server health"; "429 — rate limited, retry after backoff"). Never surface raw server stack traces.

### Claude's Discretion
- Exact per-endpoint hint strings (D-06) — which endpoints get special hints, exact wording
- Implementation details of the import-time signature validation (how to extract function signatures, what exception message format)
- Test structure and organization for WFC and ERR requirements

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — WFC-01, WFC-02, WFC-03 (workflow contracts), ERR-01, ERR-02, ERR-03, ERR-04 (error diagnostics)

### Current Implementation
- `nautobot_mcp/workflows.py` — `WORKFLOW_REGISTRY` (bug: verify_data_model missing parsed_config), `_build_envelope()`, `run_workflow()`
- `nautobot_mcp/catalog/workflow_stubs.py` — `WORKFLOW_STUBS` (bug: verify_data_model params missing parsed_config)
- `nautobot_mcp/client.py` — `_handle_api_error()` (needs 400 body parsing + hint enrichment)
- `nautobot_mcp/exceptions.py` — `NautobotValidationError`, `NautobotAPIError` exception classes
- `nautobot_mcp/verification.py` — `verify_data_model()` function signature (takes `parsed_config: ParsedConfig`)

### Prior Phase Decisions
- `.planning/phases/19-partial-failure-resilience/19-CONTEXT.md` — WarningCollector pattern, `{"operation": "<name>", "error": "<message>"}` format, three-tier status model

### Existing Tests
- `tests/test_workflows.py` — 60 lines, registry sync guard tests
- `tests/test_exceptions.py` — 90 lines, exception hierarchy tests
- `tests/test_client.py` — (check for API error handling tests)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `NautobotValidationError.errors` field (already in `exceptions.py`) — designed for field-level errors, ready to use
- `WarningCollector` format from Phase 19 — `{"operation": "<name>", "error": "<message>"}` — directly reusable for ERR-03 envelope-level origin
- `onboard_config` registry entry in `workflows.py` — shows the `transforms` pattern for `ParsedConfig.model_validate`
- `run_workflow()` try/except block — ideal interception point for ERR-03 composite error origin capture

### Established Patterns
- Registry is a plain dict — no class needed for WFC-03 self-check, can validate in a module-level function called at import
- `error.req.text` from pynautobot `RequestError` carries the raw response body — `error.req.status_code` carries HTTP status
- Existing exceptions use `code` field for machine-readable error types — hint map follows same machine-readable pattern

### Integration Points
- `workflows.py` — fix `verify_data_model` entry, add import-time validation, add composite error → warning conversion
- `workflow_stubs.py` — update `verify_data_model` params
- `client.py` `_handle_api_error()` — parse 400 body JSON, apply hint map
- `exceptions.py` — no structural changes needed (NautobotValidationError already has `errors` field)
- `tests/test_workflows.py` — add WFC-03 self-check tests

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for test structure and exact hint string wording.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-workflow-contracts-error-diagnostics*
*Context gathered: 2026-03-26*
