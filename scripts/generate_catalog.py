#!/usr/bin/env python3
"""Developer utility: discover Nautobot API endpoints and generate catalog data.

Usage:
    python scripts/generate_catalog.py [--url URL] [--token TOKEN] [--output FILE]

Introspects a Nautobot server's API root to discover available endpoints,
then outputs a catalog data structure for review and integration into
nautobot_mcp/catalog/core_endpoints.py.

This is NOT an MCP tool — it's a developer utility for catalog maintenance.
"""

import argparse
import json
import os
import sys
from typing import Optional


def discover_endpoints(url: str, token: str, verify_ssl: bool = False) -> dict:
    """Discover available API endpoints from Nautobot root.

    Args:
        url: Nautobot server URL.
        token: API authentication token.
        verify_ssl: Whether to verify SSL certificates.

    Returns:
        Dict of discovered endpoints grouped by app.
    """
    import requests

    headers = {"Authorization": f"Token {token}"}
    session = requests.Session()
    session.verify = verify_ssl

    # GET /api/ returns available apps
    resp = session.get(f"{url.rstrip('/')}/api/", headers=headers)
    resp.raise_for_status()
    api_root = resp.json()

    discovered: dict = {}
    for app_name, app_url in api_root.items():
        if app_name in ("status", "docs", "swagger", "graphql"):
            continue

        # GET each app root to find endpoint list
        try:
            app_resp = session.get(app_url, headers=headers)
            app_resp.raise_for_status()
            app_endpoints = app_resp.json()

            discovered[app_name] = {}
            for endpoint_name, endpoint_url in app_endpoints.items():
                discovered[app_name][endpoint_name] = {
                    "endpoint": endpoint_url.replace(url.rstrip("/"), ""),
                    "methods": ["GET", "POST", "PATCH", "DELETE"],
                    "filters": [],
                    "description": f"TODO: Add description for {endpoint_name}",
                }
        except Exception as e:
            print(f"  Warning: Could not discover {app_name}: {e}", file=sys.stderr)

    return discovered


def main(args: Optional[list] = None) -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Discover Nautobot API endpoints")
    parser.add_argument("--url", default=None, help="Nautobot URL (or use NAUTOBOT_URL env)")
    parser.add_argument("--token", default=None, help="API token (or use NAUTOBOT_TOKEN env)")
    parser.add_argument("--output", default=None, help="Output file (default: stdout)")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL verification")

    opts = parser.parse_args(args)

    # Resolve URL and token
    url = opts.url or os.environ.get("NAUTOBOT_URL")
    token = opts.token or os.environ.get("NAUTOBOT_TOKEN")

    if not url or not token:
        print(
            "Error: --url and --token required (or set NAUTOBOT_URL/NAUTOBOT_TOKEN env vars)",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Discovering endpoints from {url}...", file=sys.stderr)
    endpoints = discover_endpoints(url, token, verify_ssl=not opts.no_verify_ssl)

    output = json.dumps(endpoints, indent=2, sort_keys=True)

    if opts.output:
        with open(opts.output, "w") as f:
            f.write(output)
        print(f"Written to {opts.output}", file=sys.stderr)
    else:
        print(output)

    # Summary
    total = sum(len(v) for v in endpoints.values())
    print(f"\nDiscovered {total} endpoints across {len(endpoints)} apps", file=sys.stderr)


if __name__ == "__main__":
    main()
