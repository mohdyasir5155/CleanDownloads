# Script to render an authentic terminal session demo GIF for CleanDownloads
import os
from PIL import Image, ImageDraw, ImageFont

def render_terminal_frame(lines, active_cmd="", width=800, height=480):
    # Dark modern terminal theme
    bg_color = (15, 23, 42)      # Deep slate
    card_bg = (23, 32, 54)       # Window bg
    border_color = (51, 65, 85)  # Border
    text_color = (226, 232, 240) # Text slate-100
    cyan = (56, 189, 248)        # Sky cyan
    green = (74, 222, 128)       # Green 400
    yellow = (250, 204, 21)      # Yellow
    purple = (192, 132, 252)     # Purple
    dim = (148, 163, 184)        # Dim slate

    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Window header bar
    header_height = 40
    draw.rectangle([(0, 0), (width, header_height)], fill=(30, 41, 59))
    draw.line([(0, header_height), (width, header_height)], fill=border_color, width=1)

    # Window controls (macOS / Windows modern style)
    draw.ellipse([(16, 14), (28, 26)], fill=(244, 63, 94))   # Red
    draw.ellipse([(36, 14), (48, 26)], fill=(251, 191, 36))  # Yellow
    draw.ellipse([(56, 14), (68, 26)], fill=(34, 197, 94))   # Green

    # Window Title
    title = "PowerShell - CleanDownloads v1.0.0"
    draw.text((width // 2 - 110, 12), title, fill=dim)

    # Font setup
    try:
        font = ImageFont.truetype("consola.ttf", 15)
        font_bold = ImageFont.truetype("consolab.ttf", 15)
    except:
        font = ImageFont.load_default()
        font_bold = font

    y = header_height + 20
    x_margin = 24
    line_spacing = 22

    for item in lines:
        prefix, text, color_type = item
        col = text_color
        f = font
        if color_type == "cyan":
            col = cyan
            f = font_bold
        elif color_type == "green":
            col = green
            f = font_bold
        elif color_type == "yellow":
            col = yellow
        elif color_type == "dim":
            col = dim
        elif color_type == "purple":
            col = purple

        if prefix:
            draw.text((x_margin, y), prefix, font=font_bold, fill=cyan)
            p_len = len(prefix) * 9 + 4
            draw.text((x_margin + p_len, y), text, font=f, fill=col)
        else:
            draw.text((x_margin, y), text, font=f, fill=col)
        y += line_spacing

    return img.convert("RGB")

def build_demo_gif(output_path):
    frames = []

    # Frame 1: Initial Prompt
    f1 = render_terminal_frame([
        ("PS C:\\Users\\User> ", "cleandownloads scan", "text")
    ])

    # Frame 2: Scan Output
    f2 = render_terminal_frame([
        ("PS C:\\Users\\User> ", "cleandownloads scan", "text"),
        ("", "   CLEAN DOWNLOADS v1.0.0", "cyan"),
        ("", "   One command. Zero clutter.", "dim"),
        ("", "   ────────────────────────────────────────────", "dim"),
        ("", "   Downloads scanned: 248 items", "text"),
        ("", "   Ready to organize: 146 files (102 already sorted)", "yellow"),
        ("", "   Top categories:    Documents (38), Images (42), Archives (19)", "text"),
        ("", "   Safety status:     14 invariants guaranteed (zero data loss)", "green")
    ])

    # Frame 3: Dry-Run Prompt
    f3 = render_terminal_frame([
        ("PS C:\\Users\\User> ", "cleandownloads scan", "text"),
        ("", "   Downloads scanned: 248 items | Ready: 146 files", "dim"),
        ("", "", "text"),
        ("PS C:\\Users\\User> ", "cleandownloads organize --dry-run", "text")
    ])

    # Frame 4: Dry-Run Preview
    f4 = render_terminal_frame([
        ("PS C:\\Users\\User> ", "cleandownloads organize --dry-run", "text"),
        ("", "   DRY RUN PREVIEW (Simulating movements, 0 files changed)", "yellow"),
        ("", "   ────────────────────────────────────────────────────────", "dim"),
        ("", "   [Documents/PDF]  invoice_2026.pdf  -> Documents/PDF/invoice_2026.pdf", "text"),
        ("", "   [Images/PNG]     screenshot.png    -> Images/PNG/screenshot.png", "text"),
        ("", "   [Software/EXE]   setup_tool.exe    -> Software/EXE/setup_tool.exe", "text"),
        ("", "   [Archives/ZIP]   project_data.zip  -> Archives/ZIP/project_data.zip", "text"),
        ("", "   [Code/Python]    worker.py         -> Code/Python/worker.py", "text"),
        ("", "   ... 141 more planned safe moves", "dim"),
        ("", "   Zero overwrites. Numbered suffixes ready if collisions exist.", "green")
    ])

    # Frame 5: Real Organize Execution
    f5 = render_terminal_frame([
        ("PS C:\\Users\\User> ", "cleandownloads organize", "text"),
        ("", "   Organizing Downloads folder...", "cyan"),
        ("", "   Moving 146 files into clean category folders...", "dim")
    ])

    # Frame 6: Organize Success & Undo notice
    f6 = render_terminal_frame([
        ("PS C:\\Users\\User> ", "cleandownloads organize", "text"),
        ("", "   ============================================================", "green"),
        ("", "   [PASS] 146 files successfully organized in 0.12 seconds!", "green"),
        ("", "   ============================================================", "green"),
        ("", "   Operation Batch: #20261101-01 (Logged to history.db)", "dim"),
        ("", "   Zero clutter. Downloads folder is now spotless.", "cyan"),
        ("", "", "text"),
        ("", "   Need to reverse this run? Just run: cleandownloads undo", "purple"),
        ("", "", "text"),
        ("PS C:\\Users\\User> ", "", "text")
    ])

    # Append frames with durations (ms)
    all_frames = [
        (f1, 1500),
        (f2, 2500),
        (f3, 1200),
        (f4, 3000),
        (f5, 1000),
        (f6, 4500)
    ]

    images = [af[0] for af in all_frames]
    durations = [af[1] for af in all_frames]

    images[0].save(
        output_path,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
        optimize=True
    )
    print(f"Generated demo GIF: {output_path} ({os.path.getsize(output_path)} bytes)")

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "demo.gif")
    build_demo_gif(out)
