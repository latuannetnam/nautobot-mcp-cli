---
plan: 11-01
phase: 11
title: "Pydantic Models for Firewall & Policy Domains"
status: complete
completed_at: 2026-03-21
commits:
  - 959a36a
  - 0a2fc7a
  - 1cace2c
key-files:
  created:
    - nautobot_mcp/models/cms/firewalls.py
    - nautobot_mcp/models/cms/policies.py
  modified:
    - nautobot_mcp/models/cms/__init__.py
---

## Summary

Created Pydantic models for all 23 firewall and policy CMS models following the `CMSBaseSummary` pattern established in Phases 9 and 10.

### What Was Built

**Firewall models** (`nautobot_mcp/models/cms/firewalls.py`) — 7 models:
- `FirewallFilterSummary` — top-level device-scoped filter
- `FirewallTermSummary` — child of filter
- `FirewallMatchConditionSummary` — child of term
- `FirewallMatchConditionToPrefixListSummary` — junction table
- `FirewallFilterActionSummary` — child of term
- `FirewallPolicerSummary` — top-level device-scoped policer
- `FirewallPolicerActionSummary` — child of policer

**Policy models** (`nautobot_mcp/models/cms/policies.py`) — 16 models:
- `PolicyPrefixListSummary`, `PolicyPrefixSummary`
- `PolicyCommunitySummary`, `PolicyAsPathSummary`
- `PolicyStatementSummary`, `JPSTermSummary`
- `JPSMatchConditionSummary`, `JPSMatchConditionRouteFilterSummary`
- `JPSMatchConditionPrefixListSummary`, `JPSMatchConditionCommunitySummary`, `JPSMatchConditionAsPathSummary`
- `JPSActionSummary`, `JPSActionCommunitySummary`, `JPSActionAsPathSummary`
- `JPSActionLoadBalanceSummary`, `JPSActionInstallNexthopSummary`

**Package exports** (`nautobot_mcp/models/cms/__init__.py`) updated with all 23 new models in `__all__`.

### Verification

```
All 23 models imported successfully
```
- `python -c "from nautobot_mcp.models.cms.firewalls import FirewallFilterSummary, ..."` ✓ 0
- `python -c "from nautobot_mcp.models.cms.policies import PolicyStatementSummary, ..."` ✓ 0
- `python -c "from nautobot_mcp.models.cms import FirewallFilterSummary, PolicyStatementSummary"` ✓ 0

### Deviations

None. Followed exact `routing.py` pattern with `_extract_nested_id_name` and `_str_val` helpers reused from that module.

## Self-Check: PASSED
