# Phase 21: Workflow Contracts & Error Diagnostics - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 21-workflow-contracts-error-diagnostics
**Mode:** discuss
**Areas discussed:** Workflow param contracts, Error diagnostics & enrichment

---

## Area 1: Workflow Param Contracts

### Q1: WFC-03 — Startup validation approach

| Option | Description | Selected |
|--------|-------------|----------|
| Import-time validation (Recommended) | Validate function signatures against required params when workflows.py is first imported. Fails fast. | ✓ |
| Explicit validate_registry() call | Standalone function callers must invoke explicitly. Flexible but easy to forget. | |
| On-first-use validation | Check registry on first run_workflow() call. Lazy, still before real work. | |

**User's choice:** Import-time validation (Recommended)
**Notes:** Consistent with the project's "fail fast" philosophy. Custom exception type (NautobotValidationError) noted as Claude's discretion — consistent with existing hierarchy.

### Q2: WFC-03 — Exception type for startup validation

| Option | Description | Selected |
|--------|-------------|----------|
| NautobotValidationError | Consistent with existing exception hierarchy, clear error codes | ✓ (Claude's discretion) |
| ValueError | Standard Python, no new exception class needed | |

**User's choice:** Defer to Claude's discretion — NautobotValidationError

### Bug Fixes (no decision needed — all clear-cut)

- WFC-01: `verify_data_model` required list missing `parsed_config` → add it
- WFC-02: `verify_data_model` needs `transforms` for `ParsedConfig.model_validate` → add it
- Stubs: `workflow_stubs.py` verify_data_model params missing `parsed_config` → add it

---

## Area 2: Error Diagnostics & Enrichment

### Q1: ERR-02 — Contextual hint approach

| Option | Description | Selected |
|--------|-------------|----------|
| Per-endpoint hint map (Recommended) | Hardcoded ERROR_HINTS dict keyed by endpoint pattern. More precise. Low maintenance for ~10-15 high-value endpoints. | ✓ |
| Hint derivation from operation+model | Construct hints dynamically from operation and model name. No maintenance, less precise. | |

**User's choice:** Per-endpoint hint map (Recommended)

### Q2: ERR-03 — Composite error origin approach

| Option | Description | Selected |
|--------|-------------|----------|
| Envelope-level origin (Recommended) | run_workflow() catches composite exceptions and adds to warnings list in envelope. Reuses WarningCollector format. No new exception class. | ✓ |
| Exception-level origin | Composite functions wrap child calls in try/except and raise with .origin attribute set. More structured but requires new exception subclass. | |

**User's choice:** Envelope-level origin (Recommended)
**Notes:** Reuses existing Phase 19 WarningCollector pattern. `{"operation": "<name>", "error": "<message>"}` format carries through to error envelope.

### Q3: ERR-04 — NautobotAPIError hint enrichment

| Option | Description | Selected |
|--------|-------------|----------|
| Hint map + status code fallback (Recommended) | Apply per-endpoint hint map (ERR-02) to NautobotAPIError for known endpoints. Status-code-based fallback for 500/429/etc. | ✓ |
| Status code only | Skip per-endpoint hints. Generic guidance by status code only. Simpler, less precise. | |

**User's choice:** Hint map + status code fallback (Recommended)

### Bug Fixes (no decision needed)

- ERR-01: 400 body parsing — parse `error.req.text` as JSON, extract field-level errors, pass to `NautobotValidationError.errors`

---

## Claude's Discretion

- Exact per-endpoint hint strings (which endpoints, exact wording)
- Implementation details of import-time signature validation (how to extract function signatures, exact exception message)
- Test structure and organization for WFC and ERR requirements

## Deferred Ideas

None — discussion stayed within phase scope
