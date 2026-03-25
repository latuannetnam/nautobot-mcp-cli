# Phase 15: Catalog Engine & Core Endpoints - Research

**Researched:** 2026-03-24
**Status:** Complete

## Research Objective

Understand current codebase patterns, identify reusable assets, and map out what the catalog engine needs to index to inform planning.

## Codebase Analysis

### 1. Current Server Architecture (`server.py` — 3,883 lines, 165 tools)

Pattern for every tool:
```python
@mcp.tool(name="nautobot_{operation}")
def nautobot_{operation}(params...) -> dict:
    """Docstring with Args/Returns."""
    try:
        client = get_client()
        result = domain_module.function(client, **params)
        return result.model_dump()
    except Exception as e:
        handle_error(e)
```

Key infrastructure to preserve:
- `get_client()` singleton (`_client: NautobotClient | None`)
- `handle_error()` translates `NautobotMCPError` → `ToolError`
- `FastMCP("Nautobot MCP Server")` initialization

### 2. pynautobot Accessor Patterns (`client.py`)

Core app accessors (properties on `NautobotClient`):
- `client.api.dcim` → devices, interfaces, device_types, device_roles, manufacturers, platforms, locations
- `client.api.ipam` → prefixes, ip_addresses, vlans, namespaces
- `client.api.circuits` → circuits, providers, circuit_types, circuit_terminations
- `client.api.tenancy` → tenants, tenant_groups

Plugin accessors:
- `client.api.plugins.golden_config` → compliance_rules, golden_configs
- `client.api.plugins.netnam_cms_core` → all CMS endpoints (38+)

pynautobot API:
- `endpoint.all()` — list all
- `endpoint.filter(**kwargs)` — filtered list
- `endpoint.get(id=uuid)` or `endpoint.get(name=name)` — single object
- `endpoint.create(**data)` — create
- Record `.save()` — update (set attrs first)
- Record `.delete()` — delete

### 3. CMS Endpoint Registry (`cms/client.py`)

```python
CMS_ENDPOINTS = {
    # Routing (8 entries)
    "juniper_static_routes": "JuniperStaticRoute",
    "juniper_static_route_nexthops": "JuniperStaticRouteNexthop",
    "juniper_static_route_qualified_nexthops": "JuniperStaticRouteQualifiedNexthop",
    "juniper_bgp_groups": "JuniperBGPGroup",
    "juniper_bgp_neighbors": "JuniperBGPNeighbor",
    "juniper_bgp_address_families": "JuniperBGPAddressFamily",
    "juniper_bgp_policy_associations": "JuniperBGPPolicyAssociation",
    "juniper_bgp_received_routes": "JuniperBGPReceivedRoute",
    # Interfaces (7 entries)
    "juniper_interface_units": "JuniperInterfaceUnit",
    "juniper_interface_families": "JuniperInterfaceFamily",
    "juniper_interface_family_filters": "JuniperInterfaceFamilyFilter",
    "juniper_interface_family_policers": "JuniperInterfaceFamilyPolicer",
    "juniper_interface_vrrp_groups": "JuniperInterfaceVRRPGroup",
    "vrrp_track_routes": "VRRPTrackRoute",
    "vrrp_track_interfaces": "VRRPTrackInterface",
    # Firewalls (7 entries)
    "juniper_firewall_filters": "JuniperFirewallFilter",
    "juniper_firewall_terms": "JuniperFirewallTerm",
    "juniper_firewall_match_conditions": "JuniperFirewallFilterMatchCondition",
    "juniper_firewall_actions": "JuniperFirewallFilterAction",
    "juniper_firewall_policers": "JuniperFirewallPolicer",
    "juniper_firewall_policer_actions": "JuniperFirewallPolicerAction",
    "juniper_firewall_match_condition_prefix_lists": "JuniperFirewallMatchConditionToPrefixList",
    # Policies (15 entries)
    "juniper_policy_statements": "JuniperPolicyStatement",
    "jps_terms": "JPSTerm",
    "jps_match_conditions": "JPSMatchCondition",
    "jps_match_condition_route_filters": "JPSMatchConditionRouteFilter",
    "jps_match_condition_prefix_lists": "JPSMatchConditionPrefixList",
    "jps_match_condition_communities": "JPSMatchConditionCommunity",
    "jps_match_condition_as_paths": "JPSMatchConditionAsPath",
    "jps_actions": "JPSAction",
    "jps_action_communities": "JPSActionCommunity",
    "jps_action_as_paths": "JPSActionAsPath",
    "jps_action_load_balances": "JPSActionLoadBalance",
    "jps_action_install_nexthops": "JPSActionInstallNexthop",
    "juniper_policy_as_paths": "JuniperPolicyAsPath",
    "juniper_policy_communities": "JuniperPolicyCommunity",
    "juniper_policy_prefix_lists": "JuniperPolicyPrefixList",
    "juniper_policy_prefixes": "JuniperPolicyPrefix",
    # ARP (1 entry)
    "juniper_arp_entries": "JuniperArpEntry",
}
```

Total: 38 entries across 5 domains. All support full CRUD via generic `cms_list/get/create/update/delete` helpers.

### 4. Composite Workflow Functions (for WORKFLOW_REGISTRY)

These exist in domain modules and will become `run_workflow` targets:

| Workflow Name | Function | File | Lines |
|---------------|----------|------|-------|
| `bgp_summary` | `get_device_bgp_summary()` | `cms/routing.py:598` | N+1 query |
| `routing_table` | `get_device_routing_table()` | `cms/routing.py:667` | N+1 query |
| `firewall_summary` | `get_device_firewall_summary()` | `cms/firewalls.py:647` | N+1 query |
| `interface_detail` | `get_interface_detail()` | `cms/interfaces.py:652` | N+1 query |
| `onboard_config` | `onboard_config()` | `onboarding.py:64` | 499 LOC |
| `compare_device` | `compare_device()` | `drift.py:101` | 256 LOC |
| `verify_data_model` | `verify_data_model()` | `verification.py:200` | ~150 LOC |
| `verify_compliance` | via CLI `verify_compliance_cmd()` | `cli/verify.py:20` | ~80 LOC |

CMS drift functions (`compare_bgp`, `compare_routes`) are exposed as MCP tools in `server.py` — need to locate the actual domain functions.

### 5. Core Endpoint Inventory (for Static Catalog)

From `server.py` tool definitions, the curated core endpoints used for network automation:

**DCIM:**
- `devices` — list, get, create, update, delete + `device_summary`
- `interfaces` — list (with IP enrichment), get, create, update + `assign_ip_to_interface`

**IPAM:**
- `prefixes` — list, create
- `ip_addresses` — list, create + `get_device_ips`
- `vlans` — list, create

**Tenancy (via Organization module):**
- `tenants` — list, get, create, update
- `locations` — list, get, create, update

**Circuits:**
- `circuits` — list, get, create, update
- `providers` — list, get, create
- `circuit_types` — list, get, create

**Golden Config (plugin):**
- `golden_configs` — list, get
- `compliance_rules` — list, get

### 6. Token Budget Analysis

Estimating catalog response size using design doc format:
- Core endpoints (~15 entries): ~600 tokens
- CMS endpoints (38 entries, grouped): ~800 tokens if condensed, ~1500 if full
- Workflows (10 entries): ~400 tokens

**Full unfiltered catalog: ~1800-2500 tokens** — exceeds soft 1500 target.

**Mitigation options:**
1. Collapse CMS to domain-level summaries in unfiltered view (~200 tokens for CMS)
2. Shorten descriptions to <10 words each
3. Use `domain` filter — each filtered view stays well under 1500

## Validation Architecture

### Dimension 1: Code correctness
- All catalog entries map to real pynautobot accessors
- CMS auto-discovery reads live `CMS_ENDPOINTS` dict

### Dimension 2: API contract
- `nautobot_api_catalog(domain=None)` returns all domains
- `nautobot_api_catalog(domain="dcim")` returns only DCIM

### Dimension 3: Integration
- Catalog module importable by new `server.py`
- No circular imports with `cms/client.py`

### Dimension 4: Performance
- Static catalog is dict lookup — O(1)
- CMS discovery at import time, not per-call

---

## RESEARCH COMPLETE

Key findings summary:
1. **38 CMS endpoints** auto-discoverable from `CMS_ENDPOINTS` dict
2. **~15 curated core endpoints** across dcim/ipam/tenancy/circuits
3. **10 composite workflows** already exist as domain functions
4. **Token budget needs CMS collapsing** for unfiltered view
5. **pynautobot accessor pattern** well-established: `client.api.{app}.{endpoint}`
6. **No existing catalog module** — this is greenfield code

---
*Research completed: 2026-03-24*
