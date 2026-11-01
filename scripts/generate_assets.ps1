# Generate High-Resolution Terminal Screenshot and Demo Animation using .NET System.Drawing
Add-Type -AssemblyName System.Drawing

$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
$assetsDir = Join-Path $repoRoot "assets"
if (-not (Test-Path $assetsDir)) { New-Item -ItemType Directory -Path $assetsDir -Force | Out-Null }

$screenshotPath = Join-Path $assetsDir "screenshot-main.png"

# Dimensions
$width = 1600
$height = 1080

$bmp = New-Object System.Drawing.Bitmap($width, $height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias

# Colors
$bgColor = [System.Drawing.Color]::FromArgb(255, 12, 16, 24)
$titleBg = [System.Drawing.Color]::FromArgb(255, 18, 24, 38)
$tabBg = [System.Drawing.Color]::FromArgb(255, 26, 34, 52)
$borderColor = [System.Drawing.Color]::FromArgb(255, 45, 55, 75)
$textColor = [System.Drawing.Color]::FromArgb(255, 226, 232, 240)
$cyanColor = [System.Drawing.Color]::FromArgb(255, 56, 189, 248)
$greenColor = [System.Drawing.Color]::FromArgb(255, 74, 222, 128)
$yellowColor = [System.Drawing.Color]::FromArgb(255, 250, 204, 21)
$dimColor = [System.Drawing.Color]::FromArgb(255, 148, 163, 184)
$redColor = [System.Drawing.Color]::FromArgb(255, 248, 113, 113)

# Background
$g.Clear([System.Drawing.Color]::FromArgb(255, 8, 11, 18))

# Window Container (Margin 40px)
$wX = 40
$wY = 40
$wW = $width - 80
$wH = $height - 80

# Window drop shadow
$shadowBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(90, 0, 0, 0))
$g.FillRectangle($shadowBrush, $wX + 10, $wY + 12, $wW, $wH)

# Window Body
$bodyBrush = New-Object System.Drawing.SolidBrush($bgColor)
$g.FillRectangle($bodyBrush, $wX, $wY, $wW, $wH)

# Window Border
$borderPen = New-Object System.Drawing.Pen($borderColor, 2)
$g.DrawRectangle($borderPen, $wX, $wY, $wW, $wH)

# Title Bar
$titleBrush = New-Object System.Drawing.SolidBrush($titleBg)
$g.FillRectangle($titleBrush, $wX, $wY, $wW, 44)

# Tab
$tabBrush = New-Object System.Drawing.SolidBrush($tabBg)
$g.FillRectangle($tabBrush, $wX + 16, $wY + 8, 260, 36)

# Fonts
$fontFamily = "Consolas"
try {
    $testFont = New-Object System.Drawing.Font("Cascadia Code", 10)
    $fontFamily = "Cascadia Code"
} catch {}

$tabFont = New-Object System.Drawing.Font($fontFamily, 11, [System.Drawing.FontStyle]::Bold)
$titleTextBrush = New-Object System.Drawing.SolidBrush($textColor)
$g.DrawString("⚡ PowerShell — CleanDownloads", $tabFont, $titleTextBrush, ($wX + 26), ($wY + 17))

# Window Control Buttons (Min, Max, Close)
$closeBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 239, 68, 68))
$maxBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 234, 179, 8))
$minBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 34, 197, 94))
$g.FillEllipse($minBrush, ($wX + $wW - 74), ($wY + 16), 13, 13)
$g.FillEllipse($maxBrush, ($wX + $wW - 52), ($wY + 16), 13, 13)
$g.FillEllipse($closeBrush, ($wX + $wW - 30), ($wY + 16), 13, 13)

# Terminal Text Lines
$termFont = New-Object System.Drawing.Font($fontFamily, 13, [System.Drawing.FontStyle]::Regular)
$termBoldFont = New-Object System.Drawing.Font($fontFamily, 13, [System.Drawing.FontStyle]::Bold)

$lines = @(
    @{ Text = "PS C:\Users\User> cleandownloads preview"; Color = $cyanColor; Bold = $true },
    @{ Text = ""; Color = $textColor; Bold = $false },
    @{ Text = "   CLEAN DOWNLOADS v1.0.0"; Color = $cyanColor; Bold = $true },
    @{ Text = "   One command. Zero clutter."; Color = $dimColor; Bold = $false },
    @{ Text = "   ────────────────────────────────────────────────────────────"; Color = $dimColor; Bold = $false },
    @{ Text = ""; Color = $textColor; Bold = $false },
    @{ Text = "PREVIEW — 6 files ready for organization"; Color = $yellowColor; Bold = $true },
    @{ Text = ""; Color = $textColor; Bold = $false },
    @{ Text = "  annual_report_2026.docx  (1.4 MB)"; Color = $textColor; Bold = $true },
    @{ Text = "    Downloads\annual_report_2026.docx"; Color = $dimColor; Bold = $false },
    @{ Text = "    → Downloads\Documents\Word\annual_report_2026.docx"; Color = $greenColor; Bold = $false },
    @{ Text = ""; Color = $textColor; Bold = $false },
    @{ Text = "  invoice_october.pdf  (324.5 KB)"; Color = $textColor; Bold = $true },
    @{ Text = "    Downloads\invoice_october.pdf"; Color = $dimColor; Bold = $false },
    @{ Text = "    → Downloads\Documents\PDF\invoice_october.pdf"; Color = $greenColor; Bold = $false },
    @{ Text = ""; Color = $textColor; Bold = $false },
    @{ Text = "  screenshot_01.png  (2.1 MB)"; Color = $textColor; Bold = $true },
    @{ Text = "    Downloads\screenshot_01.png"; Color = $dimColor; Bold = $false },
    @{ Text = "    → Downloads\Images\PNG\screenshot_01.png"; Color = $greenColor; Bold = $false },
    @{ Text = ""; Color = $textColor; Bold = $false },
    @{ Text = "  backup_dataset.zip  (42.8 MB)"; Color = $textColor; Bold = $true },
    @{ Text = "    Downloads\backup_dataset.zip"; Color = $dimColor; Bold = $false },
    @{ Text = "    → Downloads\Archives\ZIP\backup_dataset.zip"; Color = $greenColor; Bold = $false },
    @{ Text = ""; Color = $textColor; Bold = $false },
    @{ Text = "  vscode_setup.exe  (92.4 MB)"; Color = $textColor; Bold = $true },
    @{ Text = "    Downloads\vscode_setup.exe"; Color = $dimColor; Bold = $false },
    @{ Text = "    → Downloads\Software\EXE\vscode_setup.exe"; Color = $greenColor; Bold = $false },
    @{ Text = ""; Color = $textColor; Bold = $false },
    @{ Text = "FILE BREAKDOWN"; Color = $cyanColor; Bold = $true },
    @{ Text = "────────────────────────────────────────────────────────────"; Color = $dimColor; Bold = $false },
    @{ Text = "  Documents: 2 files  |  Images: 1 file  |  Archives: 1 file"; Color = $textColor; Bold = $false },
    @{ Text = "  Software:  1 file   |  Code:   1 file  |  Total: 6 files (140.2 MB)"; Color = $textColor; Bold = $false },
    @{ Text = "────────────────────────────────────────────────────────────"; Color = $dimColor; Bold = $false },
    @{ Text = "✔ Dry run complete. 6 files ready. Zero files moved."; Color = $greenColor; Bold = $true },
    @{ Text = ""; Color = $textColor; Bold = $false },
    @{ Text = "PS C:\Users\User> cleandownloads organize --dry-run"; Color = $cyanColor; Bold = $true }
)

$curY = $wY + 62
$curX = $wX + 30
$lineHeight = 23

foreach ($l in $lines) {
    $f = if ($l.Bold) { $termBoldFont } else { $termFont }
    $brush = New-Object System.Drawing.SolidBrush($l.Color)
    $g.DrawString($l.Text, $f, $brush, $curX, $curY)
    $curY += $lineHeight
}

# Save Screenshot PNG
$bmp.Save($screenshotPath, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
Write-Host "[+] Generated screenshot-main.png at: $screenshotPath"
