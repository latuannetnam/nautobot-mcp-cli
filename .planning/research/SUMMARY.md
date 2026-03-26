# Research Summary — v1.5 MCP Server Quality & Agent Performance

**Date:** 2026-03-26
**Milestone context:** Improve MCP server quality and optimize for AI agents by reducing round-trips and response token footprint while preserving the 3-tool API Bridge architecture.

## Stack additions (and what to avoid)

### Recommended additions

- **`jmespath==1.0.1`** — safe field projection for response shaping (`bridge.py`, `server.py`, `config.py`)
- **`aiolimiter==1.2.1`** — batching concurrency/rate guardrails (`bridge/workflows batch executor`, config limits)
- **`opentelemetry-sdk==1.35.0`** + **`opentelemetry-exporter-otlp-proto-http==1.35.0`** — request tracing and latency visibility
- **`prometheus-client==0.23.1`** — KPI metrics (p95, error rate, throughput, partial-rate)
- **`PyJWT==2.10.1`** — MCP-side token verification for non-stdio hardening

### Keep current stack

- FastMCP + pynautobot + Pydantic v2 + existing exception hierarchy
- Extend current architecture instead of introducing new framework layers

### Avoid adding

- No Celery/RQ/Kafka for v1.5 batching
- No GraphQL/OpenAPI generation layer
- No second web framework just for metrics/auth
- No replacement of `pynautobot` with raw HTTP wrappers

---

## Must-have feature set vs differentiators

### Table stakes (must-have)

1. Stable low-count tool surface (keep 3 tools)
2. Contract-first catalog metadata (`contract_version`, params, response shape)
3. Structured errors with retryability and field-level diagnostics
4. Bounded responses by default (caps + truncation metadata)
5. Consistent top-level response envelope
6. Composite workflows to reduce round-trips

### Differentiators

1. Workflow contract versioning + compatibility guards
2. Explicit response modes (`minimal`/`standard`/`debug`)
3. Deterministic result ordering
4. Contract snapshot tests for MCP outputs
5. High-value planner workflows for multi-step investigations

### Anti-features to avoid

- Re-expanding into many endpoint-specific tools
- Unbounded defaults
- Shape-shifting responses
- Opaque error strings

---

## Architecture rollout order (recommended)

1. **Contract compatibility guardrails**
   - Define immutable minimum response keys
   - Add non-breaking envelope metadata
   - Add compatibility tests for current clients/skills

2. **Workflow batch execution (safe first path)**
   - Implement batch in `nautobot_run_workflow` first
   - Per-item status envelopes with aggregate `ok/partial/error`
   - Reuse existing validation path per batch item

3. **Projection + compact response adapter**
   - Central post-processing layer shared by core and CMS execution paths
   - Add `response_mode` + `fields`/`exclude_fields`
   - Enforce required identity-field floor (`id`, etc.)

4. **Security hardening + resource guardrails**
   - Keep strict endpoint prefix boundaries (`/api/`, `cms:`)
   - Add policy checks and request-size limits
   - Preserve UUID-path normalization behavior

5. **Observability + KPI gate**
   - Instrument request_id, latency, status, warnings
   - Add benchmark/UAT scenarios validating performance and contract stability

---

## Critical risks and mitigations

### Highest-risk pitfalls

- Batch path bypasses existing validation
- Fail-fast batch semantics regress partial-failure behavior
- Compact/projection causes contract drift
- Projection strips identity fields required for follow-up operations
- Security changes regress UUID endpoint normalization or loosen boundary checks

### Required controls

- Single execution-path policy (batch calls existing validated path)
- Per-item result envelopes; never discard successful items due to one failure
- Contract tests for default/non-default response modes
- Projection safelist + required-field floor
- Explicit resource guardrails (`max_batch_items`, projection limits, per-item caps)

---

## KPI targets and instrumentation strategy

### KPI targets (v1.5)

- **Round-trips per common agent task:** reduce **40–60%**
- **Median response token/size footprint:** reduce **35–55%**
- **p95 latency:**
  - catalog/cached discovery < **1.5s**
  - complex workflow calls < **3s**
- **Error-retry loop rate:** reduce **30%+**
- **First-pass task completion rate (no re-plan):** increase **20%+**

### Instrumentation strategy

- Add tracing spans per tool call and downstream bridge/workflow operation
- Emit structured metrics:
  - request count by tool/status
  - latency histogram (p50/p95/p99)
  - partial-success rate
  - truncation/projection usage rate
  - response size bytes distribution
- Add benchmark scenarios:
  1) catalog discovery
  2) projected list GET
  3) mixed batch workflow (partial success)
  4) CMS-heavy composite workflow

---

## Recommended requirement grouping for milestone scoping

1. **Contract & Envelope Stability**
2. **Batch Execution & Round-trip Reduction**
3. **Projection/Compaction & Token Efficiency**
4. **Security & Resource Guardrails**
5. **Observability, Benchmarks, and KPI Verification**

These groups align directly with the planned P0–P2 objective and provide clean phase boundaries for roadmap generation.