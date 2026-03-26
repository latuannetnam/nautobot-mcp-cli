# STACK for v1.5 MCP Server Quality & Agent Performance

**Scope:** New capabilities only (response modes/projection, batching, observability, auth hardening, KPI benchmarking).
**Baseline:** Keep v1.4 architecture (FastMCP + pynautobot + Pydantic) and extend it.

## Required additions

| Capability | Library | Version | Integration points | Why this is needed / impact |
|---|---|---:|---|---|
| Response modes + field projection | `jmespath` | `==1.0.1` | `nautobot_mcp/bridge.py` (post-fetch projection), `nautobot_mcp/server.py` tool args (`response_mode`, `fields`), `nautobot_mcp/config.py` defaults | Gives a safe, standard projection syntax for agents (reduce payload/tokens without custom parser complexity). |
| High-volume batching safety | `aiolimiter` | `==1.2.1` | `nautobot_mcp/bridge.py` batch executor (concurrency + rate caps), workflow fan-out paths, `config.py` (`batch_max_items`, `batch_concurrency`, `batch_rps`) | Prevents agent-driven burst traffic from overloading Nautobot; enables predictable throughput for bulk reads/writes. |
| Distributed tracing + request spans | `opentelemetry-sdk` | `==1.35.0` | `server.py` (tool-level spans), `bridge.py` (endpoint/method spans), workflow dispatcher spans | End-to-end traceability per MCP call and downstream Nautobot operation; critical for debugging latency and failure hotspots. |
| OTLP export to collector/APM | `opentelemetry-exporter-otlp-proto-http` | `==1.35.0` | bootstrap/init path (telemetry setup), `config.py` (`OTEL_EXPORTER_OTLP_ENDPOINT`) | Makes traces usable in real systems (Tempo/Jaeger/Grafana Cloud/etc.) instead of local-only instrumentation. |
| Service metrics endpoint for KPIs | `prometheus-client` | `==0.23.1` | `server.py` (counters/histograms), new `/metrics` exposure path, `bridge.py` (method/endpoint metrics), workflow result status metrics | Required for KPI benchmarking in production-like runs (p95 latency, error rate, partial-rate, throughput). |
| Token verification for MCP-side auth hardening | `PyJWT` | `==2.10.1` | `server.py` auth guard before tool dispatch, `config.py` (`MCP_AUTH_ENABLED`, issuer/audience/public key), `exceptions.py` (`NautobotAuthorizationError`) | Adds explicit caller authentication/authorization control for MCP entrypoint; closes "any local caller can execute tools" gap. |

### Required `pyproject.toml` additions

```toml
dependencies = [
  # existing deps...
  "jmespath==1.0.1",
  "aiolimiter==1.2.1",
  "opentelemetry-sdk==1.35.0",
  "opentelemetry-exporter-otlp-proto-http==1.35.0",
  "prometheus-client==0.23.1",
  "PyJWT==2.10.1",
]
```

## Optional additions

| Library | Version | Use when | Integration impact |
|---|---:|---|---|
| `orjson` | `==3.11.3` | If batch/projection responses become CPU-bound during serialization | Swap response serialization paths for lower latency and smaller CPU cost. |
| `structlog` | `==25.4.0` | If you need consistently structured JSON logs with context binding | Replace ad-hoc logging in `bridge.py`/`server.py`; improves correlation with traces/metrics. |
| `pytest-benchmark` (dev) | `==5.1.0` | If KPI benchmarking should be repeatable in CI/UAT | Add benchmark suites for catalog, call bridge, and workflow latencies. |

## Keep current stack

- **FastMCP `>=3.0.0`**: already aligns with MCP tooling and works with OTel instrumentation.
- **pynautobot `>=2.3.0`**: keep as single Nautobot API transport layer; do not bypass with raw HTTP clients.
- **Pydantic v2 + pydantic-settings v2**: continue as validation/config core for new response/batch/auth settings.
- **Current exception hierarchy**: extend, don’t replace; add auth/rate-limit exceptions under `NautobotMCPError`.

## Avoid adding

- **Do not add Celery/RQ/Kafka** for v1.5 batching: adds operational overhead; in-process bounded batching is enough for this milestone.
- **Do not add a second web framework** (FastAPI/Flask) just for metrics/auth: integrate directly in current server process.
- **Do not add GraphQL/OpenAPI tool generation layers**: conflicts with validated 3-tool API Bridge design.
- **Do not add heavyweight policy engines** (OPA/Keycloak adapters) in v1.5: JWT verification + scoped checks are sufficient now.
- **Do not replace `pynautobot` with raw `httpx/requests` wrappers**: would regress existing error handling and endpoint compatibility.

