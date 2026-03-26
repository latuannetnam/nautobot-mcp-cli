# Feature Research — v1.5 MCP Server Quality & Agent Performance

**Domain:** Agent-performance features for Nautobot MCP API Bridge
**Researched:** 2026-03-26
**Scope:** New behavior for v1.5 only (building on shipped v1.4)

## Table Stakes

These are baseline patterns in top MCP servers for reducing round-trips, lowering token payloads, and keeping contracts predictable.

| Capability | Why it is table stakes | v1.5 behavior to add | Complexity | Depends on existing architecture |
|---|---|---|---|---|
| **Stable 3–5 tool surface** | Tool overload hurts model selection accuracy and increases prompt cost | Keep 3-tool surface as default; enforce “no endpoint-specific MCP tool sprawl” as a design rule | LOW | Existing `server.py` 3-tool API Bridge |
| **Contract-first discovery** | Agents need deterministic discovery before execution | Expand catalog with explicit `contract_version`, required/optional params, and response shape summary per workflow | MEDIUM | `nautobot_api_catalog`, catalog engine |
| **Strict input validation + typed errors** | Predictable failures are required for autonomous recovery | Standardize error envelope fields across all tools (`error_code`, `hint`, `retryable`, `field_errors`) | MEDIUM | Existing validation in `bridge.py`, existing error hint system |
| **Bounded responses by default** | Unbounded lists are a token bomb | Make limits explicit in every list-like response and include truncation metadata consistently | LOW | Existing `limit`, hard cap, truncation behavior in `bridge.py` |
| **Response shape consistency** | Agents need reusable parsing logic | Ensure every tool returns fixed top-level keys in stable order/type (`status`, `data`, `warnings`, `meta`) | MEDIUM | Existing workflow envelopes + partial-failure pattern |
| **Server-side composite workflows** | Round-trip reduction is the biggest practical win | Add/expand intent-level workflows for common multi-call tasks (read-heavy diagnostics first) | MEDIUM | Existing workflow registry + `nautobot_run_workflow` |
| **Identifier normalization** | Agents frequently pass URLs/UUIDs/names inconsistently | Extend normalization rules (already for UUID paths) to consistently accept name/UUID/URL where safe | MEDIUM | Existing endpoint normalization and device resolution paths |

## Differentiators

These separate “works” from “best-in-class” for agent efficiency and reliability.

| Differentiator | Why it matters | v1.5 behavior | Complexity | Depends on existing architecture |
|---|---|---|---|---|
| **Workflow contract versioning** | Prevents silent breakage when workflow schemas evolve | Add per-workflow `version` + changelog metadata in catalog; optional `min_version` guard on execution | MEDIUM | Workflow registry, catalog metadata |
| **Token-budget-aware response modes** | Lets agent choose concise vs diagnostic payloads intentionally | Add explicit `response_mode` (`minimal`, `standard`, `debug`) for workflows and bridge responses | MEDIUM | Existing `detail=False`, `limit=N`, response-size metadata |
| **Machine-actionable partial success semantics** | Enables robust autonomous continuation despite partial failures | Unify status taxonomy across tools: `ok`, `partial`, `error`; include per-subtask warning codes | LOW-MEDIUM | Existing `WarningCollector` and 3-tier status pattern |
| **Deterministic result ordering** | Reduces non-deterministic diffs and retry confusion | Guarantee stable sorting keys for list responses where backend ordering is ambiguous | LOW | Bridge response wrapping (`call_nautobot`) |
| **Contract test snapshots for MCP outputs** | Keeps tool contracts predictable over time | Add snapshot tests for envelope/schema per workflow/tool (not only functional tests) | MEDIUM | Existing UAT + pytest foundation |
| **Single-call “planner” workflows for common investigations** | Major round-trip savings in multi-step diagnostics | Add curated high-value bundles (e.g., “device health + config drift + CMS deltas”) with capped detail | MEDIUM-HIGH | Existing workflow orchestration and partial-failure handling |

## Anti-features

These are commonly requested but usually reduce agent quality, inflate tokens, or increase unpredictability.

| Anti-feature | Why it hurts agent performance | Better alternative | Complexity impact if avoided |
|---|---|---|---|
| **Re-expanding into many endpoint-specific MCP tools** | Tool-selection confusion, context bloat, maintenance overhead | Keep universal bridge + catalog + workflows | Saves HIGH complexity long-term |
| **Unbounded “return everything” defaults** | Token spikes, latency, model truncation | Default capped responses + explicit opt-in detail modes | Saves MEDIUM runtime/debug cost |
| **Schema-less/shape-shifting responses** | Fragile agent parsers and retry loops | Fixed envelopes + versioned contracts | Saves HIGH integration cost |
| **Overly “magic” parameter inference** | Non-deterministic behavior and hidden side effects | Explicit normalization rules + transparent metadata | Saves MEDIUM debugging cost |
| **Client-side orchestration requirement for common tasks** | Too many round-trips and higher failure surface | Move frequent N+1 patterns into server workflows | Saves HIGH token + latency cost |
| **Opaque error strings only** | Hard for agents to self-heal | Structured error codes + hints + retryability flags | Saves MEDIUM recovery cost |

## Prioritization

### P1 (Must-have for v1.5)

1. **Catalog contract metadata** (`contract_version`, params, response shape summary)
   - **Why:** Foundation for predictable contracts.
   - **Complexity:** MEDIUM.
   - **Dependencies:** `nautobot_api_catalog`, catalog engine.

2. **Unified response/error envelopes across all 3 tools**
   - **Why:** Predictable parsing + autonomous retries.
   - **Complexity:** MEDIUM.
   - **Dependencies:** `server.py` tool wrappers, `bridge.py` error translation, existing workflow envelopes.

3. **Token-budget response modes** (`minimal`/`standard`/`debug`)
   - **Why:** Direct control of payload size by agent intent.
   - **Complexity:** MEDIUM.
   - **Dependencies:** Existing `detail`, `limit`, response-size metadata.

4. **Deterministic ordering + consistent truncation metadata**
   - **Why:** Repeatable outputs and simpler diffing.
   - **Complexity:** LOW.
   - **Dependencies:** `call_nautobot` result shaping.

### P2 (High-value differentiators after P1)

1. **Workflow versioning and compatibility guardrails**
   - **Complexity:** MEDIUM.
   - **Dependencies:** Workflow registry + catalog.

2. **Contract snapshot tests (schema-level)**
   - **Complexity:** MEDIUM.
   - **Dependencies:** Existing pytest/UAT setup.

3. **1–2 new planner workflows for common investigations**
   - **Complexity:** MEDIUM-HIGH.
   - **Dependencies:** Existing composite orchestration + partial-failure model.

### P3 (Defer unless capacity remains)

1. **Broader identifier normalization expansion across all endpoints**
   - **Complexity:** MEDIUM-HIGH due to endpoint-specific ambiguity.
   - **Dependencies:** Bridge routing + endpoint registries.

2. **Advanced adaptive payload shaping by token budget integer target**
   - **Complexity:** HIGH.
   - **Dependencies:** Response-size metadata + per-workflow field-pruning rules.

---

**Bottom line:**
For top MCP servers, **table stakes** are bounded payloads, strict contracts, and server-side composites. The strongest **v1.5 differentiators** are contract versioning, explicit response modes, and deterministic envelopes that let agents recover and continue automatically. The main **anti-feature to avoid** is any return to tool sprawl or shape-shifting outputs.