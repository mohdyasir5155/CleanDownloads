"""Tests for safety invariants and security validation."""

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

