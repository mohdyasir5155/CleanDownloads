"""Generate an authentic animated demo GIF of CleanDownloads CLI in action."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

repo_root = Path(__file__).parent.parent
assets_dir = repo_root / "assets"
assets_dir.mkdir(parents=True, exist_ok=True)
gif_path = assets_dir / "demo.gif"

WIDTH = 1100
HEIGHT = 700

# Color palette (Modern GitHub Dark / Windows Terminal)
BG_COLOR = (13, 17, 23)
TITLE_BG = (22, 27, 34)
TAB_BG = (30, 37, 48)
BORDER_COLOR = (48, 54, 61)
TEXT_COLOR = (230, 237, 243)
CYAN = (56, 189, 248)
GREEN = (63, 185, 80)
YELLOW = (210, 153, 34)
DIM = (139, 148, 158)
BLUE = (88, 166, 255)
RED = (248, 81, 73)

# Fonts
try:
    font = ImageFont.truetype("consola.ttf", 16)
    font_bold = ImageFont.truetype("consolab.ttf", 16)
    tab_font = ImageFont.truetype("consolab.ttf", 13)
except Exception:
    font = ImageFont.load_default()
    font_bold = font
    tab_font = font

def create_window_base():
    img = Image.new("RGB", (WIDTH, HEIGHT), (8, 11, 16))
    draw = ImageDraw.Draw(img)

    wx, wy, ww, wh = 25, 25, WIDTH - 50, HEIGHT - 50

    # Window background & border
    draw.rectangle([wx, wy, wx + ww, wy + wh], fill=BG_COLOR, outline=BORDER_COLOR, width=2)
    # Titlebar
    draw.rectangle([wx, wy, wx + ww, wy + 38], fill=TITLE_BG)
    # Tab
    draw.rectangle([wx + 12, wy + 6, wx + 230, wy + 38], fill=TAB_BG)
    draw.text((wx + 22, wy + 12), "PowerShell - CleanDownloads", font=tab_font, fill=TEXT_COLOR)

    # Window buttons
    draw.ellipse([wx + ww - 65, wy + 13, wx + ww - 53, wy + 25], fill=(35, 134, 54))
    draw.ellipse([wx + ww - 45, wy + 13, wx + ww - 33, wy + 25], fill=(210, 153, 34))
    draw.ellipse([wx + ww - 25, wy + 13, wx + ww - 13, wy + 25], fill=(248, 81, 73))

    return img, draw, wx + 20, wy + 52

# Scenario progression lines for each keyframe
scenes = [
    # Frame 0: Idle prompt
    [
        ("PS C:\\Users\\User\\Downloads> ", CYAN, True),
    ],
    # Frame 1: Typing scan
    [
        ("PS C:\\Users\\User\\Downloads> cleandownloads scan", CYAN, True),
    ],
    # Frame 2: Scan Output
    [
        ("PS C:\\Users\\User\\Downloads> cleandownloads scan", CYAN, True),
        ("", TEXT_COLOR, False),
        ("   CLEAN DOWNLOADS v1.0.0", CYAN, True),
        ("   One command. Zero clutter.", DIM, False),
        ("   ───────────────────────────────────────────", DIM, False),
        ("Target Directory:  C:\\Users\\User\\Downloads", TEXT_COLOR, False),
        ("Files Ready:       6 files (140.2 MB)", GREEN, True),
        ("Already Organized: 73 files", DIM, False),
        ("", TEXT_COLOR, False),
        ("Breakdown by Category:", BLUE, True),
        ("  • Documents          2 files", TEXT_COLOR, False),
        ("  • Images             1 files", TEXT_COLOR, False),
        ("  • Archives           1 files", TEXT_COLOR, False),
        ("  • Software           1 files", TEXT_COLOR, False),
        ("  • Code               1 files", TEXT_COLOR, False),
    ],
    # Frame 3: Typing preview
    [
        ("PS C:\\Users\\User\\Downloads> cleandownloads scan", CYAN, True),
        ("   ... [Scan complete: 6 files ready] ...", DIM, False),
        ("", TEXT_COLOR, False),
        ("PS C:\\Users\\User\\Downloads> cleandownloads preview", CYAN, True),
    ],
    # Frame 4: Preview Output
    [
        ("PS C:\\Users\\User\\Downloads> cleandownloads preview", CYAN, True),
        ("", TEXT_COLOR, False),
        ("PREVIEW — 6 files ready", YELLOW, True),
        ("  annual_report.docx  (1.4 MB)  → Documents/Word/annual_report.docx", TEXT_COLOR, False),
        ("  invoice_october.pdf (320 KB)  → Documents/PDF/invoice_october.pdf", TEXT_COLOR, False),
        ("  screenshot.png      (2.1 MB)  → Images/PNG/screenshot.png", TEXT_COLOR, False),
        ("  backup_dataset.zip  (42.8 MB) → Archives/ZIP/backup_dataset.zip", TEXT_COLOR, False),
        ("  vscode_setup.exe    (92.4 MB) → Software/EXE/vscode_setup.exe", TEXT_COLOR, False),
        ("  automation.py       (14.2 KB) → Code/Python/automation.py", TEXT_COLOR, False),
        ("", TEXT_COLOR, False),
        ("No files moved yet. Run 'cleandownloads organize' to apply.", DIM, False),
    ],
    # Frame 5: Typing organize
    [
        ("PS C:\\Users\\User\\Downloads> cleandownloads organize", CYAN, True),
    ],
    # Frame 6: Organize Execution
    [
        ("PS C:\\Users\\User\\Downloads> cleandownloads organize", CYAN, True),
        ("", TEXT_COLOR, False),
        ("   CLEAN DOWNLOADS v1.0.0", CYAN, True),
        ("   One command. Zero clutter.", DIM, False),
        ("   ───────────────────────────────────────────", DIM, False),
        ("  ✔ Moved: annual_report.docx  → Documents/Word/annual_report.docx", GREEN, False),
        ("  ✔ Moved: invoice_october.pdf → Documents/PDF/invoice_october.pdf", GREEN, False),
        ("  ✔ Moved: screenshot.png      → Images/PNG/screenshot.png", GREEN, False),
        ("  ✔ Moved: backup_dataset.zip  → Archives/ZIP/backup_dataset.zip", GREEN, False),
        ("  ✔ Moved: vscode_setup.exe    → Software/EXE/vscode_setup.exe", GREEN, False),
        ("  ✔ Moved: automation.py       → Code/Python/automation.py", GREEN, False),
        ("", TEXT_COLOR, False),
        ("✔ Organization complete! Successfully organized 6 files in 0.12s.", GREEN, True),
        ("  Operation recorded in history.db (Batch ID: b7e3...)", DIM, False),
    ],
    # Frame 7: Undo Demo
    [
        ("PS C:\\Users\\User\\Downloads> cleandownloads organize", CYAN, True),
        ("  ✔ Organization complete! 6 files moved.", GREEN, False),
        ("", TEXT_COLOR, False),
        ("PS C:\\Users\\User\\Downloads> cleandownloads undo", CYAN, True),
        ("", TEXT_COLOR, False),
        ("✔ Undo finished: Restored 6 files to original root locations.", GREEN, True),
        ("  ↩ Restored: annual_report.docx", DIM, False),
        ("  ↩ Restored: invoice_october.pdf", DIM, False),
        ("  ↩ Restored: screenshot.png", DIM, False),
        ("  ↩ Restored: backup_dataset.zip", DIM, False),
        ("  ↩ Restored: vscode_setup.exe", DIM, False),
        ("  ↩ Restored: automation.py", DIM, False),
        ("", TEXT_COLOR, False),
        ("PS C:\\Users\\User\\Downloads> ", CYAN, True),
    ],
]

durations = [1200, 1000, 2500, 1000, 2800, 1000, 3000, 3500]
frames = []

for scene in scenes:
    img, draw, start_x, start_y = create_window_base()
    cur_y = start_y
    for text, color, is_bold in scene:
        f = font_bold if is_bold else font
        draw.text((start_x, cur_y), text, font=f, fill=color)
        cur_y += 24
    frames.append(img)

# Save animated GIF
frames[0].save(
    gif_path,
    save_all=True,
    append_images=frames[1:],
    duration=durations,
    loop=0,
    optimize=True,
)

print(f"[+] Successfully generated demo.gif at: {gif_path}")
