<#
.SYNOPSIS
    Builds the CleanDownloads Inno Setup Windows Installer.

.DESCRIPTION
    Compiles installer/CleanDownloads.iss into dist/CleanDownloads-Setup-1.0.0.exe,
    signs the installer with a code signing certificate if available,
    and calculates the SHA-256 hash for release verification and WinGet manifest generation.

.EXAMPLE
    pwsh scripts/build_installer.ps1
#>

[CmdletBinding()]
param(
    [string]$Version = "1.0.0",
    [string]$CertificateThumbprint = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host " Building CleanDownloads Windows Setup Installer v$Version " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Ensure dist/cleandownloads.exe exists
$ExePath = Join-Path $ProjectRoot "dist\cleandownloads.exe"
if (-not (Test-Path $ExePath)) {
    Write-Host "[!] dist\cleandownloads.exe not found. Building executable first..." -ForegroundColor Yellow
    & (Join-Path $ScriptDir "build_executable.ps1")
    if (-not (Test-Path $ExePath)) {
        throw "Failed to find or build dist\cleandownloads.exe"
    }
}

# 2. Locate ISCC (Inno Setup Compiler)
$IsccCandidates = @(
    (Get-Command iscc.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "${env:ProgramFiles(x86)}\Inno Setup 6\iscc.exe",
    "$env:ProgramFiles\Inno Setup 6\iscc.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\iscc.exe",
    "C:\Program Files (x86)\Inno Setup 6\iscc.exe",
    "C:\Program Files\Inno Setup 6\iscc.exe"
)

$IsccPath = $null
foreach ($cand in $IsccCandidates) {
    if ($cand -and (Test-Path $cand)) {
        $IsccPath = $cand
        break
    }
}

if (-not $IsccPath) {
    throw "Inno Setup Compiler (iscc.exe) not found. Please install Inno Setup 6 (e.g. winget install JRSoftware.InnoSetup)."
}

Write-Host "[+] Found Inno Setup Compiler: $IsccPath" -ForegroundColor Green

# 3. Compile Inno Setup Script
$IssPath = Join-Path $ProjectRoot "installer\CleanDownloads.iss"
if (-not (Test-Path $IssPath)) {
    throw "Inno Setup script not found at $IssPath"
}

Write-Host "[*] Compiling installer..." -ForegroundColor Cyan
$compileOutput = & $IsccPath "/DMyAppVersion=$Version" $IssPath
Write-Host $compileOutput

$SetupExe = Join-Path $ProjectRoot "dist\CleanDownloads-Setup-$Version.exe"
if (-not (Test-Path $SetupExe)) {
    throw "Setup executable not created at $SetupExe"
}

$SetupInfo = Get-Item $SetupExe
Write-Host "[+] Setup generated successfully: $($SetupInfo.FullName)" -ForegroundColor Green
Write-Host "    Size: $([math]::Round($SetupInfo.Length / 1MB, 2)) MB ($($SetupInfo.Length) bytes)" -ForegroundColor Gray

# 4. Sign Setup Executable if Certificate Available
$cert = $null
if ($CertificateThumbprint) {
    $cert = Get-Item "Cert:\CurrentUser\My\$CertificateThumbprint" -ErrorAction SilentlyContinue
}
if (-not $cert) {
    $cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue | Select-Object -First 1
}

if ($cert) {
    Write-Host "[*] Signing installer with certificate: $($cert.Subject) [$($cert.Thumbprint)]" -ForegroundColor Cyan
    $sig = Set-AuthenticodeSignature -FilePath $SetupExe -Certificate $cert -HashAlgorithm SHA256
    Write-Host "    Signature status: $($sig.Status)" -ForegroundColor Green
} else {
    Write-Host "[!] No code signing certificate found. Setup executable remains unsigned." -ForegroundColor Yellow
}

# 5. Compute SHA-256 Checksum
$Hash = (Get-FileHash -Path $SetupExe -Algorithm SHA256).Hash
Write-Host "`n====================================================" -ForegroundColor Green
Write-Host " BUILD SUMMARY" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host " File:   CleanDownloads-Setup-$Version.exe" -ForegroundColor White
Write-Host " Path:   $SetupExe" -ForegroundColor White
Write-Host " SHA256: $Hash" -ForegroundColor Yellow
Write-Host "====================================================" -ForegroundColor Green

# 6. Save or update checksums.txt in dist/
$ChecksumFile = Join-Path $ProjectRoot "dist\checksums.txt"
$ChecksumLines = @(
    "$((Get-FileHash -Path $ExePath -Algorithm SHA256).Hash.ToLower()) *cleandownloads.exe",
    "$($Hash.ToLower()) *CleanDownloads-Setup-$Version.exe"
)
$ChecksumLines | Out-File -FilePath $ChecksumFile -Encoding utf8
Write-Host "[+] Updated checksums saved to $ChecksumFile" -ForegroundColor Green

return @{
    InstallerPath = $SetupExe
    SHA256 = $Hash
    Version = $Version
}
