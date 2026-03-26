# Phase 22: Response Ergonomics & UAT - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 22-response-ergonomics-uat
**Mode:** discuss
**Areas discussed:** Summary mode depth, limit parameter design, response_size_bytes semantics, UAT validation scope

---

## Summary Mode Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Counts at both levels | Strip families[] and vrrp_groups[] entirely; keep family_count and vrrp_group_count per unit | |
| Families only, VRRP stays | Strip families[] and vrrp_groups[] sub-arrays; keep VRRP detail if it loaded | |
| Counts per-family, families stay | Keep families but strip vrrp_groups[]; keep vrrp_group_count per family | |
| You decide | Claude decides based on typical agent use patterns | ✓ |

**User's choice:** You decide
**Notes:** User deferred to Claude. Decision: Counts at both levels (D-01) — strips families[] and vrrp_groups[] entirely, keeps family_count and vrrp_group_count per unit.

---

## limit Parameter Design (first question)

| Option | Description | Selected |
|--------|-------------|----------|
| Per-array capping with limit=0 as 'all' | limit=0 sentinel for no cap; cap each result array independently | ✓ |
| Global total cap with limit=0 as 'all' | Single limit caps total items across all arrays | |
| Per-array limits with None='all' | Explicit None for no cap, positive int per array | |

**User's choice:** Per-array capping with limit=0 as 'all'
**Notes:** Nautobot convention (limit=0 = return all) conflicts with Python falsy semantics — resolved by treating 0 as sentinel value.

---

## limit Parameter Design (second question)

| Option | Description | Selected |
|--------|-------------|----------|
| interface_detail only | Only interface_detail gets limit | |
| All composites | All composites: bgp_summary, routing_table, firewall_summary, interface_detail | ✓ |
| You decide | Claude decides | |

**User's choice:** All composites
**Notes:** All 4 composite workflows get the limit parameter for consistent API.

---

## response_size_bytes Semantics (first question)

| Option | Description | Selected |
|--------|-------------|----------|
| JSON bytes, always present | len(json.dumps(response_body)), always included in envelope | ✓ |
| JSON bytes, conditional | Only included when response exceeds threshold (>10KB) | |
| In-memory object size | sys.getsizeof of serialized object | |

**User's choice:** JSON bytes, always present
**Notes:** Measured as `len(json.dumps(response_body))`. Always present — agents can always rely on it.

---

## response_size_bytes Semantics (second question)

| Option | Description | Selected |
|--------|-------------|----------|
| All composites | bgp_summary, routing_table, firewall_summary, interface_detail all include response_size_bytes | ✓ |
| interface_detail only | Only interface_detail gets response_size_bytes | |
| You decide | Claude decides | |

**User's choice:** All composites
**Notes:** Consistent API — every composite gives size metadata.

---

## UAT Validation Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Update smoke script + add pytest | Both smoke and pytest updated with RSP coverage | ✓ |
| Pytest only | Skip smoke script; add pytest tests only | |
| Smoke script only | Update smoke script, leave pytest unchanged | |

**User's choice:** Update smoke script + add pytest
**Notes:** Both smoke script (9 checks → RSP-aware) and pytest suite get coverage for all three RSP requirements.

---

## Claude's Discretion

- Summary mode depth (D-01 through D-05) — user said "You decide"
- Exact `detail=False` implementation — CLI decided: strip families[] and vrrp_groups[] entirely, keep counts
- All other decisions made by user

## Deferred Ideas

None — discussion stayed within phase scope
