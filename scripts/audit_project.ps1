# Project Audit Script for CleanDownloads
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " CleanDownloads Repository Audit Report " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Check Version Consistency
Write-Host "`n[1] Checking Version Consistency across Files..." -ForegroundColor Yellow
$pyprojectContent = Get-Content (Join-Path $ProjectRoot "pyproject.toml") -Raw
$initContent = Get-Content (Join-Path $ProjectRoot "src\cleandownloads\__init__.py") -Raw
$versionInfoContent = Get-Content (Join-Path $ProjectRoot "version_info.txt") -Raw
$issContent = Get-Content (Join-Path $ProjectRoot "installer\CleanDownloads.iss") -Raw
$wingetContent = Get-Content (Join-Path $ProjectRoot "winget\manifests\c\CleanDownloads\CleanDownloads\1.0.0\CleanDownloads.CleanDownloads.yaml") -Raw

$pyprojectVer = if ($pyprojectContent -match 'version\s*=\s*"([^"]+)"') { $matches[1] } else { "NOT FOUND" }
$initVer = if ($initContent -match '__version__\s*=\s*"([^"]+)"') { $matches[1] } else { "NOT FOUND" }
$issVer = if ($issContent -match '#define\s+MyAppVersion\s+"([^"]+)"') { $matches[1] } else { "NOT FOUND" }
$wingetVer = if ($wingetContent -match 'PackageVersion:\s*([0-9\.]+)') { $matches[1] } else { "NOT FOUND" }

Write-Host "  pyproject.toml:                 $pyprojectVer"
Write-Host "  src/cleandownloads/__init__.py: $initVer"
Write-Host "  installer/CleanDownloads.iss:   $issVer"
Write-Host "  winget manifest:                $wingetVer"

if ($pyprojectVer -eq $initVer -and $initVer -eq $issVer -and $issVer -eq $wingetVer) {
    Write-Host "  [PASS] All version declarations match: v$pyprojectVer" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Version mismatch detected!" -ForegroundColor Red
}

# 2. Secret & Sensitive Data Audit
Write-Host "`n[2] Scanning for Secrets / API Keys / Credentials..." -ForegroundColor Yellow
$suspiciousPatterns = @(
    '(?i)(api[_-]?key|secret|password|access[_-]?token|bearer\s+[a-z0-9_-]{20,})',
    '(?i)(ghp_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{22,})',
    '-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----'
)

$flagged = @()
$sourceFiles = Get-ChildItem -Path $ProjectRoot -Recurse -File | Where-Object {
    $_.FullName -notmatch '\\(\.git|\.venv|\.pytest_cache|\.ruff_cache|build|dist|TestResults|desktop\\node_modules|desktop\\dist)\\'
}

foreach ($file in $sourceFiles) {
    # Skip binary files
    if ($file.Extension -in @(".exe", ".db", ".ico", ".png", ".jpg", ".zip", ".whl")) { continue }
    $text = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $text) { continue }
    
    foreach ($pat in $suspiciousPatterns) {
        if ($text -match $pat) {
            # Exclude known benign false positives like schema documentation or regex pattern rules
            $matchLine = ($text -split "`r?`n" | Select-String -Pattern $pat | Select-Object -First 1).Line.Trim()
            if ($matchLine -notmatch "YOUR_USERNAME|<YOUR_GITHUB_PAT>|fake|test|pattern|dummy|schema") {
                $flagged += "$($file.FullName): $matchLine"
            }
        }
    }
}

if ($flagged.Count -eq 0) {
    Write-Host "  [PASS] Zero secrets or leaked credentials found across $($sourceFiles.Count) files scanned." -ForegroundColor Green
} else {
    Write-Host "  [WARN] Potential secrets flagged:" -ForegroundColor Red
    $flagged | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
}

# 3. Identify Transient & Generated Directories to Exclude from Git
Write-Host "`n[3] Auditing Transient / Generated Assets for .gitignore..." -ForegroundColor Yellow
$transientDirs = @(
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "build",
    "dist",
    "TestResults",
    "desktop/node_modules",
    "desktop/dist"
)

foreach ($d in $transientDirs) {
    $p = Join-Path $ProjectRoot $d
    if (Test-Path $p) {
        Write-Host "  [FOUND] $d (Will be ignored by .gitignore)" -ForegroundColor Gray
    }
}

# 4. Check gitignore configuration
$gitignorePath = Join-Path $ProjectRoot ".gitignore"
if (Test-Path $gitignorePath) {
    Write-Host "`n[4] .gitignore exists ($(Get-Item $gitignorePath | Select-Object -ExpandProperty Length) bytes)." -ForegroundColor Green
} else {
    Write-Host "`n[4] .gitignore is missing!" -ForegroundColor Red
}

Write-Host "`n[Audit Complete]" -ForegroundColor Cyan
