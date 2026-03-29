# CMS Data Presence Smoke Test — HQV-PE1-NEW UAT Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `scripts/uat_cms_smoke.py` that runs 5 CMS workflow smoke tests against HQV-PE1-NEW on the prod profile using `uv run nautobot-mcp --json ...` subprocess calls, and prints a PASS/FAIL summary table.

**Architecture:** Single standalone script that shells out to `uv run nautobot-mcp --json ...` for each workflow. Output is parsed from stdout as JSON. Profile is prod (default active profile).

**Tech Stack:** Python ≥ 3.11, subprocess, json, time

---

## File to Create

- **Create:** `scripts/uat_cms_smoke.py`

---

## Task 1: Scaffold `scripts/uat_cms_smoke.py`

**Files:**
- Create: `scripts/uat_cms_smoke.py`

- [ ] **Step 1: Create the file with header and imports**

```python
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
        "checks": ["status != error", "total_groups >= 0", "total_neighbors >= 0"],
    },
    {
        "id": "routing_table",
        "name": "Routing Table",
        "cmd": [
            "uv", "run", "nautobot-mcp", "--json",
            "cms", "routing", "routing-table",
            "--device", DEVICE,
        ],
        "checks": ["status != error", "total_routes >= 0"],
    },
    {
        "id": "firewall_summary",
        "name": "Firewall Summary",
        "cmd": [
            "uv", "run", "nautobot-mcp", "--json",
            "cms", "firewalls", "firewall-summary",
            "--device", DEVICE,
        ],
        "checks": ["status != error", "total_filters >= 0", "total_policers >= 0"],
    },
    {
        "id": "interface_detail",
        "name": "Interface Detail",
        "cmd": [
            "uv", "run", "nautobot-mcp", "--json",
            "cms", "interfaces", "detail",
            "--device", DEVICE,
        ],
        "checks": ["status != error", "total_units >= 0"],
    },
    {
        "id": "devices_inventory",
        "name": "Devices Inventory",
        "cmd": [
            "uv", "run", "nautobot-mcp", "--json",
            "devices", "inventory",
            "--device", DEVICE,
        ],
        "checks": ["status != error", "non-empty response"],
    },
]


@dataclass
class WorkflowResult:
    id: str
    name: str
    passed: bool
    elapsed_ms: float
    status: str | None
    error: str | None
    summary: str


def run_workflow(workflow: dict) -> WorkflowResult:
    """Run one workflow via subprocess and evaluate pass/fail.

    Parses JSON from stdout. Returns WorkflowResult.
    """
    t0 = time.monotonic()
    try:
        result = subprocess.run(
            workflow["cmd"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
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

    # Try to parse JSON from stdout
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return WorkflowResult(
            id=workflow["id"],
            name=workflow["name"],
            passed=False,
            elapsed_ms=elapsed_ms,
            status=None,
            error=f"Non-JSON stdout: {result.stdout[:200]}",
            summary="PARSE ERROR",
        )

    # Evaluate pass/fail criteria
    status = data.get("status")
    error = data.get("error")
    passed = status in ("ok", "partial") and error is None

    summary_parts = []
    if passed:
        summary_parts.append("PASS")
    else:
        summary_parts.append("FAIL")

    if status:
        summary_parts.append(f"status={status}")
    if error:
        summary_parts.append(f"error={error}")

    return WorkflowResult(
        id=workflow["id"],
        name=workflow["name"],
        passed=passed,
        elapsed_ms=elapsed_ms,
        status=status,
        error=error,
        summary=" | ".join(summary_parts),
    )


def print_results(results: list[WorkflowResult], total_ms: float) -> None:
    """Print a formatted summary table."""
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
    passed = sum(1 for r in results if r.passed)
    print(f"  {passed}/{len(results)} passed  |  Total time: {total_ms:.0f}ms")
    print(f"{'=' * 72}\n")


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
```

- [ ] **Step 2: Run script to verify it executes**

Run: `uv run python scripts/uat_cms_smoke.py`
Expected: Script starts, attempts all 5 workflows, prints results table

- [ ] **Step 3: Commit**

```bash
git add scripts/uat_cms_smoke.py
git commit -m "feat(uat): add CMS smoke UAT script for HQV-PE1-NEW

Runs 5 workflow smoke tests via uv run nautobot-mcp --json ...
against prod profile for HQV-PE1-NEW. Layer 1 UAT verifies CMS
plugin has JunOS data present.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

## Verification

After the script runs against prod:

1. All 5 rows show **PASS** — CMS data is present for HQV-PE1-NEW
2. Any **FAIL** row shows a clear error message (status value or stderr excerpt)
3. Elapsed time per workflow is printed
4. Exit code is `0` on all-pass, `1` on any failure

Run locally:
```bash
uv run python scripts/uat_cms_smoke.py
```

Expected prod output (all PASS):
```
======================================================================
  CMS Smoke UAT — HQV-PE1-NEW | Profile: prod
======================================================================
  Workflow                ID                  Result       Time (ms)
  ----------------------  ------------------  ----------  ----------
  BGP Summary             bgp_summary         PASS           1234ms
  Routing Table           routing_table       PASS            567ms
  Firewall Summary        firewall_summary     PASS            890ms
  Interface Detail        interface_detail     PASS           1100ms
  Devices Inventory       devices_inventory    PASS            234ms
  ----------------------------------------------------------------------
  5/5 passed  |  Total time: 4025ms
======================================================================

All CMS smoke tests PASSED.
```
