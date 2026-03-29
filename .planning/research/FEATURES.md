# Research: Features — v1.7 URI Limit Fix

**Domain:** Bug fix — eliminate 414 Request-URI Too Large and 500 errors
**Researched:** 2026-03-29

## Overview

Single category: **Reliability / Bug Fix**. No new user-facing features — pure defect elimination.

## Findings: 414-risk patterns

### HIGH severity — bridge unguarded (bridge.py)

`nautobot_call_nautobot` accepts arbitrary `params` dict. Any caller can inject `id__in=[uuid1, ..., uuid10000]` and trigger 414 on **any endpoint** (core or CMS). This is the most dangerous finding.

| Pattern | File | Risk | Fix |
|---------|------|------|-----|
| `.filter(**params)` | `bridge.py:188` | HIGH | Guard `__in` list params; raise if > 500 |
| `.filter(**effective_params)` | `bridge.py:270` | HIGH | Same guard for CMS path |

### LOW severity — ipam.py already chunked

`get_device_ips()` already chunks at 500 with `chunked()`. But `.filter(id__in=chunk)` creates repeated query params, not comma-separated. At 700 IPs → 2 chunks × ~18 KB each → 414.

| Pattern | File | Risk | Fix |
|---------|------|------|-----|
| `.filter(id__in=chunk)` | `ipam.py:371` | LOW | Direct HTTP with comma-separated |
| `.filter(interface=chunk)` | `ipam.py:361` | LOW | Direct HTTP with comma-separated |
| `.filter(id__in=chunk)` | `ipam.py:269` | LOW | Already chunked at 500; VLANs are few per device |

### LOW severity — all other .filter() sites

All other `.filter()` calls in the codebase pass **scalar values** (single device name, single interface ID, etc.). These are safe — no list expansion.

## VLANs 500 error

`devices summary DEVICE` calls `client.count("ipam", "vlans", location="HQV")` → hits `/api/ipam/vlans/count/?location=HQV` → **500 Internal Server Error** from Nautobot server.

This is a **server-side issue** — cannot be fixed in CLI/MCP code. Mitigation: catch 500 errors on `/count/` and return `None` for affected counts, letting the operation continue without the VLAN count.

## Complexity

- ipam.py fix: LOW complexity, isolated, well-understood pattern
- bridge.py fix: MEDIUM complexity, affects all MCP callers, needs careful error messaging
- VLANs 500 mitigation: LOW complexity, one extra try/except

## Dependencies

None — all patterns exist in codebase already.
