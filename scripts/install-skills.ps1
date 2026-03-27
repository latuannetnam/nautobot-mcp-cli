# install-skills.ps1 — Install Claude Code skills from this repo into your profile
param(
    [switch]$WhatIf  # Dry-run: show what would be copied without copying
)

$ErrorActionPreference = 'Stop'

# Resolve paths relative to script location (not cwd)
$SourceRoot = Join-Path $PSScriptRoot "..\.claude\skills"
$DestRoot   = Join-Path $env:USERPROFILE ".claude\skills"

# Validate source skills directory exists in repo
if (-not (Test-Path $SourceRoot -PathType Container)) {
    Write-Error "Source skills directory not found: $SourceRoot"
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

# Copy each skill from repo -> profile
$Skills = Get-ChildItem $SourceRoot -Directory -ErrorAction SilentlyContinue
if ($null -eq $Skills -or $Skills.Count -eq 0) {
    Write-Warning "No skill directories found in $SourceRoot"
    exit 0
}

foreach ($skill in $Skills) {
    $dest = Join-Path $DestRoot $skill.Name
    if ($WhatIf) {
        Write-Host "[WhatIf] Would copy $($skill.Name) -> $dest"
    } else {
        Copy-Item $skill.FullName $dest -Recurse -Force
        Write-Host "[OK] Installed skill: $($skill.Name)"
    }
}

if ($WhatIf) {
    Write-Host "`nWhatIf complete. $($Skills.Count) skill(s) would be installed to $DestRoot"
} else {
    Write-Host "`nDone. $($Skills.Count) skill(s) installed to $DestRoot"
}
