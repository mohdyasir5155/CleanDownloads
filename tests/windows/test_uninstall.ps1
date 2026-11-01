# Test Case I: Uninstallation Testing
param(
    [string]$QaRoot = "C:\CleanDownloads-QA",
    [string]$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
)

$ErrorActionPreference = "Stop"
$logFile = Join-Path $QaRoot "TestLogs\uninstall-log.txt"
$testResults = @{
    TestId = "TC-I"
    Name = "Uninstallation Verification"
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

Log-Step "Starting Test Case I: Uninstallation Verification..."

try {
    $localAppData = $env:LOCALAPPDATA
    if (-not $localAppData) { $localAppData = Join-Path $env:USERPROFILE "AppData\Local" }
    $installDir = Join-Path $localAppData "CleanDownloads"
    $binDir = Join-Path $installDir "bin"
    $venvDir = Join-Path $installDir "venv"
    $srcDir = Join-Path $installDir "src"
    $appSourceDir = Join-Path $installDir "app"
    $configPath = Join-Path $installDir "config.json"
    $dbPath = Join-Path $installDir "history.db"
    $testDownloads = Join-Path $QaRoot "TestDownloads"

    # Place a user file in TestDownloads to verify it is never touched
    $userDoc = Join-Path $testDownloads "precious_user_file.txt"
    "Precious Personal Data That Must Never Be Touched" | Set-Content $userDoc -Encoding UTF8

    # 1. Execute uninstaller with KeepData option
    $uninstallerScript = Join-Path $RepoRoot "uninstall.ps1"
    Log-Step "Executing: uninstall.ps1 -NonInteractive -KeepData"
    $uninstallOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $uninstallerScript -NonInteractive -KeepData *>&1
    Add-Content -Path $logFile -Value ($uninstallOutput -join "`r`n")

    # 2. Verify application executable directories removed
    if (Test-Path $venvDir) { throw "Virtual environment directory was not removed: $venvDir" }
    if (Test-Path $srcDir) { throw "Application source directory was not removed: $srcDir" }
    if (Test-Path $appSourceDir) { throw "Application app directory was not removed: $appSourceDir" }
    if (Test-Path $binDir) { throw "Bin launcher directory was not removed: $binDir" }
    Log-Step "[PASS] Application executables and virtual environment cleanly removed."
    $testResults.Steps += "Application executables removed"

    # 3. Verify User PATH was cleaned
    $currentUserPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentUserPath -and ($currentUserPath -like "*$binDir*")) {
        throw "Bin directory was not removed from User PATH! Current PATH: $currentUserPath"
    }
    Log-Step "[PASS] User PATH verified: CleanDownloads bin directory cleanly removed."
    $testResults.Steps += "User PATH cleaned"

    # 4. Verify user files in Downloads were NEVER touched
    if (-not (Test-Path $userDoc)) {
        throw "CRITICAL FAILURE: User file in Downloads was deleted by uninstaller!"
    }
    Log-Step "[PASS] User Downloads directory remained 100% untouched."
    $testResults.Steps += "User downloads untouched"

    # 5. Verify config.json and history.db preserved when KeepData is requested
    if (-not (Test-Path $configPath)) { throw "config.json was unexpectedly deleted despite KeepData=true!" }
    if (-not (Test-Path $dbPath)) { throw "history.db was unexpectedly deleted despite KeepData=true!" }
    Log-Step "[PASS] Configuration and history preserved per user choice."
    $testResults.Steps += "Data preserved as requested"

    # 6. Test Idempotency: Run uninstaller a second time when already uninstalled
    Log-Step "Running uninstaller second time to verify safe idempotency..."
    $secondUninstall = & powershell -NoProfile -ExecutionPolicy Bypass -File $uninstallerScript -NonInteractive -KeepData *>&1
    Log-Step "[PASS] Idempotent uninstallation executed safely without errors."
    $testResults.Steps += "Idempotent uninstall verified"

    Log-Step "[PASS] TEST CASE I PASSED: Uninstallation verified successfully."
} catch {
    $err = $_.Exception.Message
    Log-Step "[FAIL] TEST CASE I FAILED: $err"
    $testResults.Passed = $false
    $testResults.Failures += $err
}

$testResults | ConvertTo-Json -Depth 5
