"""Test fixture generators and sample file helpers for CleanDownloads tests."""

from pathlib import Path


def populate_dummy_downloads(target_dir: Path) -> list[Path]:
    """Populate target directory with a representative assortment of test files."""
    files = {
        "annual_report.pdf": b"%PDF-1.4 dummy",
        "meeting_minutes.docx": b"PK dummy docx",
        "spreadsheet.xlsx": b"PK dummy xlsx",
        "slides.pptx": b"PK dummy pptx",
        "diagram.png": b"\x89PNG dummy",
        "photo.jpg": b"\xff\xd8\xff dummy",
        "video_demo.mp4": b"dummy mp4",
        "podcast.mp3": b"ID3 dummy mp3",
        "archive.zip": b"PK dummy zip",
        "setup_helper.exe": b"MZ dummy exe",
        "script.py": b"# dummy python script\nprint('hello')",
        "webpage.html": b"<!DOCTYPE html><html><body>hello</body></html>",
        "style.css": b"body { margin: 0; }",
        "main.rs": b"fn main() {}",
        "unknown_format.xyz": b"unknown binary data",
    }

    created = []
    for filename, content in files.items():
        p = target_dir / filename
        p.write_bytes(content)
        created.append(p)
    return created
