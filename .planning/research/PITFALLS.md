# PITFALLS — v1.5 MCP Server Quality & Agent Performance

**Scope:** Subsequent milestone after v1.4, focused on agent-performance and quality upgrades to the 3-tool API Bridge (`nautobot_api_catalog`, `nautobot_call_nautobot`, `nautobot_run_workflow`).
**Target changes:** batching, projection, compact responses, and security hardening.
**Research date:** 2026-03-26

## High-risk pitfalls

| ID | Pitfall (milestone-specific) | Why this codebase is exposed | Recommended mitigation phase |
|---|---|---|---|
| P1 | **Batch path bypasses existing validation** | `call_nautobot()` currently enforces `_strip_uuid_from_endpoint()`, `_validate_endpoint()`, `_validate_method()`. A new batch executor can accidentally skip these per-item checks for speed. | **Phase 2 — Batch execution engine** |
| P2 | **Fail-fast batching breaks v1.4 partial-resilience expectations** | v1.4 established partial-failure behavior in workflows. If a batch aborts on first error, agents lose successful results and retry unnecessarily. | **Phase 2 — Batch execution engine** |
| P3 | **Response contract drift from compact mode** | Existing clients/skills expect `count`, `results`, `endpoint`, `method` and optionally `truncated`/`total_available`. Compact mode often removes “redundant” fields that are actually relied on. | **Phase 1 — Contract compatibility guardrails** |
| P4 | **Projection removes identity/navigation fields** | If projection strips `id`, `url`, or relation keys, follow-up PATCH/DELETE and workflow chaining fail. | **Phase 3 — Projection and compaction** |
| P5 | **Projection/compact applied inconsistently across core vs CMS routes** | `_execute_core()` and `_execute_cms()` are separate paths; uneven implementation causes agent confusion and nondeterministic outputs. | **Phase 3 — Projection and compaction** |
| P6 | **Batch limits applied globally instead of per operation** | Current `limit` semantics are per call with `MAX_LIMIT`. In batch mode, a shared cap can starve later operations and silently under-return data. | **Phase 2 — Batch execution engine** |
| P7 | **Security hardening blocks valid UUID endpoint patterns** | v1.4 added UUID path normalization (`/api/.../<uuid>/`). Tight regex/prefix rules can regress this and break common agent inputs. | **Phase 4 — Security hardening** |
| P8 | **Security relaxations re-open endpoint injection surface** | Current bridge only allows `/api/` and `cms:` prefixes. Performance shortcuts that add “raw URL” support can bypass safe routing boundaries. | **Phase 4 — Security hardening** |
| P9 | **Error quality regresses in optimized paths** | `server.handle_error()` depends on `NautobotMCPError.message/hint`. Batch/compact wrappers often collapse errors into generic strings, removing actionable hints. | **Phase 1 — Contract compatibility guardrails** |
| P10 | **Unbounded optimization knobs create DoS-by-legitimate-use** | Batch count + broad GET + projection wildcards can create massive in-memory lists (`list(endpoint_accessor.all())`) despite `MAX_LIMIT` on returned rows. | **Phase 4 — Security hardening** |

## Prevention controls

| Pitfall IDs | Prevention control | Actionable implementation in this repo | Testable acceptance criteria |
|---|---|---|---|
| P1, P8 | **Single execution path policy** | Implement batch as a thin loop that calls existing `call_nautobot()` per item (or a shared internal function) instead of a separate fast path. | Unit test: invalid endpoint/method in batch item returns same `NautobotValidationError` structure as single call. |
| P2 | **Per-item result envelope with aggregate status** | Return `{"status": "ok/partial/error", "items": [...], "errors": [...]}` while preserving successful item payloads even when others fail. | Integration test: 1 valid + 1 invalid item returns `status=partial`, includes one success and one structured error. |
| P3, P9 | **Response compatibility contract** | Define immutable minimum keys for `nautobot_call_nautobot` responses (`endpoint`, `method`, `count`, `results` or equivalent canonical compact field). Version any breaking compact schema (`compact_v2`). | Contract tests for normal and compact modes; existing agent skills pass without changes in default mode. |
| P4 | **Projection safelist + required fields floor** | Enforce required identity fields (`id`, optionally `url`) always included unless explicitly disabled with a guarded flag. Reject unknown projection fields with validation errors. | Unit test: projection omitting `id` still returns `id`; unknown field returns `VALIDATION_ERROR` + hint. |
| P5 | **Normalization layer after route execution** | Apply projection/compact in one post-processing function used by both `_execute_core()` and `_execute_cms()`. | Snapshot tests: equivalent core and CMS list calls produce identical envelope semantics under projection/compact. |
| P6, P10 | **Resource guardrails** | Add `max_batch_items`, `max_projection_fields`, and per-item `limit` clamped by `MAX_LIMIT`; reject oversized requests early. | Security/perf tests: oversized batch returns deterministic validation error; memory/time stays within threshold under stress tests. |
| P7 | **Regression lock for UUID normalization** | Keep `_strip_uuid_from_endpoint()` behavior covered before and after security changes; preserve one-UUID support and explicit rejection of nested UUID paths. | Unit tests: `/api/dcim/devices/<uuid>/` resolves correctly; nested UUID path returns clear validation hint. |
| P8 | **Strict endpoint allowlist enforcement** | Preserve `/api/` and `cms:` prefix checks; never execute arbitrary host URLs from tool input. | Unit test: `https://evil.example/...` rejected with unsupported-prefix validation error. |
| P1–P10 | **Milestone gate with scenario UAT** | Add live/UAT scenarios: catalog→projected read→batch mixed CRUD→workflow follow-up; include CMS endpoint coverage. | CI gate: all new unit + integration tests pass; UAT script reports no schema or hint regressions. |

## Early warning signals

- **Validation mismatch spike:** Rising count of `Unknown endpoint` / `Invalid method` errors in batch mode compared to single-call mode (signals P1).
- **Partial status collapse:** Batch requests frequently return full `error` when at least one item should succeed (signals P2).
- **Schema drift detections:** Agent skills begin requiring conditional parsing for compact vs non-compact defaults (signals P3/P5).
- **Follow-up call failures:** Increased `PATCH requires 'id'` or not-found-after-read patterns after projected GETs (signals P4).
- **Core/CMS parity breaks:** Same query shape succeeds in core endpoints but fails/changes shape in CMS endpoints (signals P5).
- **Unexpected truncation behavior:** User reports “missing items” with low counts in later batch elements (signals P6).
- **UUID regression:** Increase in errors for endpoint strings that include object UUID paths previously accepted in v1.4 (signals P7).
- **Security boundary regression:** Any acceptance of full external URLs or non-`/api/`/`cms:` prefixes in request logs (signals P8).
- **Hint quality degradation:** Error payloads lose actionable `hint` text and become generic “Unexpected error” responses (signals P9).
- **Latency/memory cliffs:** P95 latency and worker memory jump disproportionately with large batch + wide projection requests (signals P10).

---

**Recommended phase order (v1.5):**
1. **Phase 1 — Contract compatibility guardrails** (P3, P9)
2. **Phase 2 — Batch execution engine** (P1, P2, P6)
3. **Phase 3 — Projection and compact response layer** (P4, P5)
4. **Phase 4 — Security hardening + resource limits** (P7, P8, P10)
5. **Phase 5 — Integrated UAT/perf observability gate** (cross-cutting validation)
