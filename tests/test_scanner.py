"""Tests for the Downloads scanner and safety filtering."""

import json
import os
import time
from pathlib import Path

import pytest

from cleandownloads.cli import main
from cleandownloads.config import DEFAULT_RULES, AppConfig, RuleConfig
from cleandownloads.preview import format_preview
from cleandownloads.scanner import Scanner


@pytest.fixture
def mock_downloads(tmp_path: Path) -> Path:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    # Root eligible files (aged so they are older than default min_file_age_seconds)
    past = time.time() - 1000
    for name in ["invoice.pdf", "photo.png", "setup.exe"]:
        p = downloads / name
        p.write_text(f"dummy {name}")
        os.utime(p, (past, past))

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
        min_file_age_seconds=0,
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
        min_file_age_seconds=0,
    )
    scanner = Scanner(config)
    res = scanner.scan(downloads)

    ready_names = {f.filename for f in res.ready_files}
    assert "root.pdf" in ready_names
    assert "nested.png" in ready_names
    assert "existing.pdf" not in ready_names


def test_scanner_min_file_age_filter(tmp_path: Path):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    old_file = downloads / "old.pdf"
    old_file.write_text("old pdf")
    past = time.time() - 600  # 10 minutes ago (> 300s)
    os.utime(old_file, (past, past))

    new_file = downloads / "new.pdf"
    new_file.write_text("brand new pdf")  # mtime is now (< 300s)

    rules = [RuleConfig(**r) for r in DEFAULT_RULES]
    config = AppConfig(
        rules=rules,
        downloads_dir=str(downloads),
        min_file_age_seconds=300,
    )
    scanner = Scanner(config)
    res = scanner.scan(downloads)

    ready_names = {f.filename for f in res.ready_files}
    assert "old.pdf" in ready_names
    assert "new.pdf" not in ready_names

    skipped = {sf.path.name: sf.reason for sf in res.skipped_files}
    assert skipped.get("new.pdf") == "too_new"

    # Test override: with min_file_age_seconds=0, new.pdf is ready
    config.min_file_age_seconds = 0
    res_override = scanner.scan(downloads)
    ready_override_names = {f.filename for f in res_override.ready_files}
    assert "new.pdf" in ready_override_names
    assert "old.pdf" in ready_override_names

    # Test format_preview includes too_new in skipped files summary
    config.min_file_age_seconds = 300
    res_default = scanner.scan(downloads)
    preview_output = format_preview(res_default)
    assert "SKIPPED FILES" in preview_output
    assert "too_new" in preview_output


def test_cli_min_age_override(tmp_path: Path, monkeypatch, capsys):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    new_file = downloads / "recent.pdf"
    new_file.write_text("recent file")

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))

    # 1. Without --min-age (default 300), scan --json shows recent.pdf as skipped too_new
    monkeypatch.setattr("sys.argv", ["cleandownloads", "scan", "-d", str(downloads), "--json"])
    main()
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_ready"] == 0
    assert any(sf["reason"] == "too_new" for sf in data["skipped_files"])

    # 2. With --min-age 0, scan --json shows recent.pdf as ready
    monkeypatch.setattr("sys.argv", ["cleandownloads", "scan", "-d", str(downloads), "--min-age", "0", "--json"])
    main()
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_ready"] == 1
    assert data["ready_files"][0]["filename"] == "recent.pdf"

    # 3. With preview --json and --min-age 0
    monkeypatch.setattr("sys.argv", ["cleandownloads", "preview", "-d", str(downloads), "--min-age", "0", "--json"])
    main()
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_files"] == 1
    assert len(data["planned_moves"]) == 1

    # 4. With organize --min-age 0 --dry-run --json
    monkeypatch.setattr("sys.argv", ["cleandownloads", "organize", "-d", str(downloads), "--min-age", "0", "--dry-run", "--json"])
    main()
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_files"] == 1
    assert data["is_dry_run"] is True
