---
phase: 6
title: "Device Summary & Enriched Interface Data"
decisions:
  summary_scope: "Core entities only (device + interfaces + IPs + VLANs + counts)"
  ip_enrichment: "Replace ip_addresses field type — change InterfaceSummary.ip_addresses from list[str] to list[DeviceIPEntry] using M2M traversal"
  cli_density: "Progressive — compact by default, --detail flag for full breakdown"
---

# Phase 6 Context: Device Summary & Enriched Interface Data

## Decisions

### 1. Device Summary Content Scope → Core entities only

`nautobot_device_summary("X")` returns:
- Device info (from `get_device`)
- Interfaces list (from `list_interfaces`)
- IPs mapped to interfaces (from `get_device_ips`)
- VLANs on device (from `list_vlans(device=X)`)
- Counts: interface_count, ip_count, vlan_count
- Link state stats: enabled_count, disabled_count

No golden config or config backup data — agents query those separately.

### 2. IP Enrichment Approach → Replace field type

Change `InterfaceSummary.ip_addresses` from `list[str]` to `list[DeviceIPEntry]` when `include_ips=True`.

- When `include_ips=False` (default): `ip_addresses` remains `list[str]` from pynautobot
- When `include_ips=True`: use M2M traversal, populate `ip_addresses` as `list[DeviceIPEntry]` with rich data (address, ip_id, status)
- This is technically a type change on the field, but since the field is often empty anyway (pynautobot doesn't reliably populate it), the breaking risk is minimal
- ENRICH-02 requires batch query — collect all interface IDs first, then batch M2M lookup

### 3. CLI Output Density → Progressive

`nautobot-mcp devices summary DEVICE`:
- Default: compact overview with counts
- `--detail`: full interface + IP breakdown

## Code Context

### Reusable assets
- `get_device_ips()` in `ipam.py` — already does interface → M2M → IP traversal
- `list_interfaces()` in `interfaces.py` — already filters by device
- `list_vlans(device=X)` in `ipam.py` — already filters VLANs by device
- `DeviceSummary`, `InterfaceSummary`, `DeviceIPEntry` models exist

### Key patterns
- Core function returns Pydantic model → MCP tool calls `.model_dump()` → CLI formats output
- M2M traversal for IPs via `ip_address_to_interface`
- All tools wrapped with `try/except + handle_error(e)`

### Integration points
- `server.py` line 204: `nautobot_list_interfaces` — needs `include_ips` parameter
- `devices.py`: new `get_device_summary()` function needed
- `cli/devices.py`: new `summary` command

## Deferred Ideas
None.
