# Phase 4 Research: Onboarding, Verification & Agent Skills

**Researched:** 2026-03-17
**Confidence:** High (core patterns verified against codebase + official docs)

## Standard Stack

### Config Onboarding
- **No new dependencies needed** — use existing `nautobot_mcp` CRUD functions (`create_device`, `create_interface`, `create_ip_address`, `create_prefix`, `create_vlan`)
- Onboarding is a one-directional sync: `ParsedConfig` → Nautobot
- All target CRUD operations already exist and return pydantic models

### Data Model Verification
- **DiffSync** (`pip install diffsync`) — Nautobot ecosystem's standard library for comparing/synchronizing datasets
  - Provides `DiffSyncModel` (Pydantic-based) + `Adapter` pattern
  - Built-in diff engine with `diff_from()` / `diff_to()` methods
  - Produces structured diff output with create/update/delete actions
  - Used by Nautobot Device Onboarding (v4+) and SSoT plugins
- **Alternative**: Custom comparison logic using existing CRUD (simpler but less feature-rich)
- **Recommendation**: Use DiffSync for VERIFY-02 (object-by-object comparison) — it's battle-tested and designed exactly for this use case. Skip it for onboarding (one-directional, simpler logic).

### Agent Skills
- No new dependencies — skills are markdown guide files in `.agent/skills/`
- Skills reference existing MCP tool names for agent orchestration

## Architecture Patterns

### Onboarding Architecture
```
ParsedConfig → OnboardingEngine → (dry-run plan | committed changes)
                 │
                 ├── resolve_device() → find or create device
                 ├── resolve_interfaces() → match, create, update
                 ├── resolve_ip_addresses() → auto-create prefixes, assign IPs
                 └── resolve_vlans() → match by vid+name
```

**Pattern**: The onboarding engine is a **stateful operation** that:
1. Loads parsed config (`ParsedConfig` from Phase 3 parser)
2. Loads current Nautobot state for the target device
3. Computes a plan (list of `OnboardAction` entries)
4. Either returns the plan (dry-run) or executes it (commit)

**Model**: `OnboardAction` captures each planned change:
```python
class OnboardAction(BaseModel):
    action: str  # "create", "update", "skip"
    object_type: str  # "interface", "ip_address", "prefix", "vlan", "device"
    name: str  # object identifier
    details: dict  # what will be created/changed
    reason: str  # why (e.g., "not found in Nautobot", "description changed")
```

**Model**: `OnboardResult` wraps the full operation result:
```python
class OnboardResult(BaseModel):
    device: str
    dry_run: bool
    summary: OnboardSummary  # counts by action type
    actions: list[OnboardAction]
    warnings: list[str]
```

### Verification Architecture (DiffSync-based)

```
Live Router State → ParsedConfig ─┐
                                   ├→ DiffSync adapters → Diff → DriftReport
Nautobot Records ─────────────────┘
```

**DiffSync integration pattern:**
1. Define `DiffSyncModel` subclasses for: `InterfaceModel`, `IPAddressModel`, `VLANModel`
2. Create two adapters:
   - `ParsedConfigAdapter` — loads from `ParsedConfig` object
   - `NautobotAdapter` — loads from Nautobot API using existing CRUD functions
3. `adapter_nautobot.diff_from(adapter_parsed)` → produces structured diff
4. Translate DiffSync diff → `DriftReport` model

**Model**: `DriftReport` (grouped by type):
```python
class DriftItem(BaseModel):
    name: str
    status: str  # "missing_in_nautobot", "missing_on_device", "changed"
    nautobot_value: dict | None
    device_value: dict | None
    changed_fields: dict  # {"field": {"nautobot": x, "device": y}}

class DriftSection(BaseModel):
    missing: list[DriftItem]
    extra: list[DriftItem]
    changed: list[DriftItem]

class DriftReport(BaseModel):
    device: str
    source: str  # "jmcp" or "provided"
    interfaces: DriftSection
    ip_addresses: DriftSection
    vlans: DriftSection
    summary: dict  # {"total_drifts": N, "by_type": {...}}
```

### Agent Skill Guide Structure

Skills are `.agent/skills/{skill-name}/SKILL.md` markdown files:
```markdown
---
name: onboard-router-config
description: Parse live router config and onboard into Nautobot
---

## Prerequisites
- nautobot-mcp-cli MCP server running
- jmcp MCP server running (for live config pull)
- Target device accessible via jmcp

## Steps
1. **Pull live config** — Call jmcp: `execute_junos_command(router, "show configuration | display json")`
2. **Parse config** — Call: `nautobot_parse_junos_config(config_json=<output>)`
3. **Dry-run onboard** — Call: `nautobot_onboard_config(device_name, parsed_config, dry_run=true)`
4. **Review plan** — Present the dry-run results to user
5. **Commit** — If approved, call: `nautobot_onboard_config(device_name, parsed_config, dry_run=false, commit=true)`
```

## Don't Hand-Roll

| Component | Use Instead | Why |
|-----------|------------|-----|
| Object-by-object comparison | DiffSync library | Battle-tested, handles create/update/delete diffs, used by Nautobot ecosystem |
| Prefix computation from IP | Python `ipaddress` stdlib | `ipaddress.ip_interface("10.0.0.1/30").network` gives the prefix |
| Device type detection from parsed config | Existing `ParsedConfig.platform` field | Already auto-detected by JunOS parser |

## Common Pitfalls

### Onboarding
1. **Nautobot v2 Namespace requirement** — IPs and prefixes require a Namespace (default: "Global"). The existing `create_ip_address()` and `create_prefix()` already handle this with `namespace="Global"` default.
2. **Device type / role must exist** — `create_device()` requires `device_type`, `role`, and `location` to already exist. The onboarding engine must resolve these first.
3. **Interface type mapping** — JunOS interface names (ge-, xe-, et-) need to map to Nautobot interface types (1000BASE-T, 10GBASE-X-SFP+, etc.). A lookup table is required.
4. **Idempotency race conditions** — Between "check exists" and "create", another process could create the same object. Use pynautobot's error handling to catch 409 Conflict and retry as update.
5. **IP assignment to interface** — `assign_ip_to_interface()` already exists but requires both the IP and interface to exist in Nautobot first.

### Verification
1. **DiffSync model identifiers** — Must use correct `_identifiers` tuple to match objects across adapters (e.g., `("name",)` for interfaces, `("address",)` for IPs).
2. **Attribute comparison scope** — Not all attributes should be compared (e.g., Nautobot-only fields like `id`, `created`, `last_updated` should be excluded).
3. **Live config freshness** — jmcp output represents the running config at a point in time. The skill guide should note that stale configs may cause false drifts.

### Agent Skills
1. **Step dependencies** — Skills must clearly document which steps depend on previous step outputs. Agent must pass outputs between MCP tool calls.
2. **Error handling in guides** — Skills should document expected errors and recovery actions (e.g., "if device not found, try creating it first").

## Code Examples

### Onboarding — resolve or create interface
```python
def resolve_interface(client, device_id, parsed_iface, dry_run=True):
    """Check if interface exists, plan create/update/skip."""
    existing = client.api.dcim.interfaces.get(
        device_id=device_id, name=parsed_iface.name
    )
    if existing is None:
        return OnboardAction(
            action="create", object_type="interface",
            name=parsed_iface.name,
            details={"type": map_interface_type(parsed_iface.name), ...}
        )
    # Compare attributes
    changes = {}
    if existing.description != parsed_iface.description:
        changes["description"] = parsed_iface.description
    if changes and update_existing:
        return OnboardAction(action="update", ...)
    return OnboardAction(action="skip", ...)
```

### DiffSync — Interface model
```python
from diffsync import Adapter, DiffSyncModel

class InterfaceModel(DiffSyncModel):
    _modelname = "interface"
    _identifiers = ("device_name", "name",)
    _attributes = ("description", "enabled", "interface_type",)

    device_name: str
    name: str
    description: str = ""
    enabled: bool = True
    interface_type: str = ""

class NautobotAdapter(Adapter):
    interface = InterfaceModel
    top_level = ["interface"]

    def load(self):
        for iface in list_interfaces(self.client, device=self.device_name).results:
            self.add(InterfaceModel(
                device_name=self.device_name,
                name=iface.name,
                description=iface.description,
                enabled=iface.enabled,
                interface_type=iface.type,
            ))
```

### Prefix auto-creation from IP
```python
import ipaddress

def auto_create_prefix(client, ip_with_mask: str, namespace: str = "Global"):
    """Auto-create the smallest containing prefix for an IP."""
    iface = ipaddress.ip_interface(ip_with_mask)
    network = str(iface.network)  # e.g., "10.0.0.0/30"
    # Check if prefix exists
    existing = client.api.ipam.prefixes.get(prefix=network, namespace=namespace)
    if existing:
        return PrefixSummary.from_nautobot(existing)
    return create_prefix(client, prefix=network, namespace=namespace)
```

---

*Research completed: 2026-03-17*
*Phase: 04-onboarding-verification-agent-skills*
