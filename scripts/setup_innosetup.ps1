# Setup Inno Setup 6 for building installers
$ErrorActionPreference = "Stop"

$tempExe = Join-Path $env:TEMP "innosetup-6.7.3.exe"
$url = "https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe"

Write-Host "Downloading Inno Setup from $url..." -ForegroundColor Cyan
curl.exe -L -o $tempExe $url

if (-not (Test-Path $tempExe)) {
    throw "Download failed"
}

Write-Host "Downloaded $(Get-Item $tempExe | Select-Object -ExpandProperty Length) bytes" -ForegroundColor Green

$installDir = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6"
Write-Host "Installing silently to $installDir..." -ForegroundColor Cyan
Start-Process -FilePath $tempExe -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER /DIR=`"$installDir`"" -Wait

$iscc = Join-Path $installDir "iscc.exe"
if (Test-Path $iscc) {
    Write-Host "Inno Setup successfully installed at $iscc" -ForegroundColor Green
    & $iscc /? | Select-Object -First 3
} else {
    Write-Host "Looking for iscc.exe..." -ForegroundColor Yellow
    Get-ChildItem -Path $env:LOCALAPPDATA -Filter "iscc.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
}
