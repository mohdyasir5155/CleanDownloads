# Test Case H: Upgrade Installation Testing
param(
    [string]$QaRoot = "C:\CleanDownloads-QA",
    [string]$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
)

$ErrorActionPreference = "Stop"
$logFile = Join-Path $QaRoot "TestLogs\upgrade-log.txt"
$testResults = @{
    TestId = "TC-H"
    Name = "Upgrade Installation Verification"
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

Log-Step "Starting Test Case H: Upgrade Installation Verification..."

try {
    $localAppData = $env:LOCALAPPDATA
    if (-not $localAppData) { $localAppData = Join-Path $env:USERPROFILE "AppData\Local" }
    $installDir = Join-Path $localAppData "CleanDownloads"
    $venvPython = Join-Path $installDir "venv\Scripts\python.exe"
    $testDownloads = Join-Path $QaRoot "TestDownloads"
    $env:CLEANDOWNLOADS_DOWNLOADS_DIR = $testDownloads
    if (-not (Test-Path $testDownloads)) { New-Item -ItemType Directory -Path $testDownloads -Force | Out-Null }
    $configPath = Join-Path $installDir "config.json"
    $dbPath = Join-Path $installDir "history.db"

    # 1. Establish pre-existing state with custom configuration and user files
    Log-Step "Setting up pre-upgrade state with custom rule and user files..."
    
    # Add a unique custom rule: "E-Books" (.epub, .mobi) -> "Documents/eBooks"
    $customRule = @{
        name = "QA Custom E-Books Rule"
        category = "eBooks"
        subfolder = "Documents/eBooks"
        extensions = @("epub", "mobi")
    }

    $existingConfig = @{
        downloads_dir = $testDownloads
        rules = @($customRule)
        default_fallback_folder = "Other"
        ignored_extensions = @("crdownload", "part", "tmp")
        excluded_directories = @("Documents", "Other")
    }
    $existingConfig | ConvertTo-Json -Depth 5 | Set-Content $configPath -Encoding UTF8
    Log-Step "Injected custom rule 'QA Custom E-Books Rule' into $configPath"

    # Place a user file in TestDownloads
    $userEbook = Join-Path $testDownloads "novel.epub"
    "Pre-Upgrade User Book Content" | Set-Content $userEbook -Encoding UTF8

    # 2. Run installer to simulate upgrade
    Log-Step "Executing installer to upgrade CleanDownloads..."
    $installerScript = Join-Path $RepoRoot "install.ps1"
    $upgradeOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $installerScript -NonInteractive -SkipInitialScan *>&1
    Add-Content -Path $logFile -Value ($upgradeOutput -join "`r`n")

    # 3. Verify user files in Downloads were untouched
    if (-not (Test-Path $userEbook)) {
        throw "User file '$userEbook' was deleted or moved by upgrade installer!"
    }
    $ebookContent = Get-Content $userEbook -Raw
    if ($ebookContent.Trim() -ne "Pre-Upgrade User Book Content") {
        throw "User file content was modified by upgrade installer!"
    }
    Log-Step "[PASS] User files in Downloads directory remained 100% untouched during upgrade."
    $testResults.Steps += "User downloads untouched"

    # 4. Verify custom configuration preserved
    $postUpgradeConfigRaw = Get-Content $configPath -Raw
    if ($postUpgradeConfigRaw -notmatch "QA Custom E-Books Rule" -or $postUpgradeConfigRaw -notmatch "Documents/eBooks") {
        throw "Custom user rules were overwritten or deleted during upgrade!"
    }
    Log-Step "[PASS] Custom user configuration and rules successfully preserved across upgrade."
    $testResults.Steps += "Custom config preserved"

    # 5. Verify history database was preserved
    if (-not (Test-Path $dbPath)) {
        throw "history.db was deleted during upgrade!"
    }
    Log-Step "[PASS] Operation history database preserved."
    $testResults.Steps += "History database preserved"

    # 6. Verify CLI functions properly after upgrade
    $versionOutput = & $venvPython -c "import cleandownloads; print(cleandownloads.__version__)"
    if ($versionOutput.Trim() -ne "1.0.0") {
        throw "Unexpected version after upgrade: $versionOutput"
    }
    Log-Step "[PASS] CLI verified operational after upgrade: v$versionOutput"
    $testResults.Steps += "CLI operational post-upgrade"

    Log-Step "[PASS] TEST CASE H PASSED: Upgrade installation verified successfully."
} catch {
    $err = $_.Exception.Message
    Log-Step "[FAIL] TEST CASE H FAILED: $err"
    $testResults.Passed = $false
    $testResults.Failures += $err
}

$testResults | ConvertTo-Json -Depth 5
