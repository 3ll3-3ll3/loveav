param(
    [string]$Target = $(if ($env:LOVEAV_SKILL_DIR) { $env:LOVEAV_SKILL_DIR } else { Join-Path $env:USERPROFILE ".codex\skills\loveav" })
)

$ErrorActionPreference = "Stop"
$Source = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

New-Item -ItemType Directory -Force $Target | Out-Null

$files = @("SKILL.md", "README.md")
foreach ($file in $files) {
    Copy-Item -Force (Join-Path $Source $file) (Join-Path $Target $file)
}

$dirs = @("agents", "references", "scripts")
foreach ($dir in $dirs) {
    $sourceDir = Join-Path $Source $dir
    if (Test-Path $sourceDir) {
        $targetDir = Join-Path $Target $dir
        New-Item -ItemType Directory -Force $targetDir | Out-Null
        Copy-Item -Recurse -Force (Join-Path $sourceDir "*") $targetDir
    }
}

Write-Host "LoveAV Skill synced to: $Target"
Write-Host "Private loveav-data was not copied or deleted."
