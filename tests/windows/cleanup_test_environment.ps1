# Cleanup Disposable QA Test Environment for CleanDownloads
param(
    [string]$QaRoot = "C:\CleanDownloads-QA"
)

$ErrorActionPreference = "Continue"

Write-Host "==> Cleaning up QA Test Downloads in $QaRoot..."

$testDownloads = Join-Path $QaRoot "TestDownloads"
if (Test-Path $testDownloads) {
    Get-ChildItem -Path $testDownloads -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "    Emptied $testDownloads"
}

# Restore original CleanDownloads data if backup exists
$localAppData = $env:LOCALAPPDATA
if (-not $localAppData) { $localAppData = Join-Path $env:USERPROFILE "AppData\Local" }
$appDataDir = Join-Path $localAppData "CleanDownloads"
$backupTarget = Join-Path $QaRoot "TestBackups\CleanDownloads-OriginalBackup"

if (Test-Path $backupTarget) {
    Write-Host "    Restoring original CleanDownloads data to $appDataDir..."
    if (Test-Path $appDataDir) { Remove-Item -Recurse -Force $appDataDir -ErrorAction SilentlyContinue }
    Copy-Item -Path $backupTarget -Destination $appDataDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "[PASS] QA Test Environment cleanup complete."
