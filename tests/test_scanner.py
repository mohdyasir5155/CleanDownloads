"""Tests for the Downloads scanner and safety filtering."""

from pathlib import Path

import pytest

from cleandownloads.config import DEFAULT_RULES, AppConfig, RuleConfig
from cleandownloads.scanner import Scanner


@pytest.fixture
def mock_downloads(tmp_path: Path) -> Path:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    # Root eligible files
    (downloads / "invoice.pdf").write_text("dummy pdf")
    (downloads / "photo.png").write_text("dummy png")
    (downloads / "setup.exe").write_text("dummy exe")

    # Incomplete downloads
    (downloads / "movie.mp4.crdownload").write_text("partial")
    (downloads / "huge.zip.part").write_text("partial")

    # System files
    (downloads / "desktop.ini").write_text("[ShellClassInfo]")
    (downloads / "Thumbs.db").write_text("cache")

    # Organized folder with existing organized files
    docs_pdf = downloads / "Documents" / "PDF"
    docs_pdf.mkdir(parents=True)
    (docs_pdf / "prior_invoice.pdf").write_text("already organized")

    return downloads


def test_scanner_root_only_default(mock_downloads: Path):
    rules = [RuleConfig(**r) for r in DEFAULT_RULES]
    config = AppConfig(rules=rules, downloads_dir=str(mock_downloads), recursive=False)
    scanner = Scanner(config)

    res = scanner.scan(mock_downloads)

    assert res.downloads_dir == mock_downloads.resolve()
    # Ready files should only be the 3 eligible root files
    ready_names = {f.filename for f in res.ready_files}
    assert ready_names == {"invoice.pdf", "photo.png", "setup.exe"}
    assert res.total_ready == 3

    # Already organized count should reflect prior_invoice.pdf
    assert res.already_organized_count >= 1

    # Incomplete files and system files skipped
    skipped_reasons = {sf.path.name: sf.reason for sf in res.skipped_files}
    assert skipped_reasons.get("movie.mp4.crdownload") == "incomplete_download"
    assert skipped_reasons.get("huge.zip.part") == "incomplete_download"
    assert skipped_reasons.get("desktop.ini") == "hidden_system"
    assert skipped_reasons.get("Thumbs.db") == "hidden_system"


def test_scanner_size_filter(tmp_path: Path):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    small_file = downloads / "tiny.pdf"
    small_file.write_bytes(b"123")  # 3 bytes

    big_file = downloads / "normal.pdf"
    big_file.write_bytes(b"1234567890" * 100)  # 1000 bytes

    rules = [RuleConfig(**r) for r in DEFAULT_RULES]
    config = AppConfig(
        rules=rules,
        downloads_dir=str(downloads),
        min_file_size_bytes=100,  # Min 100 bytes
    )
    scanner = Scanner(config)
    res = scanner.scan(downloads)

    ready_names = {f.filename for f in res.ready_files}
    assert "normal.pdf" in ready_names
    assert "tiny.pdf" not in ready_names

    skipped = [sf for sf in res.skipped_files if sf.path.name == "tiny.pdf"]
    assert len(skipped) == 1
    assert skipped[0].reason == "size_limit"


def test_scanner_recursive_mode(tmp_path: Path):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    (downloads / "root.pdf").write_text("root file")

    subfolder = downloads / "NestedUnorganizedFolder"
    subfolder.mkdir()
    (subfolder / "nested.png").write_text("nested image")

    # Excluded folder should not be traversed
    excluded = downloads / "Documents"
    excluded.mkdir()
    (excluded / "existing.pdf").write_text("existing")

    rules = [RuleConfig(**r) for r in DEFAULT_RULES]
    config = AppConfig(
        rules=rules,
        downloads_dir=str(downloads),
        recursive=True,
    )
    scanner = Scanner(config)
    res = scanner.scan(downloads)

    ready_names = {f.filename for f in res.ready_files}
    assert "root.pdf" in ready_names
    assert "nested.png" in ready_names
    assert "existing.pdf" not in ready_names
