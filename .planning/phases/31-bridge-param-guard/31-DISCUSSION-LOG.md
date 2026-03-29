# Phase 31: Bridge Param Guard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 31-bridge-param-guard
**Areas discussed:** Error behavior, Comma-separation strategy, Guard scope

---

## Error Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Raise NautobotValidationError | Fast-fail, caller must fix. Consistent with bridge error model. | ✓ |
| Warn + truncate to 500 | Emit warning, silently truncate, continue. More lenient but may mask bugs. | |
| Warn + chunk and merge | Auto-split into batches, execute all, merge. Most forgiving but complex. | |

**User's choice:** Raise NautobotValidationError
**Notes:** Consistent with BRIDGE-01 spec and bridge's existing error model. Fast-fail is preferred for clarity.

---

## Comma-Separation Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Convert all `__in` lists to comma-separated | DRF-native format. Matches BRIDGE-03. Eliminates 414 risk for 100-500 items. | ✓ |
| Pass through unchanged | Keep existing pynautobot behavior for ≤500. Only guard >500 threshold. | |
| Convert only 11-500 | Heuristic: ≤10 pass through, 11-500 converted. Small lists don't need conversion. | |

**User's choice:** Convert all `__in` lists to comma-separated
**Notes:** Matches BRIDGE-03 spec. Doing this for all `__in` lists ≤ 500 proactively eliminates 414 risk for mid-size lists.

---

## Guard Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Guard ALL `__in`-suffixed keys | Generic pattern. Catches id__in, interface__in, device__in, vlan__in, etc. Future-proof. | ✓ |
| Guard specific keys only | Only id__in and interface. Matches documented 414 risk from ipam.py. | |

**User's choice:** Guard ALL `__in`-suffixed keys
**Notes:** Generic approach is future-proof. No reason to limit to known keys when the pattern is clear.

---

## Claude's Discretion

- Exact error message wording (should include param key, count, threshold)
- Internal implementation of `_guard_filter_params()` (e.g., regex vs string suffix check for `__in` detection)
- Placement within `_execute_core()` and `_execute_cms()` (before or after pagination kwargs merge)
- Unit test structure within `tests/test_bridge.py`

## Deferred Ideas

- Extending guard to `__iexact`, `__icontains`, or other filter suffixes — future phase
- CLI-level warning when bridge call hits the guard — future enhancement

