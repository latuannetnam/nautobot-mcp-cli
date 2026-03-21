---
description: Update CHANGELOG.md and README.md after milestone completion or major feature addition
---

## When to use

Run this workflow after:
- Completing a GSD milestone (`/gsd-complete-milestone`)
- Shipping a major feature phase (new MCP tools, CLI commands, models)
- Any time the feature set diverges meaningfully from what README documents

Trigger with `/update-docs` or ask: *"update the changelog and README"*.

---

## Step 1 — Determine scope

Identify what changed since the last doc update:

```bash
# Find last doc-update commit
git log --oneline --grep="docs:" | head -5

# See what changed since that commit (or since last tag)
git log <last-tag>..HEAD --oneline
git diff <last-tag>..HEAD --stat
```

Also read:
- `.planning/milestones/v*.md` — latest milestone archive for what was shipped
- `.planning/phases/*/` — any `*-SUMMARY.md` files for phases not yet in CHANGELOG

---

## Step 2 — Update `CHANGELOG.md`

### Rules
- Follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format
- If completing a milestone: rename `[Unreleased]` to `[vX.Y] — YYYY-MM-DD`, add fresh `[Unreleased]`
- If updating mid-milestone: add entries under `[Unreleased]`
- Group entries under sub-headings that match the feature area (not generic Added/Changed)
- Each entry = one user-observable capability, not an implementation detail
- Always add stats line: MCP tools count, test count, files changed if milestone

### Entry format

```markdown
## [Unreleased]

### <Feature Area Name>
- `tool_name` — one-line description of what it does for the user

### CLI Commands
- `nautobot-mcp <cmd> <sub>` — what it does

### Stats (milestone only)
- MCP tools: N → **M**
- Unit tests: N → **M**
```

### Source material (read in order)
1. Latest `*-SUMMARY.md` files from `.planning/phases/`
2. `git log --oneline` since last tag
3. `nautobot_mcp/server.py` — count `@mcp.tool` decorators for tool count
4. `uv run pytest tests/ --co -q 2>&1 | tail -1` — for test count

### ⚠️ CHANGELOG editing pitfall — read before writing

When promoting `[Unreleased]` to `[vX.Y]`, **do NOT** use a replace-file-content tool that includes existing version sections in the replacement text. Doing so will:
- Duplicate existing `[vX.Y]` sections (v1.1 appears twice, etc.)
- Place the new version in the wrong position (old ones end up before it)

**Safe approach:** overwrite the entire CHANGELOG from scratch, or only edit the `[Unreleased]` heading line and insert a new fresh `[Unreleased]` block above it — never paste old version content into the replacement.

**Always reconstruct the file in correct order:**
```
[Unreleased]   ← fresh, empty
[vN.N]         ← newest, just promoted
[vN.N-1]       ← previous (unchanged)
[vN.N-2]       ← older (unchanged)
```

---

## Step 3 — Update `README.md`

### What to check and update

| Section | Update trigger |
|---------|---------------|
| Header tagline (line 3) | New core capability |
| `## Features` table | Any new MCP tool group or CLI command group |
| `<details>` MCP tool blocks | New individual tools |
| `### Commands` code block | New CLI command examples |
| `## Drift Detection` or equivalent | New workflow patterns |

### Rules
- Mark new features with ✨ in the Features table for the current milestone cycle; remove ✨ on next milestone
- Show concrete CLI examples, not just capability descriptions
- For agent-facing features, include the tool chain pattern in a code block
- Keep existing sections — only add/update, never remove working examples

### Tool count

```bash
# Get exact count of registered MCP tools
uv run python -c "import asyncio; from nautobot_mcp.server import mcp; tools = asyncio.run(mcp.list_tools()); print(f'{len(tools)} tools')"
```

---

## Step 4 — Commit

```bash
# Stage both files
git add CHANGELOG.md README.md

# Commit with descriptive message
git commit -m "docs: update CHANGELOG and README for <version or feature description>"
```

If this follows a milestone completion, the commit should go on the same branch before pushing and tagging.

---

## Step 5 — Verify

Quick sanity check before declaring done:

```powershell
# Confirm each version section appears EXACTLY ONCE, in newest-first order
Select-String -Pattern "^## \[" CHANGELOG.md | Select-Object LineNumber, Line
# Expected: [Unreleased] first, then [vN.N] descending. No duplicates.

# Confirm tool count in README matches actual
Select-String -Pattern "\d+ (MCP )?tools" README.md

# Confirm new version appears in CHANGELOG
Select-String -Pattern "^## \[v" CHANGELOG.md
```

Confirm:
- `[Unreleased]` section exists and is empty (if a milestone was just closed)
- No version header appears more than once
- Newest version is the first `[vX.Y]` entry after `[Unreleased]`
- README has no stale `(vX.Y)` version tags in section headings (those belong in CHANGELOG only)
