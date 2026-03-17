"""Output formatters for the Nautobot MCP CLI.

Provides table and JSON output formatting for CLI commands.
"""

from __future__ import annotations

import json
from typing import Any

from tabulate import tabulate

# ---------------------------------------------------------------------------
# Column definitions per resource type
# ---------------------------------------------------------------------------

DEVICE_COLUMNS = ["name", "status", "location", "role", "device_type", "platform"]
INTERFACE_COLUMNS = ["name", "type", "enabled", "description"]
PREFIX_COLUMNS = ["prefix", "namespace", "status", "location"]
IP_COLUMNS = ["address", "namespace", "status", "dns_name"]
VLAN_COLUMNS = ["vid", "name", "status", "location"]
TENANT_COLUMNS = ["name", "description"]
LOCATION_COLUMNS = ["name", "location_type", "parent"]
CIRCUIT_COLUMNS = ["cid", "provider", "circuit_type", "status"]


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def format_table(data: list[dict], columns: list[str]) -> str:
    """Format a list of dicts as a plain table using tabulate.

    Args:
        data: List of dicts (each representing a row).
        columns: Column keys to include in the table.

    Returns:
        Formatted table string.
    """
    rows = []
    for item in data:
        row = [item.get(col, "") for col in columns]
        rows.append(row)
    return tabulate(rows, headers=columns, tablefmt="simple")


def format_json(data: Any) -> str:
    """Format data as indented JSON string.

    Args:
        data: Any JSON-serializable data.

    Returns:
        Pretty-printed JSON string.
    """
    return json.dumps(data, indent=2, default=str)


def output(data: dict, json_mode: bool, columns: list[str]) -> None:
    """Output data in table or JSON format.

    Args:
        data: Data dict (expected to have 'results' key for table mode).
        json_mode: If True, output JSON; otherwise output table.
        columns: Column keys for table output.
    """
    if json_mode:
        print(format_json(data))
    else:
        results = data.get("results", [])
        if results:
            print(format_table(results, columns))
        else:
            print("No results found.")


def output_single(data: dict, json_mode: bool, columns: list[str]) -> None:
    """Output a single resource in table or JSON format.

    Args:
        data: Single resource dict.
        json_mode: If True, output JSON; otherwise output table.
        columns: Column keys for table output.
    """
    if json_mode:
        print(format_json(data))
    else:
        print(format_table([data], columns))
