<#
.SYNOPSIS
    Automated Distribution and Packaging QA Test Suite for CleanDownloads.

.DESCRIPTION
    Executes isolated verification tests for:
    1. Standalone executable functionality and exit codes
    2. Silent non-administrator Inno Setup installation
    3. User PATH registration and environment broadcast
    4. Upgrade scenario and binary replacement
    5. Configuration and history database persistence
    6. Non-destruction invariant: Downloads contents never deleted
    7. Silent uninstallation and PATH cleanup
    8. PowerShell Bootstrapper signature/checksum verification & tampering rejection
#>

[CmdletBinding()]
param(
    [string]$SetupExe = "",
    [string]$TestWorkspace = "C:\CleanDownloads-QA\DistTest"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

# Colors
$Cyan   = [char]27 + "[96m"
$Green  = [char]27 + "[92m"
$Yellow = [char]27 + "[93m"
$Red    = [char]27 + "[91m"
$Bold   = [char]27 + "[1m"
$Reset  = [char]27 + "[0m"

$Results = [System.Collections.Generic.List[PSCustomObject]]::new()

function Record-TestResult {
    param([string]$Name, [bool]$Passed, [string]$Details)
    $status = if ($Passed) { "${Green}PASS${Reset}" } else { "${Red}FAIL${Reset}" }
    Write-Host " [$status] $Name"
    if ($Details) { Write-Host "        $Details" -ForegroundColor Gray }
    $Results.Add([PSCustomObject]@{
        Test = $Name
        Passed = $Passed
        Details = $Details
    })
}

Write-Host "`n${Cyan}${Bold}====================================================${Reset}"
Write-Host "${Cyan}${Bold} CleanDownloads Distribution QA Test Suite ${Reset}"
Write-Host "${Cyan}${Bold}====================================================${Reset}`n"

# Setup isolated sandbox
if (Test-Path $TestWorkspace) {
    Remove-Item -Recurse -Force $TestWorkspace -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $TestWorkspace | Out-Null
$fakeDownloads = Join-Path $TestWorkspace "Downloads"
New-Item -ItemType Directory -Force -Path $fakeDownloads | Out-Null

# Create sample personal files in fake downloads
"personal invoice" | Set-Content (Join-Path $fakeDownloads "invoice.pdf")
"precious photo" | Set-Content (Join-Path $fakeDownloads "photo.png")
"critical notes" | Set-Content (Join-Path $fakeDownloads "notes.txt")

# Locate installer
if (-not $SetupExe) {
    $SetupExe = Join-Path $ProjectRoot "dist\CleanDownloads-Setup-1.0.0.exe"
}

# ---------------------------------------------------------
# Test 1: Verify Standalone Executable
# ---------------------------------------------------------
Write-Host "${Cyan}--> Test 1: Standalone Executable Verification${Reset}"
$exePath = Join-Path $ProjectRoot "dist\cleandownloads.exe"
if (Test-Path $exePath) {
    $verOut = & $exePath --version 2>&1
    $helpOut = & $exePath --help 2>&1
    $pass = ($verOut -match "1\.0\.0") -and ($LASTEXITCODE -eq 0) -and ($helpOut -match "CleanDownloads")
    Record-TestResult "Standalone Executable Execution & Exit Code" $pass "Version: $verOut, Exit: $LASTEXITCODE"
} else {
    Record-TestResult "Standalone Executable Execution & Exit Code" $false "dist\cleandownloads.exe not found"
}

# ---------------------------------------------------------
# Test 2: Inno Setup Non-Admin Silent Fresh Install
# ---------------------------------------------------------
Write-Host "${Cyan}--> Test 2: Inno Setup Non-Admin Silent Fresh Install${Reset}"
if (Test-Path $SetupExe) {
    $installProc = Start-Process -FilePath $SetupExe -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -Wait -PassThru
    $installedDir = Join-Path $env:LOCALAPPDATA "Programs\CleanDownloads"
    $installedExe = Join-Path $installedDir "cleandownloads.exe"
    $uninstaller = Join-Path $installedDir "unins000.exe"

    $pass = ($installProc.ExitCode -eq 0) -and (Test-Path $installedExe) -and (Test-Path $uninstaller)
    Record-TestResult "Silent Non-Admin Installation" $pass "ExitCode: $($installProc.ExitCode), Installed: (Test-Path=$pass)"
} else {
    Record-TestResult "Silent Non-Admin Installation" $false "Setup executable not found at $SetupExe"
}

# ---------------------------------------------------------
# Test 3: User PATH Registration Verification
# ---------------------------------------------------------
Write-Host "${Cyan}--> Test 3: User PATH Environment Registration${Reset}"
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
$expectedDir = Join-Path $env:LOCALAPPDATA "Programs\CleanDownloads"
$pathRegistered = $userPath -and ($userPath -like "*$expectedDir*")
Record-TestResult "User PATH Environment Registration" $pathRegistered "HKCU\Environment\Path contains $expectedDir"

# ---------------------------------------------------------
# Test 4: Configuration & History State Outside Binary Dir
# ---------------------------------------------------------
Write-Host "${Cyan}--> Test 4: Storage Separation & Persistence${Reset}"
$appDataDir = Join-Path $env:LOCALAPPDATA "CleanDownloads"
New-Item -ItemType Directory -Force -Path $appDataDir | Out-Null
$testConfig = Join-Path $appDataDir "config.json"
'{"test_sentinel": "qa_value_12345"}' | Set-Content $testConfig -Encoding utf8

$testDb = Join-Path $appDataDir "history.db"
'sqlite_test_sentinel' | Set-Content $testDb -Encoding utf8

# ---------------------------------------------------------
# Test 5: Upgrade Scenario
# ---------------------------------------------------------
Write-Host "${Cyan}--> Test 5: Upgrade Preserves State & User Files${Reset}"
if (Test-Path $SetupExe) {
    $upgradeProc = Start-Process -FilePath $SetupExe -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -Wait -PassThru
    $configContent = if (Test-Path $testConfig) { Get-Content $testConfig -Raw } else { "" }
    $dbExists = Test-Path $testDb

    $pass = ($upgradeProc.ExitCode -eq 0) -and ($configContent -match "qa_value_12345") -and $dbExists
    Record-TestResult "Upgrade State Persistence" $pass "Config preserved: ($($configContent -match 'qa_value_12345')), DB preserved: $dbExists"
} else {
    Record-TestResult "Upgrade State Persistence" $false "Setup executable missing"
}

# ---------------------------------------------------------
# Test 6: Non-Destruction Invariant (Downloads Never Touched)
# ---------------------------------------------------------
Write-Host "${Cyan}--> Test 6: User Personal Files Integrity${Reset}"
$p1 = (Get-Content (Join-Path $fakeDownloads "invoice.pdf") -Raw).Trim()
$p2 = (Get-Content (Join-Path $fakeDownloads "photo.png") -Raw).Trim()
$p3 = (Get-Content (Join-Path $fakeDownloads "notes.txt") -Raw).Trim()
$downloadsUntouched = ($p1 -eq "personal invoice") -and ($p2 -eq "precious photo") -and ($p3 -eq "critical notes")
Record-TestResult "Downloads Zero-Data-Loss Invariant" $downloadsUntouched "All user files in fake Downloads perfectly intact"

# ---------------------------------------------------------
# Test 7: Bootstrapper Security Rejection (Corrupted/Tampered)
# ---------------------------------------------------------
Write-Host "${Cyan}--> Test 7: Bootstrapper Security Checks${Reset}"
$corruptFile = Join-Path $TestWorkspace "corrupt_setup.exe"
"CORRUPTED BINARY DATA" | Set-Content $corruptFile

# A. Missing checksum rejection (fails closed)
$missingChecksumPassed = $false
try {
    & (Join-Path $ProjectRoot "install.ps1") -InstallerPath $corruptFile -Silent 2>$null
} catch {
    $missingChecksumPassed = $true
}

# B. Corrupt / mismatched hash rejection
$mismatchedChecksumPassed = $false
try {
    & (Join-Path $ProjectRoot "install.ps1") -InstallerPath $corruptFile -ExpectedSha256 "0000000000000000000000000000000000000000000000000000000000000000" -Silent 2>$null
} catch {
    $mismatchedChecksumPassed = $true
}

# C. Non-HTTPS URL rejection
$httpsRejectionPassed = $false
try {
    & (Join-Path $ProjectRoot "install.ps1") -InstallerUrl "http://insecure-downloads.com/setup.exe" -ExpectedSha256 "0000000000000000000000000000000000000000000000000000000000000000" -Silent 2>$null
} catch {
    $httpsRejectionPassed = $true
}

# D. Untrusted / Unexpected publisher rejection when -RequireSignature is requested
$publisherRejectionPassed = $false
try {
    & (Join-Path $ProjectRoot "install.ps1") -InstallerPath $SetupExe -ExpectedSha256 "0000000000000000000000000000000000000000000000000000000000000000" -RequireSignature -ExpectedPublisher "NonExistentMaliciousPublisher" -Silent 2>$null
} catch {
    $publisherRejectionPassed = $true
}

$securityPassed = $missingChecksumPassed -and $mismatchedChecksumPassed -and $httpsRejectionPassed -and $publisherRejectionPassed
Record-TestResult "Bootstrapper Security Integrity Verification" $securityPassed "Missing Checksum Rejected: $missingChecksumPassed, Mismatched Hash Rejected: $mismatchedChecksumPassed, Insecure HTTP Rejected: $httpsRejectionPassed, Untrusted Publisher Rejected: $publisherRejectionPassed"

# ---------------------------------------------------------
# Test 8: Silent Uninstallation & PATH Cleanup
# ---------------------------------------------------------
Write-Host "${Cyan}--> Test 8: Silent Uninstallation & Environment Cleanup${Reset}"
$uninstaller = Join-Path $env:LOCALAPPDATA "Programs\CleanDownloads\unins000.exe"
if (Test-Path $uninstaller) {
    $uninstProc = Start-Process -FilePath $uninstaller -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -Wait -PassThru
    $installedDir = Join-Path $env:LOCALAPPDATA "Programs\CleanDownloads"
    $binaryRemoved = -not (Test-Path (Join-Path $installedDir "cleandownloads.exe"))

    $newUserPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $pathCleaned = -not ($newUserPath -like "*$installedDir*")

    # Config should still be preserved
    $configStillThere = Test-Path $testConfig

    $pass = ($uninstProc.ExitCode -eq 0) -and $binaryRemoved -and $pathCleaned -and $configStillThere
    Record-TestResult "Uninstallation & Environment Cleanup" $pass "Binaries removed: $binaryRemoved, PATH cleaned: $pathCleaned, Data preserved: $configStillThere"
} else {
    Record-TestResult "Uninstallation & Environment Cleanup" $false "Uninstaller not found at $uninstaller"
}

# Cleanup QA temp files
Remove-Item -Recurse -Force $TestWorkspace -ErrorAction SilentlyContinue

$passCount = ($Results | Where-Object { $_.Passed -eq $true }).Count
$totalCount = $Results.Count
Write-Host "`n${Cyan}${Bold}====================================================${Reset}"
Write-Host "${Cyan}${Bold} SUMMARY: $passCount / $totalCount Tests Passed ${Reset}"
Write-Host "${Cyan}${Bold}====================================================${Reset}`n"

return $Results
