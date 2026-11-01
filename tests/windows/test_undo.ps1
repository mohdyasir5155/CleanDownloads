# Test Case F: Undo Engine Verification
param(
    [string]$QaRoot = "C:\CleanDownloads-QA"
)

$ErrorActionPreference = "Stop"
$logFile = Join-Path $QaRoot "TestLogs\application-log.txt"
$testResults = @{
    TestId = "TC-F"
    Name = "Undo Engine & Tamper Verification"
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

Log-Step "Starting Test Case F: Undo Engine & Tamper Verification..."

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

    # 1. Clean test folder and populate fresh test dataset
    Get-ChildItem -Path $testDownloads -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    $generatorScript = Join-Path $PSScriptRoot "generate_test_files.py"
    & $venvPython $generatorScript $testDownloads

    # Record pre-organization hashes
    $initialFiles = Get-ChildItem -Path $testDownloads -File -Force
    $preHashes = @{}
    foreach ($f in $initialFiles) {
        $preHashes[$f.Name] = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash
    }

    # 2. Perform real organization
    Log-Step "Executing organization before testing undo..."
    $orgOutput = & $venvPython -m cleandownloads.cli organize *>&1
    Add-Content -Path $logFile -Value "`r`n=== Organize Before Undo ===`r`n$($orgOutput -join "`r`n")"

    # 3. Execute undo command
    Log-Step "Executing: cleandownloads undo"
    $undoOutput = & $venvPython -m cleandownloads.cli undo *>&1
    Add-Content -Path $logFile -Value "`r`n=== Undo Output ===`r`n$($undoOutput -join "`r`n")"

    # 4. Verify all files returned to root TestDownloads directory
    $restoredFiles = Get-ChildItem -Path $testDownloads -File -Force
    if ($restoredFiles.Count -ne $initialFiles.Count) {
        throw "Undo restoration count mismatch! Expected: $($initialFiles.Count), Found: $($restoredFiles.Count)"
    }

    foreach ($f in $restoredFiles) {
        $restoredHash = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash
        $expectedHash = $preHashes[$f.Name]
        if ($restoredHash -ne $expectedHash) {
            throw "Hash mismatch after undo for '$($f.Name)'! Expected: $expectedHash, Got: $restoredHash"
        }
    }
    Log-Step "[PASS] Standard Undo Verified: All $($restoredFiles.Count) files successfully restored to root with 100% hash match."
    $testResults.Steps += "Standard undo verified"

    # 5. Advanced Sub-Test: Collision during undo (occupied original destination)
    Log-Step "Testing collision handling during undo (occupied original destination)..."
    # Clean and create single test file
    Get-ChildItem -Path $testDownloads -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    $contract = Join-Path $testDownloads "contract.pdf"
    "Original Contract v1" | Set-Content $contract -Encoding UTF8

    & $venvPython -m cleandownloads.cli organize *>&1 | Out-Null
    
    # Place a NEW file at original location before undoing
    "Newly Downloaded Contract v2" | Set-Content $contract -Encoding UTF8

    # Run undo
    $undoCollisionOutput = & $venvPython -m cleandownloads.cli undo *>&1
    Add-Content -Path $logFile -Value "`r`n=== Undo Collision Output ===`r`n$($undoCollisionOutput -join "`r`n")"

    # Verify root contract.pdf was NOT overwritten
    $rootContent = Get-Content $contract -Raw
    if ($rootContent.Trim() -ne "Newly Downloaded Contract v2") {
        throw "CRITICAL FAILURE: Existing root file was overwritten during undo! Content: $rootContent"
    }

    # Verify restored contract was saved collision-safely as contract (1).pdf
    $restoredCollision = Join-Path $testDownloads "contract (1).pdf"
    if (-not (Test-Path $restoredCollision)) {
        throw "Restored file was not created collision-safely at $restoredCollision!"
    }
    $restoredContent = Get-Content $restoredCollision -Raw
    if ($restoredContent.Trim() -ne "Original Contract v1") {
        throw "Restored file content corrupted during collision-safe undo! Content: $restoredContent"
    }
    Log-Step "[PASS] Undo Collision Invariant: Pre-existing root file protected, restored file assigned safe numbered suffix."
    $testResults.Steps += "Collision-safe undo verified"

    # 6. Advanced Sub-Test: Modified destination file integrity rejection
    Log-Step "Testing SHA-256 integrity rejection for modified destination files..."
    Get-ChildItem -Path $testDownloads -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    $tamperDoc = Join-Path $testDownloads "tamper_doc.pdf"
    "Legitimate Document Content" | Set-Content $tamperDoc -Encoding UTF8

    & $venvPython -m cleandownloads.cli organize *>&1 | Out-Null
    
    $destTamper = Join-Path $testDownloads "Documents\PDF\tamper_doc.pdf"
    # Tamper with file at destination
    "MALICIOUS ALTERED CONTENT OVERWRITE" | Set-Content $destTamper -Encoding UTF8

    # Attempt undo
    $undoTamperOutput = & $venvPython -m cleandownloads.cli undo *>&1
    Add-Content -Path $logFile -Value "`r`n=== Undo Tamper Output ===`r`n$($undoTamperOutput -join "`r`n")"

    # Destination file must remain untouched, root must NOT have tamper_doc.pdf
    if (Test-Path $tamperDoc) {
        throw "Tampered/modified file was incorrectly restored to original location!"
    }
    if (-not (Test-Path $destTamper)) {
        throw "Tampered destination file was unexpectedly removed!"
    }
    Log-Step "[PASS] Undo Integrity Invariant: Modified destination file was safely rejected and not restored."
    $testResults.Steps += "Tampered file restoration rejected"

    Log-Step "[PASS] TEST CASE F PASSED: Undo engine and integrity checks verified successfully."
} catch {
    $err = $_.Exception.Message
    Log-Step "[FAIL] TEST CASE F FAILED: $err"
    $testResults.Passed = $false
    $testResults.Failures += $err
}

$testResults | ConvertTo-Json -Depth 5
