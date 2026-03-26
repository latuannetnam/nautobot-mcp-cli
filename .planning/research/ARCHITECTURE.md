# ARCHITECTURE for v1.5 MCP Server Quality & Agent Performance

## Proposed architecture

v1.5 should keep the **3-tool surface unchanged** (`nautobot_api_catalog`, `nautobot_call_nautobot`, `nautobot_run_workflow`) and add new capabilities as **optional behaviors behind existing tool calls**.

### Recommended patterns

1. **Capability-advertised extension pattern (contract-safe)**
   - Add a `capabilities` block in `nautobot_api_catalog` response.
   - Agents discover support for `response_modes`, `field_projection`, `batch`, `observability`, `security_policies` before using them.
   - No breaking change: existing clients ignore unknown catalog fields.

2. **Execution envelope pattern (uniform observability + errors)**
   - Standardize metadata for every tool response:
     - `request_id`, `timestamp`, `latency_ms`
     - `status` (`ok|partial|error`)
     - `warnings` (already workflow-native)
     - `response_size_bytes` (already present in workflows)
   - Preserve current top-level keys; only add optional metadata fields.

3. **Policy middleware pattern (security centralized, logic unchanged)**
   - Introduce a pre-dispatch policy guard in bridge/workflow dispatch path:
     - method allowlist by endpoint
     - endpoint/domain RBAC profile checks
     - payload redaction for sensitive fields in logs
   - Keep domain modules unchanged; security enforced at the bridge seam.

4. **Projection + mode adapter pattern (token/size control)**
   - Add optional response shaping layer after core/CMS execution:
     - `mode`: `full|summary|minimal`
     - `fields`: include-list projection
     - `exclude_fields`: deny-list projection
   - Applies consistently to `call_nautobot` and `run_workflow` output.

5. **Batch orchestration pattern (single call, isolated failures)**
   - Add `batch` operation as an optional mode inside `nautobot_run_workflow` first (safer), then optionally in `nautobot_call_nautobot`.
   - Use per-item result envelopes with partial-failure semantics:
     - each item has independent `status`, `error`, `data`, `latency_ms`
   - Reuse existing v1.4 partial/warning concepts to avoid all-or-nothing failures.

### Target integration flow (v1.5)

```text
Agent
  ├─(1) nautobot_api_catalog() → discovers capabilities + policy hints
  ├─(2) nautobot_call_nautobot(..., options={mode, fields, trace})
  │      └─ server.py
  │          └─ bridge.py
  │              ├─ policy guard (authz/method/domain)
  │              ├─ endpoint routing (core/CMS existing)
  │              ├─ response adapter (mode/projection)
  │              └─ observability emitter (metrics + structured logs)
  └─(3) nautobot_run_workflow(..., params={..., execution:{batch,...}})
         └─ workflows.py dispatcher
             ├─ policy guard (workflow-level)
             ├─ registry dispatch (existing)
             ├─ optional batch fan-out
             ├─ envelope builder (existing + trace metadata)
             └─ observability emitter
```

---

## component changes

### New components (v1.5)

1. **`nautobot_mcp/response_adapter.py` (NEW)**
   - Responsibilities:
     - apply `mode` (`full|summary|minimal`)
     - apply `fields` / `exclude_fields` projection
     - compute final `response_size_bytes` consistently
   - Integration points:
     - called by `bridge.call_nautobot()` before return
     - called by `workflows.run_workflow()` before envelope finalization

2. **`nautobot_mcp/observability.py` (NEW)**
   - Responsibilities:
     - generate/propagate `request_id`
     - timing (`latency_ms`)
     - structured event emission (tool, endpoint/workflow, status, truncation, policy decisions)
     - metrics hooks (counter/histogram interface)
   - Integration points:
     - wrapper context in `server.py` tool handlers
     - event calls in `bridge.py` and `workflows.py`

3. **`nautobot_mcp/security/policy.py` (NEW)**
   - Responsibilities:
     - endpoint/method allowlists
     - workflow allowlists
     - optional role/profile-based restrictions
     - redaction rules for sensitive params/body fields
   - Integration points:
     - pre-dispatch checks in `bridge.call_nautobot()`
     - pre-dispatch checks in `workflows.run_workflow()`

4. **`nautobot_mcp/batch.py` (NEW)**
   - Responsibilities:
     - validate batch schema
     - execute items serially (v1) with deterministic ordering
     - collect per-item envelopes + aggregate status
   - Integration points:
     - invoked from `workflows.run_workflow()` for first rollout

### Modified components

1. **`nautobot_mcp/server.py` (MODIFIED)**
   - Add optional arguments (non-breaking defaults):
     - `nautobot_call_nautobot(..., options: dict | None = None)`
     - `nautobot_run_workflow(..., execution: dict | None = None)`
   - Inject request context (`request_id`, timing scope).
   - Keep existing positional/required params untouched.

2. **`nautobot_mcp/bridge.py` (MODIFIED)**
   - Add policy guard before endpoint execution.
   - Preserve existing routing/validation code paths.
   - Apply response adapter after raw result.
   - Emit observability events at validate/dispatch/return stages.

3. **`nautobot_mcp/workflows.py` (MODIFIED)**
   - Extend `run_workflow()` to accept `execution` control dict.
   - Add batch branch for workflow-level fan-out.
   - Keep `_build_envelope()` as canonical shape; append metadata fields.

4. **`nautobot_mcp/catalog/engine.py` (MODIFIED)**
   - Add `capabilities` section:
     - supported response modes
     - projection syntax
     - batch limits
     - observability fields availability
     - security policy summaries (high-level)
   - Keep current domain-filter semantics intact.

### Explicit integration points

- **Server ↔ Observability**: request lifecycle context per tool invocation.
- **Bridge ↔ Security Policy**: preflight authorize/validate operation.
- **Bridge ↔ Response Adapter**: normalize payload shaping post-dispatch.
- **Workflows ↔ Batch Engine**: optional sub-execution orchestration.
- **Catalog ↔ Agent**: capability negotiation channel.
- **Observability ↔ Security**: policy decisions included in audit events.

---

## API contract strategy

### Stability rules (must hold)

1. **Do not rename/remove existing tools or required params**.
2. **Only additive changes** in request/response schema.
3. **Default behavior matches v1.4** when new options are absent.
4. **Error contracts remain compatible** (`NautobotValidationError`, existing hint behavior).

### Additive contract design

1. `nautobot_call_nautobot`
   - Existing:
     - `method`, `endpoint`, `params`, `body`
   - Additive:
     - `options` (optional dict):
       - `mode`: `full|summary|minimal`
       - `fields`: `list[str]`
       - `exclude_fields`: `list[str]`
       - `trace`: `bool`

2. `nautobot_run_workflow`
   - Existing:
     - `workflow_id`, `params`
   - Additive:
     - `execution` (optional dict):
       - `mode`, `fields`, `exclude_fields`
       - `batch` object (optional)
       - `trace`

3. `nautobot_api_catalog`
   - Existing domain/workflow output unchanged.
   - Additive:
     - `capabilities`
     - `limits` (max batch items, projection depth, etc.)
     - `security` summary (non-sensitive)

### Versioning and negotiation

- Keep MCP tool names as v1.x stable contracts.
- Use **catalog capability discovery** instead of forcing version bumps.
- If a feature is unsupported, return clear validation hint:
  - e.g., `mode='minimal' not supported; check nautobot_api_catalog.capabilities.response_modes`.

### Backward compatibility tests

- Golden tests for v1.4 request shapes (must still pass).
- Snapshot tests for responses with no `options`/`execution` (must match prior structure except additive metadata allowed).
- Feature tests gated by `capabilities` advertisement.

---

## rollout sequence

Dependency-aware build order that minimizes regression risk:

1. **Foundation: observability primitives (NEW)**
   - Implement request context + structured events.
   - Wire minimally in `server.py` only.
   - Why first: needed to measure all subsequent rollout impact.

2. **Security policy guard (NEW + MODIFIED bridge/workflows)**
   - Add policy evaluation hooks with permissive defaults.
   - Start in "audit" mode (log only), then enforce mode.
   - Dependency: uses observability for decision trace.

3. **Response adapter for mode/projection (NEW + MODIFIED bridge/workflows)**
   - Implement shaping with strict schema validation.
   - Apply to `run_workflow` first (already has envelope discipline), then to `call_nautobot`.
   - Dependency: policy guard in place to prevent unsafe field exposure.

4. **Catalog capability publication (MODIFIED catalog/engine)**
   - Advertise supported modes/projection and limits.
   - Dependency: only publish capabilities that are actually implemented.

5. **Batch engine v1 in workflows (NEW + MODIFIED workflows/server)**
   - Introduce deterministic serial batch for workflow calls.
   - Include per-item envelope and aggregate status.
   - Dependency: observability + response adapter required for usable diagnostics/output control.

6. **Optional bridge-level batch (MODIFIED bridge/server, later phase)**
   - If needed, add batch to raw REST bridge with stricter limits.
   - Dependency: workflow batch proven stable under production load.

7. **Hardening + compatibility gate**
   - Run full UAT/live tests.
   - Add regression suite for v1.4 compatibility.
   - Release when: integration points verified, additive contract compliance proven, and partial-failure semantics validated.

### Delivery checkpoints

- **Checkpoint A:** observability + audit-only security live.
- **Checkpoint B:** response modes + field projection live and catalog-advertised.
- **Checkpoint C:** workflow batch live with partial-failure envelopes.
- **Checkpoint D:** enforcement security mode + optional bridge batch decision.
