# Phase 3: Golden Config & Config Parsing — Research

**Researched:** 2026-03-17
**Status:** Complete

## 1. Golden Config Plugin API Access

### pynautobot Plugin Pattern
- Access via `api.plugins.golden_config` (pynautobot auto-discovers plugin endpoints)
- Plugin endpoints live under `/api/plugins/golden-config/`
- Standard CRUD operations available on all models via pynautobot's `.all()`, `.get()`, `.create()`, `.update()`, `.delete()`
- Same pagination, error handling, and auth as core Nautobot endpoints

### Golden Config API Models
Key serializers/endpoints discovered:
- **`golden-config`** — Main config objects (intended/backup/compliance per device)
- **`compliance-feature`** — Feature labels (NTP, SNMP, BGP, etc.) — CRUD supported
- **`compliance-rule`** — Rules per feature per platform — CRUD supported
- **`config-compliance`** — Compliance results per device per feature
- **`config-replace`** — Config push operations (out of Phase 3 scope)

### Key API Patterns
```python
# Access plugin endpoints
gc = api.plugins.golden_config

# List compliance features
features = gc.compliance_feature.all()

# Get compliance rules for a feature
rules = gc.compliance_rule.filter(feature=feature_id)

# Get config for a device
configs = gc.golden_config.filter(device=device_id)
# Each config object has: intended_config, backup_config, compliance_config

# Get compliance results
results = gc.config_compliance.filter(device=device_id)
# Each result has: feature, actual, intended, missing, extra, ordered, compliance
```

### NautobotClient Extension
Current `NautobotClient` has properties: `dcim`, `ipam`, `tenancy`, `circuits`
Need to add: `golden_config` property → `self.api.plugins.golden_config`
Pattern: Same lazy property as existing endpoint accessors

## 2. JunOS JSON Config Structure

### How to Get JSON Output
- CLI: `show configuration | display json`
- Via jmcp: `execute_junos_command(router, "show configuration | display json")`
- Also supports `| display xml` for XML output
- Section-specific: `show configuration interfaces | display json`

### JSON Structure
```json
{
  "configuration": {
    "@": { "junos:changed-seconds": "1234567890" },
    "interfaces": {
      "interface": [
        {
          "name": "ge-0/0/0",
          "description": "To-Router-B",
          "unit": [
            {
              "name": "0",
              "family": {
                "inet": {
                  "address": [
                    { "name": "10.0.0.1/30" }
                  ]
                }
              }
            }
          ]
        }
      ]
    },
    "routing-instances": { ... },
    "protocols": { ... },
    "firewall": { ... },
    "system": { ... },
    "vlans": {
      "vlan": [
        { "name": "MGMT", "vlan-id": "100" }
      ]
    }
  }
}
```

### Key JunOS JSON Patterns
- Top-level key is always `"configuration"`
- All list items are arrays even if single element
- Field names use hyphens (JunOS style): `routing-instances`, `vlan-id`
- `"name"` is the universal identifier key
- `@` prefixed keys are metadata attributes
- Platform-specific sections:
  - **MX**: `routing-instances`, `protocols` (BGP/OSPF/MPLS)
  - **EX**: `vlans`, `ethernet-switching`, `protocols` (RSTP/LLDP)
  - **SRX**: `security` (zones, policies, NAT), `applications`

### Section-Specific Parsing
Can request specific sections: `show configuration interfaces | display json`
This reduces payload size for targeted parsing.

## 3. netutils Integration

### Library Mapper
- `netutils.lib_mapper` provides cross-library platform name mapping
- Juniper JunOS maps to `"juniper_junos"` as `network_os`
- Golden Config uses this mapping to select the right parser
- Our `VendorParser` registry should use same identifiers

### JunosConfigParser
- `netutils.config.parser.JunosConfigParser` handles curly-brace JunOS text configs
- Useful for text-based fallback (e.g., parsing Golden Config backup text)
- NOT needed for JSON-first approach (our primary path)
- May be useful for compliance text diff comparisons

### Platform Detection
- JunOS JSON config has identifiers:
  - `security` block → SRX platform
  - `ethernet-switching` in interfaces → EX platform
  - `routing-instances` with VRFs → MX platform (typical)
  - `chassis` → can contain device model info
  - `system` → contains hostname, domain-name

## 4. Compliance Architecture

### Server-Side (Golden Config)
- Compliance jobs run on Nautobot server via Nornir
- Jobs compare intended vs actual (backup) configs
- Results stored in `config_compliance` model per device per feature
- Each result has: `compliance` (bool), `actual`, `intended`, `missing`, `extra`, `ordered`
- Can trigger via API: POST to job endpoint or use GraphQL

### Client-Side Quick Diff
- Python `difflib` for text comparison (unified diff format)
- Can diff specific config sections (pull intended + backup via API, diff locally)
- Simpler than full compliance — no ordered/unordered awareness
- Useful for quick spot checks without triggering full compliance job

### Job Execution
- Nautobot jobs are async — return job ID
- Poll job status: `api.extras.jobs.get(id=job_id)` → check `status`
- Job statuses: `pending`, `running`, `completed`, `failed`, `errored`
- For single device: typically completes in seconds
- For batch: may take minutes depending on device count

## 5. Existing Code Patterns to Follow

### Domain Module Pattern
```python
# From devices.py — pattern for all domain modules
def list_devices(client: NautobotClient, **filters) -> ListResponse[DeviceSummary]:
    """List devices with optional filtering."""
    try:
        devices = client.dcim.devices.filter(**filters)
        results = [DeviceSummary.from_nautobot(d) for d in devices]
        return ListResponse(count=len(results), results=results)
    except Exception as e:
        client._handle_api_error(e, "list", "Device")

def get_device(client: NautobotClient, name_or_id: str) -> DeviceDetail:
    """Get detailed device information."""
    ...
```

### Pydantic Model Pattern
```python
# From models/ — pattern for all data models
class DeviceSummary(BaseModel):
    id: str
    name: str
    status: str
    ...
    
    @classmethod
    def from_nautobot(cls, nb_record) -> "DeviceSummary":
        return cls(
            id=str(nb_record.id),
            name=nb_record.name,
            status=str(nb_record.status),
            ...
        )
```

### MCP Tool Pattern
```python
# From server.py — pattern for all MCP tools
@mcp.tool()
async def nautobot_list_devices(...) -> str:
    """List devices with optional filtering. ..."""
    client = NautobotClient()
    result = list_devices(client, **filters)
    return result.model_dump_json()
```

## 6. Pitfalls and Risks

| Risk | Mitigation |
|------|------------|
| Golden Config plugin not installed on target Nautobot | Check plugin availability on first API call, raise clear error |
| JunOS JSON output varies by Junos version | Test with jmcp on real devices, handle optional fields gracefully |
| Compliance job may timeout for many devices | Implement configurable timeout, return partial results |
| pynautobot plugin endpoint naming may differ | Verify exact endpoint names against live Nautobot API docs at `/api/docs/` |
| Large configs may exceed jmcp command timeout | Use section-specific queries when possible |

---
*Research completed: 2026-03-17*
