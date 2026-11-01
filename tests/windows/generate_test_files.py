"""Generate a comprehensive disposable test dataset for CleanDownloads QA.

Populates the target Downloads folder with standard, edge case, and unicode files
matching Section 2 of the QA Specification.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def generate_sample_files(target_dir: Path) -> dict[str, str]:
    """Create all test files in target_dir and return a dict of {filename: sha256_hash}."""
    target_dir.mkdir(parents=True, exist_ok=True)

    files_to_create = {
        # Documents
        "sample.pdf": "PDF Sample Document Header %PDF-1.4 Content for CleanDownloads QA",
        "sample.docx": "Word Document Mock Content for CleanDownloads QA",
        "sample.txt": "Plain text note content with utf-8 encoding",
        "sample.csv": "id,name,role\n1,Alice,Security\n2,Bob,QA",
        "sample.xlsx": "Excel Spreadsheet Mock Content",
        "sample.pptx": "PowerPoint Presentation Mock Content",

        # Images
        "photo.jpg": "\xFF\xD8\xFF\xE0\x00\x10JFIF JPEG Mock binary image data",
        "image.png": "\x89PNG\r\n\x1a\n PNG Mock binary image data",
        "icon.svg": "<svg xmlns='http://www.w3.org/2000/svg'><circle r='10'/></svg>",
        "picture.webp": "RIFF....WEBPVP8 Mock webp data",

        # Videos
        "video.mp4": "ftypisom MP4 Mock video header data",
        "movie.mkv": "\x1A\x45\xDF\xA3 MKV Mock video binary data",

        # Audio
        "music.mp3": "ID3 MP3 Mock audio data with header",
        "sound.wav": "RIFF....WAVEfmt Mock audio wav data",

        # Archives
        "archive.zip": "PK\x03\x04 Zip Mock archive data",
        "backup.tar": "Mock tar archive binary content block",
        "package.7z": "7z\xBC\xAF\x27\x1C 7-Zip Mock archive header",

        # Software (DO NOT EXECUTE, purely passive test data)
        "installer.exe": "MZ\x90\x00 Passive Windows Executable Mock Header for Classification Test Only",
        "setup.msi": "\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1 MSI Installer Mock Header for Classification Test Only",

        # Development / Code
        "app.py": "print('CleanDownloads QA Python File')\n",
        "index.html": "<!DOCTYPE html><html><head><title>QA</title></head><body>QA Test</body></html>",
        "style.css": "body { margin: 0; padding: 0; font-family: sans-serif; }",
        "script.js": "console.log('CleanDownloads QA Script');",
        "main.ts": "const message: string = 'CleanDownloads QA TS';",
        "program.cpp": "#include <iostream>\nint main() { return 0; }\n",
        "App.java": "public class App { public static void main(String[] args) {} }\n",

        # Edge cases
        "unknown.xyz": "Arbitrary custom extension content that must route to Other",
        "file with spaces.pdf": "Content of file containing space characters in name",
        "नमूना.pdf": "Unicode Hindi filename test content - QA testing",
        "filename with parentheses (1).pdf": "Parentheses in filename test content",
        "duplicate.pdf": "Duplicate initial file content",
        "zero_byte.txt": "",  # zero-byte file
        "hidden_file.pdf": "Content of a file that will have the hidden attribute set",
        "readonly_doc.docx": "Content of a file that will have the read-only attribute set",
        "very_long_filename_sample_with_a_lot_of_characters_for_windows_boundary_validation_test_case_123456789.pdf": "Long filename content",
        "IMAGE.PNG": "PNG with UPPERCASE extension should route to Images/PNG",
    }

    created_paths: dict[str, Path] = {}
    for filename, content in files_to_create.items():
        file_path = target_dir / filename
        if isinstance(content, str):
            file_path.write_text(content, encoding="utf-8")
        else:
            file_path.write_bytes(content)
        created_paths[filename] = file_path

    # Apply Windows attributes for hidden and read-only test files
    if sys.platform == "win32":
        try:
            hidden_path = str(created_paths["hidden_file.pdf"])
            subprocess.run(["attrib", "+h", hidden_path], check=False, shell=False)

            readonly_path = str(created_paths["readonly_doc.docx"])
            subprocess.run(["attrib", "+r", readonly_path], check=False, shell=False)
        except Exception as e:
            print(f"Notice: Could not set Windows attributes: {e}", file=sys.stderr)

    return {name: str(path) for name, path in created_paths.items()}


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/CleanDownloads-QA/TestDownloads")
    created = generate_sample_files(target)
    print(f"Generated {len(created)} test files in: {target}")
