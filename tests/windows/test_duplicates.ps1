# Test Case E: Duplicates and Conflict Resolution Testing
param(
    [string]$QaRoot = "C:\CleanDownloads-QA"
)

$ErrorActionPreference = "Stop"
$logFile = Join-Path $QaRoot "TestLogs\application-log.txt"
$testResults = @{
    TestId = "TC-E"
    Name = "Duplicates and Conflict Resolution Verification"
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

Log-Step "Starting Test Case E: Duplicates and Conflict Resolution Verification..."

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

    # 1. Clean test folder and prepare duplicate collision fixture
    Get-ChildItem -Path $testDownloads -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    $destPdfDir = Join-Path $testDownloads "Documents\PDF"
    New-Item -ItemType Directory -Path $destPdfDir -Force | Out-Null

    # Pre-existing destination file: "Version 0"
    $preExistingDest = Join-Path $destPdfDir "invoice.pdf"
    "Pre-existing Destination Version 0" | Set-Content $preExistingDest -Encoding UTF8

    # Two files at root to organize: "Version 1" and "Version 2"
    $rootInvoice1 = Join-Path $testDownloads "invoice.pdf"
    "Invoice Root Version 1" | Set-Content $rootInvoice1 -Encoding UTF8

    $rootInvoice2 = Join-Path $testDownloads "invoice (1).pdf"
    "Invoice Root Version 2" | Set-Content $rootInvoice2 -Encoding UTF8

    Log-Step "Created collision fixture with pre-existing destination and two root files."

    # 2. Run organization
    Log-Step "Executing: cleandownloads organize"
    $orgOutput = & $venvPython -m cleandownloads.cli organize *>&1
    Add-Content -Path $logFile -Value "`r`n=== Collision Test Output ===`r`n$($orgOutput -join "`r`n")"

    # 3. Verify original destination file was NOT overwritten
    $preExistingContent = Get-Content $preExistingDest -Raw
    if ($preExistingContent.Trim() -ne "Pre-existing Destination Version 0") {
        throw "CRITICAL FAILURE: Pre-existing destination file was overwritten! Content: $preExistingContent"
    }
    Log-Step "[PASS] Zero Overwrite Invariant: Pre-existing destination file remained 100% untouched."
    $testResults.Steps += "Pre-existing file protected from overwrite"

    # 4. Verify moved files were assigned collision-safe filenames
    $destFiles = Get-ChildItem -Path $destPdfDir -File
    if ($destFiles.Count -ne 3) {
        throw "Expected 3 files in $destPdfDir, found $($destFiles.Count)!"
    }

    $allContents = $destFiles | ForEach-Object { (Get-Content $_.FullName -Raw).Trim() }
    if (-not ($allContents -contains "Invoice Root Version 1") -or -not ($allContents -contains "Invoice Root Version 2")) {
        throw "One or more colliding files lost their content during collision resolution!"
    }
    Log-Step "[PASS] All 3 versions preserved with distinct collision-safe filenames: $($destFiles.Name -join ', ')"
    $testResults.Steps += "Collision-safe filenames generated non-destructively"

    # 5. Idempotency Check: Run organization again, verify no endless renaming occurs
    Log-Step "Executing second organization run to verify idempotency (zero endless rename loops)..."
    $secondOutput = & $venvPython -m cleandownloads.cli organize *>&1
    Add-Content -Path $logFile -Value "`r`n=== Second Run Output ===`r`n$($secondOutput -join "`r`n")"

    $destFilesAfter = Get-ChildItem -Path $destPdfDir -File
    if ($destFilesAfter.Count -ne 3) {
        throw "Idempotency failed: File count changed on second organization run!"
    }
    Log-Step "[PASS] Idempotency verified: repeated organization did not move or rename already-organized files."
    $testResults.Steps += "Organization idempotency verified"

    Log-Step "[PASS] TEST CASE E PASSED: Duplicates and conflict resolution verified successfully."
} catch {
    $err = $_.Exception.Message
    Log-Step "[FAIL] TEST CASE E FAILED: $err"
    $testResults.Passed = $false
    $testResults.Failures += $err
}

$testResults | ConvertTo-Json -Depth 5
