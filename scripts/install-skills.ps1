# install-skills.ps1 — Install Claude Code skills from this repo into your profile
param(
    [switch]$WhatIf  # Dry-run: show what would be copied without copying
)

$ErrorActionPreference = 'Stop'

# Resolve paths relative to script location (not cwd)
$RepoRoot   = Join-Path $PSScriptRoot ".."
$SourceDirs = @(
    (Join-Path $RepoRoot ".claude\skills")    
)
$DestRoot   = Join-Path $env:USERPROFILE ".claude\skills"

# ---------------------------------------------------------------------------
# Step 1 — Install uv if not already present
# ---------------------------------------------------------------------------
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[INFO] Installing uv..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    # Refresh PATH so uv is available in the rest of this session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# ---------------------------------------------------------------------------
# Step 2 — Sync project dependencies with uv
# ---------------------------------------------------------------------------
Write-Host "[INFO] Syncing project dependencies with uv..."
uv sync --directory $RepoRoot

# ---------------------------------------------------------------------------
# Step 3 — Install skills from each source directory
# ---------------------------------------------------------------------------
# Validate at least one source skills directory exists in repo
$validSources = $SourceDirs | Where-Object { Test-Path $_ -PathType Container }
if ($validSources.Count -eq 0) {
    Write-Error "No skills directories found in $RepoRoot"
    exit 1
}

# Ensure destination directory exists
if (-not (Test-Path $DestRoot)) {
    $created = New-Item -ItemType Directory -Path $DestRoot -Force
    if (-not $created) {
        Write-Error "Failed to create destination directory: $DestRoot"
        exit 2
    }
}

# Copy each skill from all source directories -> profile
$Skills = $validSources | ForEach-Object {
    Get-ChildItem $_ -Directory -ErrorAction SilentlyContinue
}
if ($null -eq $Skills -or $Skills.Count -eq 0) {
    Write-Warning "No skill directories found in $RepoRoot"
    exit 0
}

foreach ($skill in $Skills) {
    $dest = Join-Path $DestRoot $skill.Name
    if ($WhatIf) {
        Write-Host "[WhatIf] Would copy $($skill.Name) -> $dest"
    } else {
        if (Test-Path $dest) {
            Remove-Item $dest -Recurse -Force
        }
        Copy-Item $skill.FullName $dest -Recurse -Force
        Write-Host "[OK] Installed skill: $($skill.Name)"
    }
}

if ($WhatIf) {
    Write-Host "`nWhatIf complete. $($Skills.Count) skill(s) would be installed to $DestRoot"
} else {
    Write-Host "`nDone. $($Skills.Count) skill(s) installed to $DestRoot"
}
