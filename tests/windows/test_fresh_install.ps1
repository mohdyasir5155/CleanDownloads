# Test Case A: Fresh Installation Testing
param(
    [string]$QaRoot = "C:\CleanDownloads-QA",
    [string]$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
)

$ErrorActionPreference = "Stop"
$logFile = Join-Path $QaRoot "TestLogs\installation-log.txt"
$testResults = @{
    TestId = "TC-A"
    Name = "Fresh Installation Verification"
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

Log-Step "Starting Test Case A: Fresh Installation Verification..."

try {
    # 1. Clean any previous installation in LocalAppData
    $localAppData = $env:LOCALAPPDATA
    if (-not $localAppData) { $localAppData = Join-Path $env:USERPROFILE "AppData\Local" }
    $installDir = Join-Path $localAppData "CleanDownloads"

    if (Test-Path $installDir) {
        Log-Step "Cleaning previous CleanDownloads install dir for pristine test: $installDir"
        Remove-Item -Recurse -Force $installDir -ErrorAction SilentlyContinue
    }

    # 2. Execute install.ps1 from repository root
    $installerScript = Join-Path $RepoRoot "install.ps1"
    Log-Step "Executing installer: $installerScript -NonInteractive -SkipInitialScan"

    $installOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $installerScript -NonInteractive -SkipInitialScan *>&1
    Add-Content -Path $logFile -Value ($installOutput -join "`r`n")

    # 3. Verify installation artifacts
    $venvPython = Join-Path $installDir "venv\Scripts\python.exe"
    $binDir = Join-Path $installDir "bin"
    $cmdLauncher = Join-Path $binDir "cleandownloads.cmd"
    $psLauncher = Join-Path $binDir "cleandownloads.ps1"

    if (-not (Test-Path $installDir)) { throw "Install directory was not created: $installDir" }
    if (-not (Test-Path $venvPython)) { throw "Virtual environment Python executable not found: $venvPython" }
    if (-not (Test-Path $cmdLauncher)) { throw "CMD launcher script missing: $cmdLauncher" }
    if (-not (Test-Path $psLauncher)) { throw "PowerShell launcher script missing: $psLauncher" }

    Log-Step "[PASS] Core installation artifacts verified in $installDir"
    $testResults.Steps += "Installation artifacts verified"

    # 4. Verify User PATH environment variable
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$binDir*") {
        throw "User PATH was not updated to include $binDir"
    }
    Log-Step "[PASS] User PATH verified to contain $binDir"
    $testResults.Steps += "User PATH verified"

    # 5. Verify version reporting via installed launcher
    $versionOutput = & $venvPython -c "import cleandownloads; print(cleandownloads.__version__)"
    if ($versionOutput.Trim() -ne "1.0.0") {
        throw "Unexpected version reported: $versionOutput (expected 1.0.0)"
    }
    Log-Step "[PASS] CleanDownloads version reported correctly: $versionOutput"
    $testResults.Steps += "Version verified as $versionOutput"

    # 6. Verify launcher execution
    $launcherTest = & $cmdLauncher --version
    Log-Step "[PASS] CLI Launcher executed successfully: $launcherTest"
    $testResults.Steps += "CLI launcher operational"

    # 7. Verify no unexpected background tasks were scheduled
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $schtasksRes = cmd.exe /c "schtasks.exe /Query /TN CleanDownloads_AutoOrganize >nul 2>&1"
    $schtasksExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP

    if ($schtasksExit -eq 0) {
        throw "Scheduled task was unexpectedly registered during basic install!"
    }
    Log-Step "[PASS] Verified no unexpected background tasks registered"
    $testResults.Steps += "No unauthorized tasks created"

    Log-Step "[PASS] TEST CASE A PASSED: Fresh installation verified successfully."
} catch {
    $err = $_.Exception.Message
    Log-Step "[FAIL] TEST CASE A FAILED: $err"
    $testResults.Passed = $false
    $testResults.Failures += $err
}

# Return results as JSON
$testResults | ConvertTo-Json -Depth 5
