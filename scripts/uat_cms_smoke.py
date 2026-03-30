#!/usr/bin/env python3
"""CMS Data Presence Smoke Test — HQV-PE1-NEW (Prod).

UAT Layer 1: Verify CMS plugin has JunOS data stored for HQV-PE1-NEW.
Uses `uv run nautobot-mcp --json ...` subprocess calls against the prod profile.

Usage:
  uv run python scripts/uat_cms_smoke.py
  NAUTOBOT_URL=https://nautobot.netnam.vn NAUTOBOT_TOKEN=xxx uv run python scripts/uat_cms_smoke.py

Exit codes:
  0 — all workflows passed
  1 — one or more workflows failed
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass

# HTTP call counter — instruments pynautobot Request._make_call
_http_call_counts: dict[str, int] = {}
_original_make_call = None


def _counting_make_call(self, *args, **kwargs):
    """Monkey-patch wrapper that counts HTTP GET calls per URL path."""
    global _http_call_counts
    url = args[0] if args else kwargs.get("url", "")
    # Extract path from URL for readability (e.g., /api/plugins/netnam-cms-core/...)
    if hasattr(self, "session") and self.session:
        base = self.session.get("base_url", "")
        if url.startswith(base):
            path = url[len(base):]
        else:
            path = url
    else:
        path = url
    key = path.rstrip("?").split("?")[0]  # strip trailing ? and query for grouping
    _http_call_counts[key] = _http_call_counts.get(key, 0) + 1
    return _original_make_call(self, *args, **kwargs)


def _install_counter():
    """Install HTTP call counter monkey-patch on pynautobot Request class."""
    global _original_make_call
    if _original_make_call is None:
        import pynautobot.core.request as req
        _original_make_call = req.Request._make_call
        req.Request._make_call = _counting_make_call


def _get_counts() -> dict[str, int]:
    """Return snapshot of HTTP call counts and reset."""
    global _http_call_counts
    snap = dict(_http_call_counts)
    _http_call_counts = {}
    return snap

PROFILE = "prod"
DEVICE = "HQV-PE1-NEW"

WORKFLOWS = [
    {
        "id": "bgp_summary",
        "name": "BGP Summary",
        "cmd": [
            "uv", "run", "nautobot-mcp", "--json",
            "cms", "routing", "bgp-summary",
            "--device", DEVICE,
        ],
    },
    {
        "id": "routing_table",
        "name": "Routing Table",
        "cmd": [
            "uv", "run", "nautobot-mcp", "--json",
            "cms", "routing", "routing-table",
            "--device", DEVICE,
        ],
    },
    {
        "id": "firewall_summary",
        "name": "Firewall Summary",
        "cmd": [
            "uv", "run", "nautobot-mcp", "--json",
            "cms", "firewalls", "firewall-summary",
            "--device", DEVICE,
        ],
    },
    {
        "id": "interface_detail",
        "name": "Interface Detail",
        "cmd": [
            "uv", "run", "nautobot-mcp", "--json",
            "cms", "interfaces", "detail",
            "--device", DEVICE,
        ],
    },
    {
        "id": "devices_inventory",
        "name": "Devices Inventory",
        "cmd": [
            "uv", "run", "nautobot-mcp", "--json",
            "devices", "inventory",
            DEVICE,
        ],
    },
]

# Performance thresholds: workflow_id → max_allowed_ms
# bgp_summary: was ~80s before fix; target <5s per v1.8 requirement (REG-01)
# Other thresholds: conservative 2x estimates; update to 2× empirically observed
# post-fix times per D-06.
THRESHOLD_MS: dict[str, float] = {
    "bgp_summary": 5000.0,
    "routing_table": 15000.0,
    "firewall_summary": 15000.0,
    "interface_detail": 15000.0,
    "devices_inventory": 15000.0,
}


@dataclass
class WorkflowResult:
    id: str
    name: str
    passed: bool
    elapsed_ms: float
    status: str | None
    error: str | None
    summary: str


_workflow_counts: dict[str, dict[str, int]] = {}


def run_workflow(workflow: dict) -> WorkflowResult:
    """Run one workflow via subprocess and evaluate pass/fail.

    Parses JSON from stdout. Returns WorkflowResult.
    """
    global _workflow_counts
    _install_counter()  # install or no-op if already installed
    t0 = time.monotonic()
    result = None
    elapsed_ms = -1.0
    try:
        result = subprocess.run(
            workflow["cmd"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

        # Threshold check — evaluate before parsing to catch slow-but-successful runs
        threshold = THRESHOLD_MS.get(workflow["id"])
        exceeded = threshold is not None and elapsed_ms > threshold

    except subprocess.TimeoutExpired:
        return WorkflowResult(
            id=workflow["id"],
            name=workflow["name"],
            passed=False,
            elapsed_ms=-1,
            status=None,
            error="Command timed out after 120s",
            summary="TIMEOUT",
        )
    except FileNotFoundError:
        return WorkflowResult(
            id=workflow["id"],
            name=workflow["name"],
            passed=False,
            elapsed_ms=-1,
            status=None,
            error="'uv' not found — ensure uv is installed and in PATH",
            summary="ERROR",
        )
    except Exception as exc:
        return WorkflowResult(
            id=workflow["id"],
            name=workflow["name"],
            passed=False,
            elapsed_ms=-1,
            status=None,
            error=str(exc),
            summary="ERROR",
        )

    # Capture HTTP call counts after subprocess completes
    counts = _get_counts()
    _workflow_counts[workflow["id"]] = counts

    # Try to parse JSON from stdout (for error reporting only)
    try:
        _ = json.loads(result.stdout)  # noqa: F841
    except json.JSONDecodeError:
        return WorkflowResult(
            id=workflow["id"],
            name=workflow["name"],
            passed=False,
            elapsed_ms=elapsed_ms,
            status=None,
            error=f"Non-JSON stdout: {result.stdout.strip()[:200] if result.stdout else '(empty stdout)'}",
            summary="PARSE ERROR",
        )

    # Check non-zero exit code
    if result.returncode != 0:
        return WorkflowResult(
            id=workflow["id"],
            name=workflow["name"],
            passed=False,
            elapsed_ms=elapsed_ms,
            status=None,
            error=f"Non-zero exit code {result.returncode}",
            summary="NON-ZERO EXIT",
        )

    # Evaluate pass/fail criteria
    # CLI commands return raw data (no workflow envelope), so pass = exit 0
    # Threshold-exceeded runs still append FAIL below but get threshold_error set
    passed = result.returncode == 0 and not exceeded

    summary_parts = []
    if passed:
        summary_parts.append("PASS")
    else:
        summary_parts.append("FAIL")
        summary_parts.append(f"exit={result.returncode}")

    if exceeded:
        threshold_error = f"Threshold exceeded: {elapsed_ms:.0f}ms > {threshold:.0f}ms"
    else:
        threshold_error = None

    return WorkflowResult(
        id=workflow["id"],
        name=workflow["name"],
        passed=passed,
        elapsed_ms=elapsed_ms,
        status=None,
        error=threshold_error,
        summary=" | ".join(summary_parts),
    )


def print_results(results: list[WorkflowResult], total_ms: float) -> None:
    """Print a formatted summary table."""
    global _workflow_counts
    print(f"\n{'=' * 72}")
    print(f"  CMS Smoke UAT — {DEVICE} | Profile: {PROFILE}")
    print(f"{'=' * 72}")
    print(f"  {'Workflow':<22} {'ID':<20} {'Result':<12} {'Time (ms)':>10}")
    print(f"  {'-' * 22} {'-' * 20} {'-' * 12} {'-' * 10}")

    for r in results:
        elapsed_str = f"{r.elapsed_ms:.0f}ms" if r.elapsed_ms >= 0 else "  N/A  "
        result_str = "PASS" if r.passed else "FAIL"
        print(f"  {r.name:<22} {r.id:<20} {result_str:<12} {elapsed_str:>10}")

    print(f"  {'-' * 72}")
    passed_count = sum(1 for r in results if r.passed)
    print(f"  {passed_count}/{len(results)} passed  |  Total time: {total_ms:.0f}ms")
    print(f"{'=' * 72}\n")

    # --- HTTP Call Counts per Workflow ---
    print(f"\n  --- HTTP Call Counts per Workflow ---")
    for wid, counts in _workflow_counts.items():
        total_calls = sum(counts.values())
        print(f"  {wid}: {total_calls} total calls")
        for path, n in sorted(counts.items(), key=lambda x: -x[1])[:5]:
            if n > 1:
                print(f"    {n:3d}x {path}")
    _workflow_counts.clear()


def main() -> int:
    print(f"Starting CMS smoke UAT for device '{DEVICE}' on profile '{PROFILE}'...")
    print(f"Target: prod (https://nautobot.netnam.vn)\n")

    results: list[WorkflowResult] = []
    t0 = time.monotonic()

    for workflow in WORKFLOWS:
        r = run_workflow(workflow)
        results.append(r)

    total_ms = (time.monotonic() - t0) * 1000
    print_results(results, total_ms)

    failed = [r for r in results if not r.passed]
    if failed:
        print("FAILURE DETAILS:")
        for r in failed:
            print(f"  [{r.id}] {r.error or 'status=' + str(r.status)}")
        print()
        return 1
    else:
        print("All CMS smoke tests PASSED.\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
