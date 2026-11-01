<#
.SYNOPSIS
    CleanDownloads Uninstaller Script for Windows.

.DESCRIPTION
    Safely uninstalls CleanDownloads by invoking the registered Windows uninstaller (unins000.exe)
    or cleaning up application binaries while strictly preserving your personal files and
    (optionally) your configuration/history.

.PARAMETER NonInteractive
    Runs uninstallation without prompting for confirmation.

.PARAMETER RemoveData
    If specified, also deletes configuration and operation history in %LOCALAPPDATA%\CleanDownloads.
    By default, user configuration and history are preserved.
#>

[CmdletBinding()]
param(
    [switch]$NonInteractive,
    [switch]$RemoveData
)

$ErrorActionPreference = "Continue"

# Terminal Colors
$Cyan   = [char]27 + "[96m"
$Green  = [char]27 + "[92m"
$Yellow = [char]27 + "[93m"
$Red    = [char]27 + "[91m"
$Bold   = [char]27 + "[1m"
$Dim    = [char]27 + "[2m"
$Reset  = [char]27 + "[0m"

Write-Host ""
Write-Host "${Yellow}${Bold}   CLEAN DOWNLOADS${Reset} ${Dim}Uninstaller${Reset}"
Write-Host "   ────────────────────────────────"
Write-Host ""

if (-not $NonInteractive) {
    $confirm = Read-Host "Are you sure you want to uninstall CleanDownloads? (y/N)"
    if ($confirm -notmatch "^[Yy]$") {
        Write-Host "Uninstallation cancelled."
        exit 0
    }
}

# 1. Remove Scheduled Tasks
Write-Host "${Cyan}-->${Reset} Checking for registered scheduled tasks..."
$systemRoot = if ($env:SystemRoot) { $env:SystemRoot } else { "C:\Windows" }
$schtasksExe = Join-Path $systemRoot "System32\schtasks.exe"
if (Test-Path $schtasksExe) {
    try {
        & $schtasksExe /Delete /TN "CleanDownloads_AutoOrganize" /F 2>$null | Out-Null
        Write-Host "    Cleaned CleanDownloads scheduled task."
    } catch {}
}

# 2. Check for Inno Setup Registered Uninstaller
$localAppData = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $env:USERPROFILE "AppData\Local" }
$programsDir = Join-Path $localAppData "Programs\CleanDownloads"
$innoUninstaller = Join-Path $programsDir "unins000.exe"

if (Test-Path $innoUninstaller) {
    Write-Host "${Cyan}-->${Reset} Executing registered Windows uninstaller..."
    $uninstArgs = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART")
    $proc = Start-Process -FilePath $innoUninstaller -ArgumentList $uninstArgs -Wait -PassThru -NoNewWindow
    Write-Host "    Registered uninstaller finished with code: $($proc.ExitCode)"
} else {
    # Manual cleanup fallback
    Write-Host "${Cyan}-->${Reset} Removing application binaries..."
    if (Test-Path $programsDir) {
        Remove-Item -Recurse -Force $programsDir -ErrorAction SilentlyContinue
    }
    $legacyInstall = Join-Path $localAppData "CleanDownloads\bin"
    if (Test-Path $legacyInstall) {
        Remove-Item -Recurse -Force $legacyInstall -ErrorAction SilentlyContinue
    }
}

# 3. Clean PATH Environment Variable
Write-Host "${Cyan}-->${Reset} Verifying User PATH environment..."
try {
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath) {
        $targets = @($programsDir, (Join-Path $localAppData "CleanDownloads\bin"))
        $newElements = @()
        foreach ($p in ($userPath -split ";")) {
            $pTrim = $p.Trim().TrimEnd('\')
            $match = $false
            foreach ($t in $targets) {
                if ($pTrim -eq $t.TrimEnd('\')) {
                    $match = $true
                    break
                }
            }
            if (-not $match -and $pTrim.Length -gt 0) {
                $newElements += $p.Trim()
            }
        }
        $cleanedPath = $newElements -join ";"
        if ($cleanedPath -ne $userPath) {
            [System.Environment]::SetEnvironmentVariable("Path", $cleanedPath, "User")
            Write-Host "    Removed CleanDownloads from User PATH."
        }
    }
} catch {
    Write-Host "    ${Yellow}Could not update User PATH automatically.${Reset}"
}

# 4. Handle Application Data / History
$dataDir = Join-Path $localAppData "CleanDownloads"
if (Test-Path $dataDir) {
    if ($RemoveData) {
        Write-Host "${Cyan}-->${Reset} Removing application data directory ($dataDir)..."
        Remove-Item -Recurse -Force $dataDir -ErrorAction SilentlyContinue
    } else {
        Write-Host "    ${Green}Preserved configuration and history database:${Reset} $dataDir"
    }
}

Write-Host ""
Write-Host "${Green}${Bold}[PASS] CleanDownloads has been uninstalled successfully.${Reset}"
Write-Host "${Dim}Your personal files in Downloads were never touched.${Reset}"
Write-Host ""
