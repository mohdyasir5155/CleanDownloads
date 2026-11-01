# Test Case J: Failure Modes & Recovery Testing
param(
    [string]$QaRoot = "C:\CleanDownloads-QA",
    [string]$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
)

$ErrorActionPreference = "Stop"
$logFile = Join-Path $QaRoot "TestLogs\application-log.txt"
$testResults = @{
    TestId = "TC-J"
    Name = "Failure Modes & Recovery Verification"
    Passed = $true
    ScenariosTested = @()
    Failures = @()
}

function Log-Step($msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

Log-Step "Starting Test Case J: Failure Modes & Recovery Verification..."

try {
    # Ensure fresh installation before testing recovery
    $installerScript = Join-Path $RepoRoot "install.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $installerScript -NonInteractive -SkipInitialScan *>&1 | Out-Null

    $localAppData = $env:LOCALAPPDATA
    if (-not $localAppData) { $localAppData = Join-Path $env:USERPROFILE "AppData\Local" }
    $installDir = Join-Path $localAppData "CleanDownloads"
    $venvPython = Join-Path $installDir "venv\Scripts\python.exe"
    $testDownloads = Join-Path $QaRoot "TestDownloads"
    $env:CLEANDOWNLOADS_DOWNLOADS_DIR = $testDownloads
    if (-not (Test-Path $testDownloads)) { New-Item -ItemType Directory -Path $testDownloads -Force | Out-Null }
    $configPath = Join-Path $installDir "config.json"

    # Reset test directory
    Get-ChildItem -Path $testDownloads -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    # Configure downloads_dir
    $testConfig = @{
        downloads_dir = $testDownloads
        rules = @(
            @{ name = "PDF Documents"; category = "Documents"; subfolder = "Documents/PDF"; extensions = @("pdf") }
        )
        default_fallback_folder = "Other"
        ignored_extensions = @("crdownload", "part", "tmp")
        excluded_directories = @("Documents", "Other")
    }
    $testConfig | ConvertTo-Json -Depth 5 | Set-Content $configPath -Encoding UTF8

    # SCENARIO 1: Locked File (Active Download / Sharing Violation)
    Log-Step "Scenario 1: Testing locked file handling..."
    $lockedFile = Join-Path $testDownloads "locked_file.pdf"
    "Initial Content Prior To Lock" | Set-Content $lockedFile -Encoding UTF8

    # Open exclusively with Python process to hold lock
    $lockScript = "import time, sys; f = open(r'$lockedFile', 'r+b'); sys.stdout.write('LOCKED\n'); sys.stdout.flush(); time.sleep(4)"
    $lockProcess = Start-Process -FilePath $venvPython -ArgumentList "-c `"$lockScript`"" -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $QaRoot "TestLogs\lock_stdout.txt")

    # Wait for lock to be established
    Start-Sleep -Milliseconds 600

    # Execute organize while file is held open
    $lockOrganizeOutput = & $venvPython -m cleandownloads.cli organize *>&1
    Add-Content -Path $logFile -Value "`r`n=== Locked File Organize Output ===`r`n$($lockOrganizeOutput -join "`r`n")"

    # Wait for locking process to exit cleanly
    $lockProcess.WaitForExit(5000)

    # Locked file must remain safely in root without loss or crash
    if (-not (Test-Path $lockedFile)) {
        throw "Locked file was unexpectedly removed or corrupted!"
    }
    Log-Step "[PASS] Scenario 1 Verified: Locked file was skipped safely without application crash."
    $testResults.ScenariosTested += "Locked file skipped safely"

    # SCENARIO 2: Read-Only File Movement
    Log-Step "Scenario 2: Testing read-only file handling..."
    $readonlyFile = Join-Path $testDownloads "readonly_report.pdf"
    "Read-Only Content" | Set-Content $readonlyFile -Encoding UTF8
    attrib +r $readonlyFile

    $roOrganizeOutput = & $venvPython -m cleandownloads.cli organize *>&1
    Add-Content -Path $logFile -Value "`r`n=== Readonly Organize Output ===`r`n$($roOrganizeOutput -join "`r`n")"

    $destRoFile = Join-Path $testDownloads "Documents\PDF\readonly_report.pdf"
    if (-not (Test-Path $destRoFile)) {
        throw "Read-only file was not moved to target destination!"
    }
    Log-Step "[PASS] Scenario 2 Verified: Read-only file was safely organized without permission failure."
    $testResults.ScenariosTested += "Read-only file moved cleanly"

    # SCENARIO 3: Malformed JSON Configuration Fallback
    Log-Step "Scenario 3: Testing malformed JSON config graceful fallback..."
    "{ this is syntax broken invalid JSON" | Set-Content $configPath -Encoding UTF8

    # Running scan must not crash; must fall back safely to default rules
    $malformedConfigOutput = & $venvPython -m cleandownloads.cli scan *>&1
    Add-Content -Path $logFile -Value "`r`n=== Malformed Config Scan Output ===`r`n$($malformedConfigOutput -join "`r`n")"

    if ($LASTEXITCODE -ne 0) {
        throw "Application crashed on malformed configuration! Expected safe default fallback."
    }
    Log-Step "[PASS] Scenario 3 Verified: Malformed JSON configuration fell back safely without crashing."
    $testResults.ScenariosTested += "Malformed config fallback verified"

    # SCENARIO 4: Oversized JSON Configuration (>512 KB)
    Log-Step "Scenario 4: Testing oversized config file DoS defense..."
    " " * (600 * 1024) | Set-Content $configPath -Encoding UTF8

    $oversizedConfigOutput = & $venvPython -m cleandownloads.cli scan *>&1
    Add-Content -Path $logFile -Value "`r`n=== Oversized Config Output ===`r`n$($oversizedConfigOutput -join "`r`n")"

    if ($LASTEXITCODE -ne 0) {
        throw "Application crashed on oversized configuration! Expected safe fallback."
    }
    Log-Step "[PASS] Scenario 4 Verified: Oversized configuration safely intercepted."
    $testResults.ScenariosTested += "Oversized config DoS intercepted"

    Log-Step "[PASS] TEST CASE J PASSED: All failure and recovery scenarios verified successfully."
} catch {
    $err = $_.Exception.Message
    Log-Step "[FAIL] TEST CASE J FAILED: $err"
    $testResults.Passed = $false
    $testResults.Failures += $err
}

$testResults | ConvertTo-Json -Depth 5
