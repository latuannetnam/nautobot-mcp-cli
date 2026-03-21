"""Entry point for the Nautobot MCP server.

Supports an optional --config flag to specify an absolute path to a YAML
config file. This is the recommended approach for Claude Desktop / sandbox
environments where CWD-based config discovery is unreliable.

    uv run python main.py --config /absolute/path/to/.nautobot-mcp.yaml
"""

import os
import sys

from nautobot_mcp.server import mcp

if __name__ == "__main__":
    # Parse --config <path> before handing off to FastMCP
    args = sys.argv[1:]
    if "--config" in args:
        idx = args.index("--config")
        if idx + 1 < len(args):
            config_path = args[idx + 1]
            os.environ["NAUTOBOT_CONFIG_FILE"] = config_path
            # Remove --config args so FastMCP doesn't see them
            args = args[:idx] + args[idx + 2:]
            sys.argv = [sys.argv[0]] + args

    mcp.run()
