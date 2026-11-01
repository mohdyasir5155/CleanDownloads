<#
.SYNOPSIS
    Secure Windows Installer Bootstrapper for CleanDownloads CLI.

.DESCRIPTION
    Downloads, cryptographically verifies, and installs the latest stable release
    of CleanDownloads for the current Windows user without requiring administrator privileges.

.PARAMETER Version
    The specific version tag to install (e.g. '1.0.0'). Defaults to 'latest'.

.PARAMETER Repo
    The GitHub repository in 'owner/repo' format. Defaults to 'mohdyasir5155/CleanDownloads'.

.PARAMETER InstallerUrl
    Direct HTTPS URL to an installer executable. Overrides GitHub Release lookup.

.PARAMETER InstallerPath
    Direct local filesystem path to an installer executable (for offline testing/deployments).

.PARAMETER ExpectedSha256
    Expected SHA-256 checksum for the installer. If omitted, checksums are verified
    against the release checksums.txt.

.PARAMETER RequireSignature
    Opt-in flag requiring a valid Authenticode digital signature on the installer executable.

.PARAMETER ExpectedPublisher
    The expected Subject or CN in the Authenticode code signing certificate when -RequireSignature is enabled.
    Defaults to 'CleanDownloads'.

.PARAMETER Silent
    Perform installation silently without interactive prompts.

.PARAMETER Force
    Reinstall or upgrade without prompting if an existing installation is detected.

.PARAMETER AllowUnsigned
    Allows installing binaries signed with non-trusted development certificates when -RequireSignature is used.

.PARAMETER SkipSignatureCheck
    Deprecated: Authenticode signature verification is now opt-in via -RequireSignature.

.EXAMPLE
    irm https://raw.githubusercontent.com/mohdyasir5155/CleanDownloads/main/install.ps1 | iex

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1 -Version 1.0.0
#>

[CmdletBinding()]
param(
    [string]$Version = "latest",
    [string]$Repo = "mohdyasir5155/CleanDownloads",
    [string]$InstallerUrl = "",
    [string]$InstallerPath = "",
    [string]$ExpectedSha256 = "",
    [string]$ExpectedPublisher = "CleanDownloads",
    [switch]$Silent,
    [switch]$Force,
    [switch]$RequireSignature,
    [switch]$AllowUnsigned,
    [switch]$SkipSignatureCheck
)

$ErrorActionPreference = "Stop"

# Enforce secure TLS protocols
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

# Terminal Colors
$Cyan   = [char]27 + "[96m"
$Green  = [char]27 + "[92m"
$Yellow = [char]27 + "[93m"
$Red    = [char]27 + "[91m"
$Bold   = [char]27 + "[1m"
$Dim    = [char]27 + "[2m"
$Reset  = [char]27 + "[0m"

function Write-Banner {
    Write-Host ""
    Write-Host "${Cyan}${Bold}   CLEAN DOWNLOADS${Reset} ${Dim}Windows Bootstrapper${Reset}"
    Write-Host "${Dim}   One command. Zero clutter.${Reset}"
    Write-Host "   ────────────────────────────────────────────────"
    Write-Host ""
}

Write-Banner

# 1. Environment Verification
Write-Host "${Cyan}-->${Reset} Verifying operating system environment..."
if (-not ($IsWindows -or ($env:OS -like "*Windows*"))) {
    Write-Host "${Red}Error: CleanDownloads is designed exclusively for Microsoft Windows.${Reset}"
    throw "CleanDownloads requires Microsoft Windows."
}

$arch = $env:PROCESSOR_ARCHITECTURE
if ($arch -notin @("AMD64", "ARM64")) {
    Write-Host "${Red}Error: Unsupported architecture '$arch'. CleanDownloads requires Windows x64.${Reset}"
    throw "Unsupported architecture '$arch'."
}
Write-Host "    Detected Windows ($arch) - Standard User Context"

# 2. Existing Installation Detection
$localAppData = $env:LOCALAPPDATA
if (-not $localAppData) {
    $localAppData = Join-Path $env:USERPROFILE "AppData\Local"
}
$installDir = Join-Path $localAppData "Programs\CleanDownloads"
$installedExe = Join-Path $installDir "cleandownloads.exe"

if (Test-Path $installedExe) {
    $currentVersion = "unknown"
    try {
        $verOut = & $installedExe --version 2>$null
        if ($verOut -match "(\d+\.\d+\.\d+)") {
            $currentVersion = $matches[1]
        }
    } catch {}

    Write-Host "${Yellow}--> Existing installation detected:${Reset} $installedExe (v$currentVersion)"

    if (-not $Force -and -not $Silent) {
        $confirm = Read-Host "    Do you want to reinstall or upgrade CleanDownloads? (y/N)"
        if ($confirm -notmatch "^[Yy]$") {
            Write-Host "${Dim}Installation cancelled by user.${Reset}"
            exit 0
        }
    } else {
        Write-Host "    Proceeding with upgrade/reinstall..."
    }
}

# 3. Resolve Target Installer Binary
$targetInstaller = ""
$isTempFile = $false
$targetVersion = $Version
$releaseChecksums = $ExpectedSha256

if ($InstallerPath) {
    if (-not (Test-Path $InstallerPath)) {
        throw "Specified InstallerPath does not exist: $InstallerPath"
    }
    $targetInstaller = (Resolve-Path $InstallerPath).Path
    Write-Host "${Cyan}-->${Reset} Using local installer binary: $targetInstaller"
} else {
    $downloadUrl = $InstallerUrl

    if (-not $downloadUrl) {
        Write-Host "${Cyan}-->${Reset} Resolving release from GitHub ($Repo)..."
        $apiUrl = if ($Version -eq "latest") {
            "https://api.github.com/repos/$Repo/releases/latest"
        } else {
            "https://api.github.com/repos/$Repo/releases/tags/v$Version"
        }

        try {
            $headers = @{ "User-Agent" = "CleanDownloads-Bootstrapper" }
            $release = Invoke-RestMethod -Uri $apiUrl -Headers $headers -UseBasicParsing -TimeoutSec 15
            $targetVersion = $release.tag_name -replace "^v", ""
            Write-Host "    Target Version: v$targetVersion"

            # Locate setup installer and checksums file
            $setupAsset = $release.assets | Where-Object { $_.name -like "CleanDownloads-Setup-*.exe" } | Select-Object -First 1
            $checksumAsset = $release.assets | Where-Object { $_.name -eq "checksums.txt" } | Select-Object -First 1

            if (-not $setupAsset) {
                throw "Could not find CleanDownloads-Setup-*.exe in release v$targetVersion"
            }

            $downloadUrl = $setupAsset.browser_download_url

            if (-not $releaseChecksums -and $checksumAsset) {
                Write-Host "    Fetching release checksums.txt..."
                $checksumText = (Invoke-RestMethod -Uri $checksumAsset.browser_download_url -Headers $headers -UseBasicParsing -TimeoutSec 10)
                if ($checksumText) {
                    foreach ($line in ($checksumText -split "`r?`n")) {
                        if ($line -match "^([a-fA-F0-9]{64})\s+\*?$([regex]::Escape($setupAsset.name))") {
                            $releaseChecksums = $matches[1]
                            break
                        }
                    }
                }
            }
        } catch {
            Write-Host "${Red}Error: Failed to resolve release from GitHub ($Repo): $($_.Exception.Message)${Reset}"
            throw
        }
    }

    # Strict HTTPS Enforcement
    if (-not ($downloadUrl -like "https://*")) {
        Write-Host "${Red}Security Error: Installer URL must use HTTPS ($downloadUrl).${Reset}"
        throw "Security Error: Installer URL must use HTTPS ($downloadUrl)."
    }

    # Download Installer to Temp Location
    $targetInstaller = Join-Path $env:TEMP "CleanDownloads-Setup-$targetVersion-$([Guid]::NewGuid().ToString('N')).exe"
    $isTempFile = $true
    Write-Host "${Cyan}-->${Reset} Downloading installer..."
    Write-Host "    Source: $downloadUrl"
    Write-Host "    Temp:   $targetInstaller"

    try {
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers.Add("User-Agent", "CleanDownloads-Bootstrapper")
        $webClient.DownloadFile($downloadUrl, $targetInstaller)
    } catch {
        Write-Host "${Red}Error: Failed to download installer from $downloadUrl${Reset}"
        Write-Host "Details: $($_.Exception.Message)"
        if ($isTempFile -and (Test-Path $targetInstaller)) { Remove-Item -Force $targetInstaller -ErrorAction SilentlyContinue }
        throw "Download failed: $($_.Exception.Message)"
    }

    if (-not (Test-Path $targetInstaller) -or (Get-Item $targetInstaller).Length -lt 1024) {
        Write-Host "${Red}Error: Downloaded installer file is missing or corrupted.${Reset}"
        if ($isTempFile -and (Test-Path $targetInstaller)) { Remove-Item -Force $targetInstaller -ErrorAction SilentlyContinue }
        throw "Downloaded installer file is missing or corrupted."
    }

    Write-Host "    Download completed ($([math]::Round((Get-Item $targetInstaller).Length / 1MB, 2)) MB)"
}

try {
    # 4. Cryptographic Integrity Verification (SHA-256)
    Write-Host "${Cyan}-->${Reset} Verifying SHA-256 file integrity..."
    if (-not $releaseChecksums) {
        Write-Host "${Red}FATAL SECURITY ERROR: Mandatory SHA-256 checksum is missing!${Reset}"
        Write-Host "  Could not obtain checksum from release checksums.txt and no -ExpectedSha256 was provided."
        Write-Host "  CleanDownloads requires cryptographic checksum verification and fails closed."
        throw "FATAL SECURITY ERROR: Mandatory SHA-256 checksum is missing. Aborting installation."
    }

    $computedHash = (Get-FileHash -Path $targetInstaller -Algorithm SHA256).Hash
    if ($computedHash.ToUpperInvariant() -ne $releaseChecksums.ToUpperInvariant()) {
        Write-Host "${Red}FATAL SECURITY ERROR: SHA-256 checksum mismatch!${Reset}"
        Write-Host "  Expected: $($releaseChecksums.ToUpperInvariant())"
        Write-Host "  Computed: $($computedHash.ToUpperInvariant())"
        throw "FATAL SECURITY ERROR: SHA-256 checksum mismatch (Expected: $releaseChecksums, Computed: $computedHash)"
    }
    Write-Host "    ${Green}SHA-256 verified successfully:${Reset} $computedHash"

    # 4b. GitHub Artifact Attestation Verification (when gh CLI is available)
    $ghCli = Get-Command gh -ErrorAction SilentlyContinue
    if ($ghCli) {
        Write-Host "${Cyan}-->${Reset} Verifying GitHub artifact attestation against $Repo..."
        try {
            $attestOutput = & $ghCli.Source attestation verify $targetInstaller --repo $Repo 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ${Green}GitHub artifact attestation verified successfully.${Reset}"
            } else {
                Write-Warning "GitHub artifact attestation check returned non-zero ($LASTEXITCODE): $attestOutput"
            }
        } catch {
            Write-Warning "Could not verify attestation via gh CLI: $($_.Exception.Message)"
        }
    }

    # 5. Authenticode Digital Signature Verification (Opt-in via -RequireSignature)
    if ($RequireSignature) {
        Write-Host "${Cyan}-->${Reset} Verifying Authenticode digital signature (-RequireSignature enabled)..."
        $sig = Get-AuthenticodeSignature -FilePath $targetInstaller

        if ($sig.Status -eq "Valid") {
            Write-Host "    Signature is cryptographically valid."
            if ($ExpectedPublisher) {
                $subject = $sig.SignerCertificate.Subject
                if ($subject -notmatch [regex]::Escape($ExpectedPublisher)) {
                    Write-Host "${Red}FATAL SECURITY ERROR: Unexpected publisher in certificate!${Reset}"
                    Write-Host "  Expected: $ExpectedPublisher"
                    Write-Host "  Signer:   $subject"
                    throw "FATAL SECURITY ERROR: Unexpected publisher in certificate: $subject"
                }
                Write-Host "    ${Green}Publisher identity verified:${Reset} $subject"
            }
        } elseif ($AllowUnsigned) {
            Write-Warning "Signature verification bypassed via -AllowUnsigned. (Status: $($sig.Status))"
        } else {
            Write-Host "${Red}FATAL SECURITY ERROR: Installer Authenticode signature is invalid or not trusted!${Reset}"
            Write-Host "  Signature Status: $($sig.Status)"
            Write-Host "  Status Message:   $($sig.StatusMessage)"
            Write-Host "  To install anyway in development environments, omit -RequireSignature or use -AllowUnsigned."
            throw "FATAL SECURITY ERROR: Installer Authenticode signature is invalid or not trusted (Status: $($sig.Status))"
        }
    } else {
        Write-Host "    Authenticode signature verification is opt-in (use -RequireSignature to enforce)."
    }

    # 6. Execute Installer
    Write-Host "${Cyan}-->${Reset} Executing Windows installer..."
    $installerArgs = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART")

    try {
        $proc = Start-Process -FilePath $targetInstaller -ArgumentList $installerArgs -Wait -PassThru -NoNewWindow
        if ($proc.ExitCode -ne 0) {
            Write-Host "${Red}Error: Installer returned non-zero exit code: $($proc.ExitCode)${Reset}"
            throw "Installer exited with code: $($proc.ExitCode)"
        }
    } catch {
        Write-Host "${Red}Error: Failed to launch installer: $($_.Exception.Message)${Reset}"
        throw "Failed to launch installer: $($_.Exception.Message)"
    }

    # 7. Post-Installation Verification
    Write-Host "${Cyan}-->${Reset} Verifying installed binary..."
    if (-not (Test-Path $installedExe)) {
        Write-Host "${Red}Error: Expected binary not found at $installedExe after installation.${Reset}"
        throw "Installed binary missing at $installedExe"
    }

    # Update PATH for the current session
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$userPath;$installDir;$env:Path"

    $verCheck = & $installedExe --version 2>&1
    Write-Host "    ${Green}Verified CleanDownloads binary:${Reset} $verCheck"

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  CleanDownloads v$targetVersion was installed successfully!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Location: $installDir"
    Write-Host "  Data Dir: $localAppData\CleanDownloads  (Preserved during upgrades)"
    Write-Host ""
    Write-Host "  Get started:" -ForegroundColor Cyan
    Write-Host "    cleandownloads --help" -ForegroundColor White
    Write-Host "    cleandownloads scan --dry-run" -ForegroundColor White
    Write-Host "    cleandownloads status" -ForegroundColor White
    Write-Host ""
    Write-Host "${Dim}Note: If 'cleandownloads' is not recognized in an existing shell, restart your terminal.${Reset}"
    Write-Host ""

} finally {
    if ($isTempFile -and (Test-Path $targetInstaller)) {
        Remove-Item -Force $targetInstaller -ErrorAction SilentlyContinue
    }
}
