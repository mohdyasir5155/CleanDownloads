# PowerShell script to generate animated terminal demo GIF using System.Drawing
Add-Type -AssemblyName System.Drawing

$width = 820
$height = 460
$destPath = Join-Path (Split-Path -Parent $PSScriptRoot) "assets\demo.gif"

# Palette & Fonts
$bgColor = [System.Drawing.Color]::FromArgb(15, 23, 42)
$headerColor = [System.Drawing.Color]::FromArgb(30, 41, 59)
$borderColor = [System.Drawing.Color]::FromArgb(51, 65, 85)
$cyan = [System.Drawing.Color]::FromArgb(56, 189, 248)
$green = [System.Drawing.Color]::FromArgb(74, 222, 128)
$yellow = [System.Drawing.Color]::FromArgb(250, 204, 21)
$purple = [System.Drawing.Color]::FromArgb(192, 132, 252)
$dim = [System.Drawing.Color]::FromArgb(148, 163, 184)
$white = [System.Drawing.Color]::FromArgb(241, 245, 249)

$font = New-Object System.Drawing.Font("Consolas", 11, [System.Drawing.FontStyle]::Regular)
$fontBold = New-Object System.Drawing.Font("Consolas", 11, [System.Drawing.FontStyle]::Bold)
$fontTitle = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Regular)

function Create-Frame($lines) {
    $bmp = New-Object System.Drawing.Bitmap($width, $height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality

    # Background
    $g.FillRectangle((New-Object System.Drawing.SolidBrush($bgColor)), 0, 0, $width, $height)

    # Header bar
    $g.FillRectangle((New-Object System.Drawing.SolidBrush($headerColor)), 0, 0, $width, 36)
    $g.DrawLine((New-Object System.Drawing.Pen($borderColor)), 0, 36, $width, 36)

    # Window dots
    $g.FillEllipse((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(244, 63, 94))), 14, 12, 12, 12)
    $g.FillEllipse((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(251, 191, 36))), 32, 12, 12, 12)
    $g.FillEllipse((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(34, 197, 94))), 50, 12, 12, 12)

    # Title
    $g.DrawString("PowerShell - CleanDownloads v1.0.0", $fontTitle, (New-Object System.Drawing.SolidBrush($dim)), 74, 9)

    $y = 52
    foreach ($line in $lines) {
        $prefix = $line.Prefix
        $text = $line.Text
        $color = $line.Color
        $f = if ($line.Bold) { $fontBold } else { $font }

        $x = 24
        if ($prefix) {
            $g.DrawString($prefix, $fontBold, (New-Object System.Drawing.SolidBrush($cyan)), $x, $y)
            $size = $g.MeasureString($prefix, $fontBold)
            $x += $size.Width - 4
        }
        $g.DrawString($text, $f, (New-Object System.Drawing.SolidBrush($color)), $x, $y)
        $y += 24
    }

    $g.Dispose()
    return $bmp
}

# Define frames
$f1Lines = @(
    @{ Prefix = "PS C:\Users\User> "; Text = "cleandownloads scan"; Color = $white; Bold = $true }
)

$f2Lines = @(
    @{ Prefix = "PS C:\Users\User> "; Text = "cleandownloads scan"; Color = $white; Bold = $true },
    @{ Prefix = ""; Text = "   CLEAN DOWNLOADS v1.0.0"; Color = $cyan; Bold = $true },
    @{ Prefix = ""; Text = "   One command. Zero clutter."; Color = $dim; Bold = $false },
    @{ Prefix = ""; Text = "   --------------------------------------------------------"; Color = $borderColor; Bold = $false },
    @{ Prefix = ""; Text = "   Target Folder:    C:\Users\User\Downloads"; Color = $white; Bold = $false },
    @{ Prefix = ""; Text = "   Total Scanned:    248 items"; Color = $white; Bold = $false },
    @{ Prefix = ""; Text = "   Files to Sort:    146 files (102 already categorized)"; Color = $yellow; Bold = $true },
    @{ Prefix = ""; Text = "   Safety Guarantee: 14 strict invariants active (zero data loss)"; Color = $green; Bold = $false }
)

$f3Lines = @(
    @{ Prefix = "PS C:\Users\User> "; Text = "cleandownloads organize --dry-run"; Color = $white; Bold = $true }
)

$f4Lines = @(
    @{ Prefix = "PS C:\Users\User> "; Text = "cleandownloads organize --dry-run"; Color = $white; Bold = $true },
    @{ Prefix = ""; Text = "   DRY RUN PREVIEW (Simulating movements, 0 files modified)"; Color = $yellow; Bold = $true },
    @{ Prefix = ""; Text = "   --------------------------------------------------------"; Color = $borderColor; Bold = $false },
    @{ Prefix = ""; Text = "   [Documents/PDF]  quarterly_report.pdf -> Documents/PDF/quarterly_report.pdf"; Color = $white; Bold = $false },
    @{ Prefix = ""; Text = "   [Images/PNG]     diagram_design.png   -> Images/PNG/diagram_design.png"; Color = $white; Bold = $false },
    @{ Prefix = ""; Text = "   [Software/EXE]   vscode_setup.exe     -> Software/EXE/vscode_setup.exe"; Color = $white; Bold = $false },
    @{ Prefix = ""; Text = "   [Archives/ZIP]   dataset_2026.zip     -> Archives/ZIP/dataset_2026.zip"; Color = $white; Bold = $false },
    @{ Prefix = ""; Text = "   [Code/Python]    process_data.py      -> Code/Python/process_data.py"; Color = $white; Bold = $false },
    @{ Prefix = ""; Text = "   ... and 141 more planned safe moves"; Color = $dim; Bold = $false },
    @{ Prefix = ""; Text = "   Collision check: Zero overwrites. All suffixes calculated."; Color = $green; Bold = $false }
)

$f5Lines = @(
    @{ Prefix = "PS C:\Users\User> "; Text = "cleandownloads organize"; Color = $white; Bold = $true },
    @{ Prefix = ""; Text = "   Organizing Downloads folder..."; Color = $cyan; Bold = $false },
    @{ Prefix = ""; Text = "   Moving 146 files into clean category folders..."; Color = $dim; Bold = $false },
    @{ Prefix = ""; Text = "   --------------------------------------------------------"; Color = $borderColor; Bold = $false },
    @{ Prefix = ""; Text = "   [PASS] 146 files successfully organized in 0.12s!"; Color = $green; Bold = $true },
    @{ Prefix = ""; Text = "   Batch #20261101-01 recorded in history.db"; Color = $dim; Bold = $false },
    @{ Prefix = ""; Text = "   Need to reverse this run? Run: cleandownloads undo"; Color = $purple; Bold = $true },
    @{ Prefix = ""; Text = "   --------------------------------------------------------"; Color = $borderColor; Bold = $false },
    @{ Prefix = "PS C:\Users\User> "; Text = ""; Color = $white; Bold = $true }
)

$frames = @(
    @{ Bmp = (Create-Frame $f1Lines); Delay = 150 },
    @{ Bmp = (Create-Frame $f2Lines); Delay = 300 },
    @{ Bmp = (Create-Frame $f3Lines); Delay = 150 },
    @{ Bmp = (Create-Frame $f4Lines); Delay = 350 },
    @{ Bmp = (Create-Frame $f5Lines); Delay = 450 }
)

# Encode GIF with Netscape loop extension
$gifBytes = [System.Collections.Generic.List[byte]]::new()

# C# helper for byte assembly
$csharp = @"
using System;
using System.IO;
using System.Drawing;
using System.Drawing.Imaging;

public static class GifHelper {
    public static void SaveAnimatedGif(string filePath, Bitmap[] frames, int[] delays) {
        using (FileStream fs = new FileStream(filePath, FileMode.Create, FileAccess.Write))
        using (BinaryWriter bw = new BinaryWriter(fs)) {
            for (int i = 0; i < frames.Length; i++) {
                using (MemoryStream ms = new MemoryStream()) {
                    frames[i].Save(ms, ImageFormat.Gif);
                    byte[] bytes = ms.ToArray();
                    
                    if (i == 0) {
                        // Header and Logical Screen Descriptor (first 13 bytes)
                        bw.Write(bytes, 0, 13);
                        // Global Color Table
                        int gctSize = 3 * (1 << ((bytes[10] & 0x07) + 1));
                        bw.Write(bytes, 13, gctSize);
                        
                        // Netscape 2.0 Loop Block
                        bw.Write((byte)0x21); // Extension
                        bw.Write((byte)0xFF); // Application
                        bw.Write((byte)0x0B); // Block Size 11
                        bw.Write(System.Text.Encoding.ASCII.GetBytes("NETSCAPE2.0"));
                        bw.Write((byte)0x03); // Sub-block length
                        bw.Write((byte)0x01);
                        bw.Write((short)0);   // Loop count 0 = infinite
                        bw.Write((byte)0x00); // Block terminator
                    }
                    
                    // Graphic Control Extension (Delay)
                    bw.Write((byte)0x21); // Extension
                    bw.Write((byte)0xF9); // Graphic Control
                    bw.Write((byte)0x04); // Byte size
                    bw.Write((byte)0x04); // Disposal method (restore to background)
                    bw.Write((short)delays[i]); // Delay time in 1/100s
                    bw.Write((byte)0x00); // Transparent color index
                    bw.Write((byte)0x00); // Block terminator
                    
                    // Image Descriptor and Data (start at 0x2C)
                    int imgIdx = 13 + 3 * (1 << ((bytes[10] & 0x07) + 1));
                    while (imgIdx < bytes.Length && bytes[imgIdx] != 0x2C) {
                        imgIdx++;
                    }
                    if (imgIdx < bytes.Length) {
                        // Write until end, skipping trailer 0x3B
                        int count = bytes.Length - imgIdx - 1;
                        bw.Write(bytes, imgIdx, count);
                    }
                }
            }
            bw.Write((byte)0x3B); // GIF Trailer
        }
    }
}
"@

Add-Type -TypeDefinition $csharp -ReferencedAssemblies "System.Drawing.dll"

$bmps = $frames | ForEach-Object { $_.Bmp }
$delays = $frames | ForEach-Object { [int]$_.Delay }

[GifHelper]::SaveAnimatedGif($destPath, $bmps, $delays)

Write-Host "Created animated demo GIF: $destPath ($((Get-Item $destPath).Length) bytes)" -ForegroundColor Green

# Cleanup
foreach ($f in $frames) { $f.Bmp.Dispose() }
$font.Dispose()
$fontBold.Dispose()
$fontTitle.Dispose()
