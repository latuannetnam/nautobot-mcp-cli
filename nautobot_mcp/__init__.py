"""nautobot-mcp-cli: MCP server and CLI for Nautobot network automation.

This package provides a Python client library for interacting with Nautobot,
with curated pydantic models and structured error handling.

# MCP Server: nautobot_mcp.server (import separately — requires fastmcp)
# CLI: nautobot_mcp.cli.app (registered as entry point — requires typer)
"""

__version__ = "0.1.0"

# Core classes
from nautobot_mcp.client import NautobotClient
from nautobot_mcp.config import NautobotProfile, NautobotSettings

# Exceptions
from nautobot_mcp.exceptions import (
    NautobotAPIError,
    NautobotAuthenticationError,
    NautobotConnectionError,
    NautobotMCPError,
    NautobotNotFoundError,
    NautobotValidationError,
)

# Domain operations
from nautobot_mcp.circuits import create_circuit, get_circuit, list_circuits, update_circuit
from nautobot_mcp.devices import create_device, delete_device, get_device, list_devices, update_device
from nautobot_mcp.interfaces import (
    assign_ip_to_interface,
    create_interface,
    get_interface,
    list_interfaces,
    update_interface,
)
from nautobot_mcp.ipam import (
    create_ip_address,
    create_prefix,
    create_vlan,
    list_ip_addresses,
    list_prefixes,
    list_vlans,
)
from nautobot_mcp.organization import (
    create_location,
    create_tenant,
    get_location,
    get_tenant,
    list_locations,
    list_tenants,
    update_location,
    update_tenant,
)
from nautobot_mcp.golden_config import (
    get_intended_config,
    get_backup_config,
    list_compliance_features,
    create_compliance_feature,
    delete_compliance_feature,
    list_compliance_rules,
    create_compliance_rule,
    update_compliance_rule,
    delete_compliance_rule,
    get_compliance_results,
    quick_diff_config,
)

# Onboarding
from nautobot_mcp.onboarding import onboard_config

# Verification
from nautobot_mcp.verification import verify_config_compliance, verify_data_model

__all__ = [
    # Version
    "__version__",
    # Core
    "NautobotClient",
    "NautobotProfile",
    "NautobotSettings",
    # Exceptions
    "NautobotMCPError",
    "NautobotConnectionError",
    "NautobotAuthenticationError",
    "NautobotNotFoundError",
    "NautobotValidationError",
    "NautobotAPIError",
    # Devices
    "list_devices",
    "get_device",
    "create_device",
    "update_device",
    "delete_device",
    # Interfaces
    "list_interfaces",
    "get_interface",
    "create_interface",
    "update_interface",
    "assign_ip_to_interface",
    # IPAM
    "list_prefixes",
    "create_prefix",
    "list_ip_addresses",
    "create_ip_address",
    "list_vlans",
    "create_vlan",
    # Organization
    "list_tenants",
    "get_tenant",
    "create_tenant",
    "update_tenant",
    "list_locations",
    "get_location",
    "create_location",
    "update_location",
    # Circuits
    "list_circuits",
    "get_circuit",
    "create_circuit",
    "update_circuit",
    # Golden Config
    "get_intended_config",
    "get_backup_config",
    "list_compliance_features",
    "create_compliance_feature",
    "delete_compliance_feature",
    "list_compliance_rules",
    "create_compliance_rule",
    "update_compliance_rule",
    "delete_compliance_rule",
    "get_compliance_results",
    "quick_diff_config",
    # Onboarding
    "onboard_config",
    # Verification
    "verify_config_compliance",
    "verify_data_model",
]

