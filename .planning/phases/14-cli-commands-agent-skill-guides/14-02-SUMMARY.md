---
phase: 14
plan: 2
status: complete
completed: 2026-03-21
---

# Summary: Plan 14-02 — CMS Device Audit Agent Skill Guide

## What Was Built
Created a comprehensive agent skill guide for CMS-aware device audit workflows. The skill walks an AI agent step-by-step through a full device audit: collecting live data from jmcp, comparing against Nautobot CMS records via drift tools, and interpreting results.

## Key Files Created

### Created
- `.agent/skills/cms-device-audit/SKILL.md` — Full device audit skill guide
  - YAML frontmatter with `name: cms-device-audit`
  - `## When to Use` section (3 use cases)
  - `## Prerequisites` section
  - `## Workflow` section with 8 numbered steps
  - `## Quick Check` abbreviated workflow
  - `## CLI Alternative` section with 6 example commands
  - `## Key MCP Tools Reference` table (8 tools)

## Workflow Coverage
- Step 1: Confirm device in Nautobot (`nautobot_device_summary`)
- Step 2: Collect live BGP (`execute_junos_command show bgp summary | display json`)
- Step 3: Compare BGP vs CMS (`nautobot_cms_compare_bgp_neighbors`)
- Step 4: Collect live routes (`execute_junos_command show route protocol static | display json`)
- Step 5: Compare routes vs CMS (`nautobot_cms_compare_static_routes`)
- Step 6: Review interface detail (`nautobot_cms_get_interface_detail`)
- Step 7: Review firewall summary (`nautobot_cms_get_device_firewall_summary`)
- Step 8: Compile audit report with decision guidance

## Verification
```bash
head -5 .agent/skills/cms-device-audit/SKILL.md  → YAML frontmatter with name: cms-device-audit
grep -c "### Step" .agent/skills/cms-device-audit/SKILL.md  → 8 (> requirement of 6)
grep "CLI Alternative" .agent/skills/cms-device-audit/SKILL.md  → match found
grep "nautobot_cms_compare_bgp_neighbors" .agent/skills/cms-device-audit/SKILL.md  → match found
grep "nautobot_cms_compare_static_routes" .agent/skills/cms-device-audit/SKILL.md  → match found
grep "execute_junos_command" .agent/skills/cms-device-audit/SKILL.md  → match found
```
