# Test Case C: Dry Run & Preview Mode Verification
param(
    [string]$QaRoot = "C:\CleanDownloads-QA"
)

$ErrorActionPreference = "Stop"
$logFile = Join-Path $QaRoot "TestLogs\application-log.txt"
$testResults = @{
    TestId = "TC-C"
    Name = "Dry Run & Preview Mode Verification"
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

Log-Step "Starting Test Case C: Dry Run & Preview Mode Verification..."

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

    # 1. Ensure test directory is clean and populated with fresh files
    Get-ChildItem -Path $testDownloads -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    $generatorScript = Join-Path $PSScriptRoot "generate_test_files.py"
    & $venvPython $generatorScript $testDownloads
    Log-Step "Populated fresh test files in $testDownloads"

    # 2. Compute SHA-256 hashes of all initial files
    $initialFiles = Get-ChildItem -Path $testDownloads -File
    $preHashes = @{}
    foreach ($file in $initialFiles) {
        $hash = (Get-FileHash -Path $file.FullName -Algorithm SHA256).Hash
        $preHashes[$file.Name] = $hash
    }
    Log-Step "Computed SHA-256 hashes for $($preHashes.Count) files before dry run."

    # 3. Execute dry run command
    Log-Step "Executing: cleandownloads organize --dry-run"
    $dryRunOutput = & $venvPython -m cleandownloads.cli organize --dry-run *>&1
    Add-Content -Path $logFile -Value "`r`n=== Dry Run Output ===`r`n$($dryRunOutput -join "`r`n")"

    # 4. Compute SHA-256 hashes after dry run and compare
    $postFiles = Get-ChildItem -Path $testDownloads -File
    if ($postFiles.Count -ne $initialFiles.Count) {
        throw "File count changed during dry run! Pre: $($initialFiles.Count), Post: $($postFiles.Count)"
    }

    foreach ($file in $postFiles) {
        $postHash = (Get-FileHash -Path $file.FullName -Algorithm SHA256).Hash
        $preHash = $preHashes[$file.Name]
        if (-not $preHash) {
            throw "Unexpected new file detected after dry run: $($file.Name)"
        }
        if ($postHash -ne $preHash) {
            throw "File content hash mismatch for '$($file.Name)'! File was modified during dry run!"
        }
    }
    Log-Step "[PASS] All $($postFiles.Count) original files remained completely untouched and identical."
    $testResults.Steps += "Original files 100% untouched"

    # 5. Verify no destination category directories were created
    $categoryDirs = @("Documents", "Images", "Videos", "Audio", "Archives", "Software", "Code", "Other")
    foreach ($cat in $categoryDirs) {
        $catPath = Join-Path $testDownloads $cat
        if (Test-Path $catPath) {
            throw "Category directory '$cat' was unexpectedly created during dry run!"
        }
    }
    Log-Step "[PASS] Verified zero destination directories were created."
    $testResults.Steps += "Zero destination directories created"

    # 6. Verify SQLite database contains no completed batches from dry-run
    $dbPath = Join-Path $installDir "history.db"
    if (Test-Path $dbPath) {
        $batchCheck = & $venvPython -c "import sqlite3; conn = sqlite3.connect(r'$dbPath'); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM batches WHERE status = \'COMPLETED\''); print(cur.fetchone()[0]); conn.close()"
        if ([int]$batchCheck.Trim() -gt 0) {
            throw "Database recorded a COMPLETED batch during dry run!"
        }
    }
    Log-Step "[PASS] Verified history database contains no false positive operations."
    $testResults.Steps += "No false history recorded"

    Log-Step "[PASS] TEST CASE C PASSED: Dry run mode verified successfully."
} catch {
    $err = $_.Exception.Message
    Log-Step "[FAIL] TEST CASE C FAILED: $err"
    $testResults.Passed = $false
    $testResults.Failures += $err
}

$testResults | ConvertTo-Json -Depth 5
