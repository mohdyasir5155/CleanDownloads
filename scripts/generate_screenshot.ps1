# Generate High-Resolution Terminal Screenshot
Add-Type -AssemblyName System.Drawing

$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
$assetsDir = Join-Path $repoRoot "assets"
if (-not (Test-Path $assetsDir)) { New-Item -ItemType Directory -Path $assetsDir -Force | Out-Null }

$screenshotPath = Join-Path $assetsDir "screenshot-main.png"

$width = 1500
$height = 980

$bmp = New-Object System.Drawing.Bitmap($width, $height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias

# Colors
$bgColor = [System.Drawing.Color]::FromArgb(255, 13, 17, 23)
$titleBg = [System.Drawing.Color]::FromArgb(255, 22, 27, 34)
$tabBg = [System.Drawing.Color]::FromArgb(255, 30, 37, 48)
$borderColor = [System.Drawing.Color]::FromArgb(255, 48, 54, 61)
$textColor = [System.Drawing.Color]::FromArgb(255, 230, 237, 243)
$cyanColor = [System.Drawing.Color]::FromArgb(255, 56, 189, 248)
$greenColor = [System.Drawing.Color]::FromArgb(255, 63, 185, 80)
$yellowColor = [System.Drawing.Color]::FromArgb(255, 210, 153, 34)
$dimColor = [System.Drawing.Color]::FromArgb(255, 139, 148, 158)
$blueColor = [System.Drawing.Color]::FromArgb(255, 88, 166, 255)

# Outer Canvas
$g.Clear([System.Drawing.Color]::FromArgb(255, 8, 11, 16))

# Window bounds
$wX = 35
$wY = 35
$wW = $width - 70
$wH = $height - 70

# Window Body
$bodyBrush = New-Object System.Drawing.SolidBrush($bgColor)
$g.FillRectangle($bodyBrush, $wX, $wY, $wW, $wH)

# Window Border
$borderPen = New-Object System.Drawing.Pen($borderColor, 2)
$g.DrawRectangle($borderPen, $wX, $wY, $wW, $wH)

# Title Bar
$titleBrush = New-Object System.Drawing.SolidBrush($titleBg)
$g.FillRectangle($titleBrush, $wX, $wY, $wW, 42)

# Tab
$tabBrush = New-Object System.Drawing.SolidBrush($tabBg)
$g.FillRectangle($tabBrush, $wX + 16, $wY + 6, 240, 36)

# Fonts
$fontFamily = "Consolas"
$tabFont = New-Object System.Drawing.Font($fontFamily, 10, [System.Drawing.FontStyle]::Bold)
$titleTextBrush = New-Object System.Drawing.SolidBrush($textColor)
$g.DrawString("PowerShell - CleanDownloads", $tabFont, $titleTextBrush, ($wX + 26), ($wY + 16))

# Window buttons
$g.FillEllipse((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 35, 134, 54))), ($wX + $wW - 68), ($wY + 15), 12, 12)
$g.FillEllipse((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 210, 153, 34))), ($wX + $wW - 48), ($wY + 15), 12, 12)
$g.FillEllipse((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 248, 81, 73))), ($wX + $wW - 28), ($wY + 15), 12, 12)

# Terminal Text Lines
$termFont = New-Object System.Drawing.Font($fontFamily, 12, [System.Drawing.FontStyle]::Regular)
$termBoldFont = New-Object System.Drawing.Font($fontFamily, 12, [System.Drawing.FontStyle]::Bold)

$lines = @(
    @("PS C:\Users\User> cleandownloads status", $cyanColor, $true),
    @("", $textColor, $false),
    @("   CLEAN DOWNLOADS v1.0.0", $cyanColor, $true),
    @("   One command. Zero clutter.", $dimColor, $false),
    @("   ------------------------------------------------------------", $dimColor, $false),
    @("SYSTEM & CONFIGURATION STATUS", $blueColor, $true),
    @("  Version:                1.0.0", $textColor, $false),
    @("  Downloads Directory:    C:\Users\User\Downloads", $textColor, $false),
    @("  App Data Directory:     C:\Users\User\AppData\Local\CleanDownloads", $textColor, $false),
    @("  Recursive Scanning:     False", $textColor, $false),
    @("  Active Organized Files: 73", $greenColor, $true),
    @("  Total Batches Run:      8", $textColor, $false),
    @("  Total Undone Files:     35", $textColor, $false),
    @("", $textColor, $false),
    @("PS C:\Users\User> cleandownloads preview", $cyanColor, $true),
    @("", $textColor, $false),
    @("PREVIEW - 6 files ready", $yellowColor, $true),
    @("", $textColor, $false),
    @("annual_report_2026.docx  (1.4 MB)", $textColor, $true),
    @("  Downloads\annual_report_2026.docx", $dimColor, $false),
    @("  -> Downloads\Documents\Word\annual_report_2026.docx", $greenColor, $false),
    @("invoice_october.pdf  (324.5 KB)", $textColor, $true),
    @("  Downloads\invoice_october.pdf", $dimColor, $false),
    @("  -> Downloads\Documents\PDF\invoice_october.pdf", $greenColor, $false),
    @("screenshot_01.png  (2.1 MB)", $textColor, $true),
    @("  Downloads\screenshot_01.png", $dimColor, $false),
    @("  -> Downloads\Images\PNG\screenshot_01.png", $greenColor, $false),
    @("vscode_setup.exe  (92.4 MB)", $textColor, $true),
    @("  Downloads\vscode_setup.exe", $dimColor, $false),
    @("  -> Downloads\Software\EXE\vscode_setup.exe", $greenColor, $false),
    @("", $textColor, $false),
    @("FILE BREAKDOWN", $blueColor, $true),
    @("------------------------------------------------------------", $dimColor, $false),
    @("  Documents: 2  |  Images: 1  |  Archives: 1  |  Software: 1", $textColor, $false),
    @("  Total: 6 files (140.2 MB) ready for organization", $textColor, $true),
    @("------------------------------------------------------------", $dimColor, $false),
    @("[DRY RUN COMPLETE] Zero files modified. Run 'cleandownloads organize' to apply.", $greenColor, $true)
)

$curY = $wY + 56
$curX = $wX + 24
$lineHeight = 22

foreach ($item in $lines) {
    $text = $item[0]
    $color = $item[1]
    $isBold = $item[2]
    $f = if ($isBold) { $termBoldFont } else { $termFont }
    $brush = New-Object System.Drawing.SolidBrush($color)
    $g.DrawString($text, $f, $brush, $curX, $curY)
    $curY += $lineHeight
}

# Save Screenshot PNG
$bmp.Save($screenshotPath, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
Write-Host "[+] Generated screenshot-main.png at: $screenshotPath"
