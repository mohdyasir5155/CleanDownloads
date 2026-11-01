# Test Case G: Application Restart and Persistence Testing
param(
    [string]$QaRoot = "C:\CleanDownloads-QA"
)

$ErrorActionPreference = "Stop"
$logFile = Join-Path $QaRoot "TestLogs\application-log.txt"
$testResults = @{
    TestId = "TC-G"
    Name = "Application Restart and Persistence Verification"
    Passed = $true
    Steps = @()
    Failures = @()
}

function Log-Step($msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

Log-Step "Starting Test Case G: Application Restart and Persistence Verification..."

try {
    $localAppData = $env:LOCALAPPDATA
    if (-not $localAppData) { $localAppData = Join-Path $env:USERPROFILE "AppData\Local" }
    $installDir = Join-Path $localAppData "CleanDownloads"
    $venvPython = Join-Path $installDir "venv\Scripts\python.exe"
    $testDownloads = Join-Path $QaRoot "TestDownloads"
    $env:CLEANDOWNLOADS_DOWNLOADS_DIR = $testDownloads
    if (-not (Test-Path $testDownloads)) { New-Item -ItemType Directory -Path $testDownloads -Force | Out-Null }

    $configPath = Join-Path $installDir "config.json"
    @{ downloads_dir = $testDownloads } | ConvertTo-Json | Set-Content $configPath -Encoding UTF8

    $dbPath = Join-Path $installDir "history.db"

    # 1. Clean test folder and populate fresh test dataset
    Get-ChildItem -Path $testDownloads -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    $generatorScript = Join-Path $PSScriptRoot "generate_test_files.py"
    & $venvPython $generatorScript $testDownloads

    # 2. Organize files
    Log-Step "Executing organization..."
    & $venvPython -m cleandownloads.cli organize *>&1 | Out-Null

    # 3. Simulate clean application termination and new session
    Log-Step "Simulating clean application termination and new session..."
    Start-Sleep -Seconds 1

    # 4. Check SQLite database integrity directly
    Log-Step "Checking SQLite database integrity via PRAGMA integrity_check..."
    $integrityRes = & $venvPython -c "import sqlite3; conn = sqlite3.connect(r'$dbPath'); cur = conn.cursor(); cur.execute('PRAGMA integrity_check'); print(cur.fetchone()[0]); conn.close()"
    if ($integrityRes.Trim() -ne "ok") {
        throw "SQLite PRAGMA integrity_check failed! Result: $integrityRes"
    }
    Log-Step "[PASS] Database integrity verified (PRAGMA integrity_check: ok)"
    $testResults.Steps += "SQLite integrity check: ok"

    # 5. Query history in new session
    Log-Step "Querying history in new session via: cleandownloads history"
    $historyOutput = & $venvPython -m cleandownloads.cli history *>&1
    Add-Content -Path $logFile -Value "`r`n=== New Session History Output ===`r`n$($historyOutput -join "`r`n")"

    $histText = $historyOutput -join "`n"
    if ($histText -notmatch "COMPLETED") {
        throw "History output in new session did not show previous completed batches!"
    }
    Log-Step "[PASS] Previous batch operations successfully retrieved in fresh session."
    $testResults.Steps += "Batch history persisted"

    # 6. Verify configuration persistence
    Log-Step "Verifying configuration persistence in new session..."
    $configOutput = & $venvPython -m cleandownloads.cli config *>&1
    Add-Content -Path $logFile -Value "`r`n=== Config Output ===`r`n$($configOutput -join "`r`n")"

    $cfgText = $configOutput -join "`n"
    if ($cfgText -notmatch [regex]::Escape($testDownloads)) {
        throw "Custom downloads directory was lost across restart! Expected $testDownloads in config output."
    }
    Log-Step "[PASS] Configuration verified to persist across sessions."
    $testResults.Steps += "Configuration persisted"

    Log-Step "[PASS] TEST CASE G PASSED: Persistence and restart verification successful."
} catch {
    $err = $_.Exception.Message
    Log-Step "[FAIL] TEST CASE G FAILED: $err"
    $testResults.Passed = $false
    $testResults.Failures += $err
}

$testResults | ConvertTo-Json -Depth 5
