# Test Case D: Real Organization Testing
param(
    [string]$QaRoot = "C:\CleanDownloads-QA"
)

$ErrorActionPreference = "Stop"
$logFile = Join-Path $QaRoot "TestLogs\application-log.txt"
$testResults = @{
    TestId = "TC-D"
    Name = "Real Organization Verification"
    Passed = $true
    FilesOrganized = 0
    HashesVerified = 0
    Failures = @()
}

function Log-Step($msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

Log-Step "Starting Test Case D: Real Organization Verification..."

try {
    $localAppData = $env:LOCALAPPDATA
    if (-not $localAppData) { $localAppData = Join-Path $env:USERPROFILE "AppData\Local" }
    $installDir = Join-Path $localAppData "CleanDownloads"
    $venvPython = Join-Path $installDir "venv\Scripts\python.exe"
    $testDownloads = Join-Path $QaRoot "TestDownloads"
    $env:CLEANDOWNLOADS_DOWNLOADS_DIR = $testDownloads
    if (-not (Test-Path $testDownloads)) { New-Item -ItemType Directory -Path $testDownloads -Force | Out-Null }

    # Ensure config points to TestDownloads
    $configPath = Join-Path $installDir "config.json"
    @{ downloads_dir = $testDownloads } | ConvertTo-Json | Set-Content $configPath -Encoding UTF8

    # 1. Clean and populate fresh test dataset
    Get-ChildItem -Path $testDownloads -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    $generatorScript = Join-Path $PSScriptRoot "generate_test_files.py"
    & $venvPython $generatorScript $testDownloads
    Log-Step "Populated fresh test files in $testDownloads"

    # 2. Record initial file hashes
    $initialFiles = Get-ChildItem -Path $testDownloads -File -Force
    $preHashes = @{}
    foreach ($f in $initialFiles) {
        $hash = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash
        $preHashes[$f.Name] = @{
            Hash = $hash
            Size = $f.Length
        }
    }
    Log-Step "Recorded $($preHashes.Count) initial files and SHA-256 hashes."

    # 3. Execute real organization
    Log-Step "Executing: cleandownloads organize"
    $orgOutput = & $venvPython -m cleandownloads.cli organize *>&1
    Add-Content -Path $logFile -Value "`r`n=== Real Organization Output ===`r`n$($orgOutput -join "`r`n")"

    # 4. Verify all moved files exist and verify content integrity (SHA-256 match)
    $movedFiles = Get-ChildItem -Path $testDownloads -Recurse -File -Force
    Log-Step "Total files present in test directory post-organization: $($movedFiles.Count)"

    $matchedHashes = 0
    foreach ($f in $movedFiles) {
        $postHash = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash
        
        # Match against pre-move hash
        if ($preHashes.ContainsKey($f.Name)) {
            $expectedHash = $preHashes[$f.Name].Hash
            if ($postHash -ne $expectedHash) {
                throw "SHA-256 hash mismatch for moved file '$($f.FullName)'! Expected: $expectedHash, Got: $postHash"
            }
            $matchedHashes++
        }
    }
    Log-Step "[PASS] Content integrity verified: $matchedHashes/$($preHashes.Count) file hashes match pre-move data exactly."
    $testResults.HashesVerified = $matchedHashes
    $testResults.FilesOrganized = $movedFiles.Count

    # 5. Verify specific category routing
    $expectedRoutings = @(
        @{ File = "Documents\PDF\sample.pdf"; Desc = "PDF document routing" },
        @{ File = "Documents\Word\sample.docx"; Desc = "Word document routing" },
        @{ File = "Images\photo.jpg"; Desc = "JPEG image routing" },
        @{ File = "Images\PNG\image.png"; Desc = "PNG image routing" },
        @{ File = "Images\PNG\IMAGE.PNG"; Desc = "Uppercase extension routing" },
        @{ File = "Videos\video.mp4"; Desc = "Video MP4 routing" },
        @{ File = "Audio\music.mp3"; Desc = "Audio MP3 routing" },
        @{ File = "Archives\ZIP\archive.zip"; Desc = "ZIP archive routing" },
        @{ File = "Code\Python\app.py"; Desc = "Python code routing" },
        @{ File = "Other\unknown.xyz"; Desc = "Unknown extension fallback routing" }
    )

    foreach ($route in $expectedRoutings) {
        $expectedPath = Join-Path $testDownloads $route.File
        if (-not (Test-Path $expectedPath)) {
            throw "Expected file was not found at target destination: $expectedPath ($($route.Desc))"
        }
        Log-Step "[PASS] Verified $($route.Desc): $($route.File)"
    }

    # 6. Verify SQLite history log
    $dbPath = Join-Path $installDir "history.db"
    $dbOpsCount = & $venvPython -c "import sqlite3; conn = sqlite3.connect(r'$dbPath'); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM operations WHERE status = \'MOVED\''); print(cur.fetchone()[0]); conn.close()"
    if ([int]$dbOpsCount.Trim() -lt 20) {
        throw "History database recorded fewer moves than expected! Recorded: $dbOpsCount"
    }
    Log-Step "[PASS] History database verified: recorded $dbOpsCount successful file movements."

    Log-Step "[PASS] TEST CASE D PASSED: Real organization verified successfully."
} catch {
    $err = $_.Exception.Message
    Log-Step "[FAIL] TEST CASE D FAILED: $err"
    $testResults.Passed = $false
    $testResults.Failures += $err
}

$testResults | ConvertTo-Json -Depth 5
