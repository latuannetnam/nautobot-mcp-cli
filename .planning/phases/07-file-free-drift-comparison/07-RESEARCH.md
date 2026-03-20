# Phase 7 Research: File-Free Drift Comparison

**Date:** 2026-03-20
**Status:** COMPLETE

## Standard Stack

- **DiffSync** — Not used for this phase. The existing `verification.py` uses DiffSync for full config comparison, but file-free drift is simpler (per-interface IP/VLAN sets). Direct set comparison is cleaner than DiffSync for this use case.
- **Pydantic** — Use for `QuickDriftReport`, `InterfaceDrift`, `DriftSummary` response models (consistent with all other modules).
- **pynautobot** — Use via existing `NautobotClient` for fetching Nautobot-side data.

## Architecture Patterns

### Input Auto-Detection
Two input shapes detected by checking `isinstance(interfaces_data, list)`:
1. **Dict (flat map):** `{"ae0.0": {"ips": [...], "vlans": [...]}}`
2. **List (DeviceIPEntry):** `[{"interface": "ae0", "address": "10.1.1.1/30"}, ...]`

Pattern: normalize both to canonical dict form before comparison.

### Comparison Strategy: Direct Set Comparison
NOT DiffSync — this is simpler. For each interface:
- IP comparison: `set(input_ips) vs set(nautobot_ips)` → missing/extra
- VLAN comparison: `set(input_vlans) vs set(nautobot_vlans)` → missing/extra

DiffSync would be overkill since we don't need to track attribute changes (description, enabled) — just set membership.

### Module Placement
New `nautobot_mcp/drift.py` module — separate from `verification.py` because:
- Different input (dict vs ParsedConfig)
- Different output (QuickDriftReport vs DriftReport)
- Different algorithm (set comparison vs DiffSync)
- Keeps `verification.py` focused on file-based comparison

## Critical Finding: VLAN-per-Interface Data Access

> [!WARNING]
> `list_interfaces()` returns `InterfaceSummary` which does NOT include `untagged_vlan` or `tagged_vlans` fields. The plan must fetch raw pynautobot records to get per-interface VLAN data.

### How Nautobot stores VLAN-to-interface mapping

In Nautobot, VLANs are associated with interfaces via two fields on the **Interface** record:
- `untagged_vlan` — single VLAN reference (or None)
- `tagged_vlans` — list of VLAN references

These are available on **raw pynautobot records** but NOT on `InterfaceSummary` (our Pydantic model strips them).

### Approaches to get per-interface VLAN data

| Approach | How | Pro | Con |
|----------|-----|-----|-----|
| **A) Raw pynautobot records** | `client.api.dcim.interfaces.filter(device=name)` then read `.untagged_vlan`/`.tagged_vlans` | Per-interface data, no extra calls | Bypasses our model layer |
| **B) Use `list_vlans(device=X)`** | Existing function in `ipam.py` | Reuses existing code | Returns **global** set of VLANs, NOT per-interface |
| **C) Enhance InterfaceSummary** | Add `untagged_vlan`/`tagged_vlans` to model | Clean model approach | Breaking/backward-compat risk, large change |

**Recommendation: Approach A** — Fetch raw interface records in `compare_device()` directly via `client.api.dcim.interfaces.filter()`. This is the same pattern used in `ipam.py`'s `list_vlans(device=X)` (line 180-187) and is the only way to get per-interface VLAN assignment.

### Impact on Plan 07-01

Task 07-01-03 (`compare_device`) must use raw pynautobot records instead of `list_interfaces()` for the VLAN comparison step. The `list_interfaces()` call can still be used for getting interface name sets for the missing/extra interface check.

## IP Address Matching Edge Cases

### Bare IPs (no prefix length)
Input: `"10.1.1.1"` vs Nautobot: `"10.1.1.1/30"`

Strategy: If input IP has no `/`, match by host part using `startswith(ip + "/")`. This is lenient-with-warnings per CONTEXT decision.

### IPv6 handling
Input: `"2001:db8::1/64"` — string comparison works since Nautobot stores the same format.

### Duplicate IPs across interfaces
Nautobot allows the same IP on multiple interfaces. The `get_device_ips()` function returns flat entries with `interface_name`. The normalization step groups by interface, so each interface gets its own IP set.

## Common Pitfalls

1. **VLAN VID vs VLAN ID** — Nautobot has both a UUID (`id`) and a VLAN ID number (`vid`). Always compare `vid` (the number), not the UUID.

2. **`tagged_vlans` iteration** — `iface.tagged_vlans` returns reference objects. Must access `.vid` attribute, and handle cases where it's a plain dict vs a pynautobot Record.

3. **`untagged_vlan` None check** — Always check `if iface.untagged_vlan:` before accessing `.vid`. Some interfaces have no untagged VLAN.

4. **InterfaceSummary has no VLANs** — The `list_interfaces()` function returns `InterfaceSummary` objects that don't include VLAN information. Must use raw pynautobot records for VLAN-per-interface data.

5. **`get_device_ips()` returns M2M-traversed IPs** — This is the correct way to get IPs per interface, not via `list_ip_addresses()` which returns IPs globally.

## Don't Hand-Roll

- **IP address parsing/validation** — Not needed. String comparison + simple `"/" in ip` check is sufficient for drift detection. Don't import `ipaddress` stdlib unless truly needed.
- **DiffSync for file-free drift** — Overkill. Direct set comparison is cleaner for IP/VLAN membership checks.
- **Custom pynautobot wrappers for VLAN access** — Use raw records directly. The pattern is established in `ipam.py`.

## Code Examples

### Fetching per-interface VLAN data (from ipam.py pattern)
```python
# This pattern is already used in ipam.py:list_vlans(device=X) lines 180-187
iface_records = list(client.api.dcim.interfaces.filter(device=device_name))
nb_vlan_map: dict[str, list[int]] = {}
for iface in iface_records:
    vlans: list[int] = []
    if hasattr(iface, "untagged_vlan") and iface.untagged_vlan:
        vid = getattr(iface.untagged_vlan, "vid", None)
        if vid is not None:
            vlans.append(int(vid))
    if hasattr(iface, "tagged_vlans") and iface.tagged_vlans:
        for vlan in iface.tagged_vlans:
            vid = getattr(vlan, "vid", None)
            if vid is not None:
                vlans.append(int(vid))
    if vlans:
        nb_vlan_map[iface.name] = vlans
```

### Input normalization (auto-detect)
```python
if isinstance(interfaces_data, list):
    # DeviceIPEntry shape → group by interface
    normalized = {}
    for entry in interfaces_data:
        iface = entry.get("interface") or entry.get("interface_name", "")
        normalized.setdefault(iface, {"ips": [], "vlans": []})
        if entry.get("address"):
            normalized[iface]["ips"].append(entry["address"])
else:
    # Dict shape — handle both {"ae0.0": {"ips": [...]}} and legacy {"ae0.0": [...]}
    ...
```

## Validation Architecture

### What to test
1. **Input normalization** — both shapes, legacy format, VLAN string→int, invalid data
2. **IP validation** — with prefix, without prefix, edge cases
3. **compare_device** — no drift, missing IP, extra IP, missing VLAN, missing interface, bare IP matching
4. **MCP tool** — registration check, returns dict
5. **CLI** — `--help` shows options, flag-based and JSON-based input

### How to verify
```bash
uv run pytest tests/test_drift.py -v  # Unit tests
uv run pytest tests/test_server.py -k "compare_device" -v  # Tool registration
uv run nautobot-mcp verify quick-drift --help  # CLI help
```

---

## RESEARCH COMPLETE

Key finding: Plan 07-01 task 07-01-03 needs adjustment — use raw pynautobot records for VLAN data instead of `list_interfaces()`. The `compare_device()` function should directly call `client.api.dcim.interfaces.filter()` for VLAN mapping.
