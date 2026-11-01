# Setup Disposable QA Test Environment for CleanDownloads
param(
    [string]$QaRoot = "C:\CleanDownloads-QA"
)

$ErrorActionPreference = "Stop"

Write-Host "==> Initializing CleanDownloads QA Directory Structure in $QaRoot..."

$subdirs = @(
    "TestDownloads",
    "TestData",
    "TestResults",
    "TestLogs",
    "TestBackups",
    "TestConfig"
)

foreach ($dir in $subdirs) {
    $fullPath = Join-Path $QaRoot $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
    }
}

# Backup existing CleanDownloads app data if present
$localAppData = $env:LOCALAPPDATA
if (-not $localAppData) { $localAppData = Join-Path $env:USERPROFILE "AppData\Local" }
$appDataDir = Join-Path $localAppData "CleanDownloads"
$backupTarget = Join-Path $QaRoot "TestBackups\CleanDownloads-OriginalBackup"

if (Test-Path $appDataDir) {
    Write-Host "    Preserving pre-existing CleanDownloads data to $backupTarget..."
    if (Test-Path $backupTarget) { Remove-Item -Recurse -Force $backupTarget }
    Copy-Item -Path $appDataDir -Destination $backupTarget -Recurse -Force
}

# Clean TestDownloads directory
Get-ChildItem -Path (Join-Path $QaRoot "TestDownloads") -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "[PASS] QA Environment initialized successfully at $QaRoot"
