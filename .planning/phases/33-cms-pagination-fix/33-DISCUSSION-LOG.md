# Phase 33: CMS Pagination Fix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 33-cms-pagination-fix
**Areas discussed:** Mechanism, Bulk limit value, Discovery strategy, Regression thresholds

---

## Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| `endpoint.limit = 200` | Get endpoint object, set `endpoint.limit = 200`, then call `.all()` / `.filter()`. One-line change, works with existing accessor pattern. | ✓ |
| Global limit override | When `limit=0`, pass `limit=200` as argument instead. But pynautobot's `.all()` doesn't take page_size — `limit` controls total records, not per-call page size. | |
| `endpoint.all(page_size=200)` | Directly pass `page_size` kwarg to pynautobot's `.all()` / `.filter()`. May or may not be supported depending on pynautobot version. | |

**User's choice:** `endpoint.limit = 200`
**Notes:** User said "give me best option". Best option is `endpoint.limit = 200` — works with pynautobot 3.0.0's concurrent fetch logic which uses `Request.limit` as page size.

---

## Bulk Limit Value

| Option | Description | Selected |
|--------|-------------|----------|
| `_CMS_BULK_LIMIT = 200` | Already mentioned in ROADMAP and REQUIREMENTS.md. 200 is conservative: ceil(151/200)=1 call instead of 151. Matches existing comma-separation threshold from Phase 31. | ✓ |
| `_CMS_BULK_LIMIT = 500` | Maximum safe value. Larger pages = fewer calls. Risk: large response payloads for dense endpoints. | |
| Dynamic based on estimated count | Check if count < 200: set page_size=count. But count itself is an extra HTTP call... | |

**User's choice:** `_CMS_BULK_LIMIT = 200`
**Notes:** Already in ROADMAP and REQUIREMENTS.md as planned value.

---

## Endpoint Discovery

| Option | Description | Selected |
|--------|-------------|----------|
| Instrument HTTP call counting | Add logging wrapper around pynautobot HTTP calls. Run workflows, count calls per endpoint. Write findings to CMS_SLOW_ENDPOINTS registry. Permanent artifact. | |
| Probe each endpoint once | Test script that calls each endpoint with limit=0 and counts requests. Quick and targeted. | |
| Document from prod testing | Only `juniper_bgp_address_families` confirmed slow. Apply page_size=200 broadly when limit=0. No endpoint-specific registry needed. | ✓ |

**User's choice:** Document from prod testing
**Notes:** Pragmatic — only one endpoint is confirmed slow. Apply fix universally when `limit=0` without conditional logic.

---

## Regression Test Thresholds

| Option | Description | Selected |
|--------|-------------|----------|
| `< 5 seconds for all workflows` | Per STATE.md: "bgp_summary must complete < 5s". Conservative ceiling. | |
| `< 10 seconds for all workflows` | More conservative. Too lenient to catch regressions. | |
| Per-workflow thresholds | bgp_summary: < 5s, interface_detail: < 3s, etc. More precise. | ✓ |

**User's choice:** Per-workflow thresholds
**Notes:** User wants per-workflow differentiation.

---

## Threshold Values

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to researcher to measure | Run smoke test after fix applied, record actual times, set thresholds at 2x observed values. Data-driven. | ✓ |
| Set conservative estimates now | bgp_summary: < 5s, others: < 3s. Pre-determined. | |
| Set lenient ceiling | < 10s for all. Only catches catastrophic regressions. | |

**User's choice:** Defer to researcher to measure
**Notes:** Thresholds set at 2x empirically observed time after fix is applied.

---

## Claude's Discretion

- Exact pynautobot version compatibility (tested against 3.0.0; any 3.x should work)
- Whether to reset `endpoint.limit = None` after the call to avoid polluting shared state
- Specific threshold values for each workflow

## Deferred Ideas

None — discussion stayed within phase scope.

