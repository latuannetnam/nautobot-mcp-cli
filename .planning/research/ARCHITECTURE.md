# Architecture Research: Nautobot MCP CLI

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     AI Agent (Claude, etc.)              │
│                                                         │
│  Uses MCP tools from both servers to orchestrate tasks  │
└──────────────┬─────────────────────┬────────────────────┘
               │                     │
               ▼                     ▼
┌──────────────────────┐  ┌──────────────────────┐
│  nautobot-mcp-cli    │  │       jmcp            │
│  (This project)      │  │  (Juniper MCP Server) │
│                      │  │                       │
│  MCP Server + CLI    │  │  Direct router access │
│  + Agent Skills      │  │  via NETCONF/SSH      │
└──────────┬───────────┘  └──────────┬────────────┘
           │                         │
           ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐
│  Nautobot Server     │  │  Network Devices     │
│  (REST API)          │  │  (Juniper, Cisco)    │
│  nautobot.netnam.vn  │  │                      │
└──────────────────────┘  └──────────────────────┘
```

## Component Architecture

```
nautobot-mcp-cli/
├── nautobot_mcp/              # Shared core library
│   ├── client/                # Nautobot API client (pynautobot wrapper)
│   │   ├── base.py            # Connection, auth, base client
│   │   ├── devices.py         # Device operations
│   │   ├── interfaces.py      # Interface operations
│   │   ├── ipam.py            # IPAM operations (prefix, IP, VLAN)
│   │   ├── organization.py    # Org operations (tenant, location)
│   │   ├── circuits.py        # Circuit operations
│   │   └── golden_config.py   # Golden Config plugin API
│   ├── parsers/               # Config parsers (vendor-specific)
│   │   ├── base.py            # Abstract parser interface
│   │   └── junos.py           # JunOS config parser
│   ├── comparators/           # Config comparison logic
│   │   ├── config_diff.py     # Config text diff
│   │   └── model_diff.py      # Data model comparison
│   └── models/                # Shared data models (pydantic)
│       ├── device.py
│       ├── interface.py
│       └── ipam.py
├── mcp_server/                # MCP server layer (thin)
│   ├── server.py              # FastMCP server setup
│   └── tools/                 # MCP tool definitions
│       ├── devices.py         # Device tools
│       ├── interfaces.py      # Interface tools
│       ├── ipam.py            # IPAM tools
│       ├── golden_config.py   # Golden Config tools
│       └── workflows.py       # Workflow/skill tools
├── cli/                       # CLI layer (thin)
│   ├── app.py                 # Typer app setup
│   └── commands/              # CLI command groups
│       ├── devices.py
│       ├── interfaces.py
│       ├── ipam.py
│       └── golden_config.py
├── skills/                    # Agent skill definitions
│   ├── onboard_config.py      # Config onboarding workflow
│   └── verify_compliance.py   # Compliance verification workflow
├── pyproject.toml
└── tests/
```

## Data Flow

### Config Onboarding Flow
```
1. Agent calls jmcp: get_junos_config(router_name)
2. Agent receives raw JunOS config text
3. Agent calls nautobot-mcp: parse_junos_config(config_text)
4. Parser extracts: interfaces, IPs, VLANs, etc.
5. Agent calls nautobot-mcp: onboard_parsed_config(parsed_data)
6. Tool creates/updates Nautobot objects via pynautobot
7. Returns: summary of changes made
```

### Compliance Verification Flow
```
1. Agent calls nautobot-mcp: get_device_intended_config(device_name)
2. Agent calls jmcp: get_junos_config(router_name)
3. Agent calls nautobot-mcp: compare_configs(intended, actual)
4. Comparator returns: structured drift report
5. Agent presents: human-readable compliance summary
```

### Data Model Verification Flow
```
1. Agent calls nautobot-mcp: get_device_interfaces(device_name)
2. Agent calls jmcp: execute_junos_command("show interfaces")
3. Agent calls nautobot-mcp: compare_interfaces(nautobot_data, live_data)
4. Returns: discrepancies between Nautobot records and live state
```

## Build Order (Dependencies)

1. **Core client** — Authentication, connection, base API client
2. **Data model operations** — Devices, interfaces, IPAM (depends on client)
3. **MCP server** — Expose core operations as tools (depends on data model ops)
4. **CLI** — Same operations via command line (depends on data model ops)
5. **Config parsers** — JunOS parser (independent of above)
6. **Comparators** — Diff logic (depends on parsers + data model)
7. **Golden Config** — Plugin API integration (depends on client)
8. **Workflow skills** — Chain operations across tools (depends on all above)
