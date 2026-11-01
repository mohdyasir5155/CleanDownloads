"""Tests for safety invariants and security validation."""

import os
import sys
from pathlib import Path

import pytest

from cleandownloads.safety import (
    SafetyViolationError,
    generate_collision_safe_path,
    is_hidden_or_system_file,
    is_incomplete_download,
    is_path_within_boundary,
    safe_move_file,
    split_extension,
    validate_move_paths,
    validate_safe_filename,
)


def test_path_boundary_check(tmp_path: Path):
    boundary = tmp_path / "Downloads"
    boundary.mkdir()

    inside = boundary / "file.pdf"
    inside_sub = boundary / "Documents" / "PDF" / "file.pdf"
    outside = tmp_path / "System32" / "evil.dll"
    traversal = boundary / ".." / "evil.txt"

    assert is_path_within_boundary(inside, boundary)
    assert is_path_within_boundary(inside_sub, boundary)
    assert not is_path_within_boundary(outside, boundary)
    assert not is_path_within_boundary(traversal, boundary)


def test_validate_move_paths_raises_on_escape(tmp_path: Path):
    boundary = tmp_path / "Downloads"
    boundary.mkdir()

    source = boundary / "invoice.pdf"
    source.write_text("dummy")

    dest_valid = boundary / "Documents" / "PDF" / "invoice.pdf"
    dest_invalid = tmp_path / "Outside" / "invoice.pdf"

    validate_move_paths(source, dest_valid, boundary)

    with pytest.raises(SafetyViolationError):
        validate_move_paths(source, dest_invalid, boundary)


def test_incomplete_download_detection():
    assert is_incomplete_download(Path("download.crdownload"))
    assert is_incomplete_download(Path("huge_movie.part"))
    assert is_incomplete_download(Path("tempfile.tmp"))
    assert is_incomplete_download(Path("asset.download"))
    assert is_incomplete_download(Path("torrent.aria2"))
    assert is_incomplete_download(Path("file.opdownload"))

    assert not is_incomplete_download(Path("final.pdf"))
    assert not is_incomplete_download(Path("image.png"))


def test_hidden_and_system_files():
    assert is_hidden_or_system_file(Path("desktop.ini"))
    assert is_hidden_or_system_file(Path("Thumbs.db"))
    assert is_hidden_or_system_file(Path(".DS_Store"))
    assert is_hidden_or_system_file(Path(".git"))
    assert is_hidden_or_system_file(Path(".hidden_config"))

    assert not is_hidden_or_system_file(Path("presentation.pptx"))


def test_collision_safe_path_generation(tmp_path: Path):
    target = tmp_path / "report.pdf"
    assert generate_collision_safe_path(target) == target

    # Create target
    target.write_text("first")
    candidate1 = generate_collision_safe_path(target)
    assert candidate1.name == "report (1).pdf"

    # Create candidate 1
    candidate1.write_text("second")
    candidate2 = generate_collision_safe_path(target)
    assert candidate2.name == "report (2).pdf"


def test_split_compound_extensions():
    stem, ext = split_extension("archive.tar.gz")
    assert stem == "archive"
    assert ext == ".tar.gz"

    stem2, ext2 = split_extension("image.png")
    assert stem2 == "image"
    assert ext2 == ".png"


def test_safe_move_file_no_overwrite(tmp_path: Path):
    boundary = tmp_path / "Downloads"
    boundary.mkdir()

    source = boundary / "photo.png"
    source.write_text("photo content")

    dest_folder = boundary / "Images" / "PNG"
    dest_folder.mkdir(parents=True)
    existing_dest = dest_folder / "photo.png"
    existing_dest.write_text("existing content")

    final_dest = safe_move_file(source, existing_dest, boundary)

    assert final_dest.name == "photo (1).png"
    assert final_dest.exists()
    assert final_dest.read_text() == "photo content"
    assert existing_dest.exists()
    assert existing_dest.read_text() == "existing content"
    assert not source.exists()


@pytest.mark.parametrize("filename", ["report..final.pdf", "v1.2..3.zip"])
def test_validate_safe_filename_accepts_legitimate_double_dots(filename: str):
    """Verify legitimate filenames with double dots are accepted."""
    validate_safe_filename(filename)


@pytest.mark.parametrize(
    "filename",
    [
        "..",
        "a/b",
        "a\\b",
        "con.txt",
        "notes.txt.",
        "file .pdf ",
        "a:stream",
    ],
)
def test_validate_safe_filename_rejects_unsafe_names(filename: str):
    """Verify unsafe filenames, devices, ADS, and trailing dots/spaces are rejected."""
    with pytest.raises(SafetyViolationError):
        validate_safe_filename(filename)


def test_atomic_collision_safe_move_posix_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test the POSIX link/unlink branch and collision renaming in atomic_collision_safe_move."""
    from cleandownloads.safety import atomic_collision_safe_move

    monkeypatch.setattr(sys, "platform", "linux")

    source = tmp_path / "test.txt"
    source.write_text("posix content", encoding="utf-8")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    target = dest_dir / "test.txt"

    # Test normal link+unlink
    final_dest, file_hash = atomic_collision_safe_move(source, target, boundary=tmp_path)
    assert final_dest == target
    assert not source.exists()
    assert target.read_text(encoding="utf-8") == "posix content"

    # Test collision avoidance under POSIX
    source2 = tmp_path / "test.txt"
    source2.write_text("posix content 2", encoding="utf-8")
    final_dest2, _ = atomic_collision_safe_move(source2, target, boundary=tmp_path)
    assert final_dest2 == dest_dir / "test (1).txt"
    assert final_dest2.read_text(encoding="utf-8") == "posix content 2"
    assert target.read_text(encoding="utf-8") == "posix content"


def test_atomic_collision_safe_move_posix_exdev_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test EXDEV cross-device link fallback to exclusive-create copy."""
    from cleandownloads.safety import atomic_collision_safe_move

    monkeypatch.setattr(sys, "platform", "linux")

    source = tmp_path / "cross.txt"
    source.write_text("cross dev content", encoding="utf-8")
    dest_dir = tmp_path / "dest2"
    dest_dir.mkdir()
    target = dest_dir / "cross.txt"

    def mock_link(src, dst):
        err = OSError("Invalid cross-device link")
        err.errno = 18  # EXDEV
        raise err

    monkeypatch.setattr(os, "link", mock_link)

    final_dest, _ = atomic_collision_safe_move(source, target, boundary=tmp_path)
    assert final_dest == target
    assert not source.exists()
    assert target.read_text(encoding="utf-8") == "cross dev content"


