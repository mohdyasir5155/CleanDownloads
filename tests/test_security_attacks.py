"""Comprehensive security attack simulation and invariant verification tests.

Validates CleanDownloads defense-in-depth security controls:
1. Path Traversal & Canonical Boundary Enforcement
2. Windows Reserved Device Names & NTFS Alternate Data Streams
3. Zero-Overwrite Invariant & Collision Resilience
4. Incomplete & Active Download Protection
5. Configuration Hardening & DoS Defense
6. SQLite SQL Injection Resilience & Transactional Safety
7. Undo Integrity Verification & Boundary Traversal Defense
8. Windows Task Scheduler Command Injection Protection
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cleandownloads.config import (
    DEFAULT_RULES,
    AppConfig,
    ConfigManager,
    ConfigurationError,
    RuleConfig,
    validate_extension_string,
    validate_subfolder_path,
)
from cleandownloads.history import HistoryDB
from cleandownloads.organizer import Organizer
from cleandownloads.safety import (
    SafetyViolationError,
    atomic_collision_safe_move,
    generate_collision_safe_path,
    is_incomplete_download,
    validate_move_paths,
    validate_safe_filename,
)
from cleandownloads.scheduler import WindowsScheduler
from cleandownloads.undo import UndoEngine

# ---------------------------------------------------------------------------
# 1. Path Traversal & Filename Attacks
# ---------------------------------------------------------------------------

def test_path_traversal_dot_dot_rejected(tmp_path: Path):
    """Verify relative traversal sequences are strictly rejected."""
    boundary = tmp_path / "Downloads"
    boundary.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("critical secret data")

    with pytest.raises(SafetyViolationError, match="Safety violation"):
        validate_move_paths(outside, boundary / "Documents" / "outside.txt", boundary)

    with pytest.raises(SafetyViolationError, match="illegal path separators or traversal"):
        validate_safe_filename("../escaped.pdf")

    with pytest.raises(SafetyViolationError, match="illegal path separators or traversal"):
        validate_safe_filename("..\\escaped.pdf")


def test_absolute_path_outside_boundary_rejected(tmp_path: Path):
    """Verify absolute paths outside boundary cannot be source or destination."""
    boundary = tmp_path / "Downloads"
    boundary.mkdir()
    source = boundary / "test.pdf"
    source.write_text("payload")

    forbidden_dest = tmp_path / "SecretDir" / "test.pdf"
    with pytest.raises(SafetyViolationError):
        validate_move_paths(source, forbidden_dest, boundary)


def test_windows_reserved_device_names_rejected():
    """Verify Windows device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9) are rejected."""
    reserved_samples = ["CON.pdf", "aux.txt", "NUL.png", "prn.docx", "COM1.zip", "lpt3.log"]
    for name in reserved_samples:
        with pytest.raises(SafetyViolationError, match="reserved device name"):
            validate_safe_filename(name)


def test_ntfs_alternate_data_stream_rejected():
    """Verify colon character in filenames (ADS exploit attempts) is rejected."""
    with pytest.raises(SafetyViolationError, match="Alternate Data Stream"):
        validate_safe_filename("normal.pdf:hidden_stream.exe")


def test_illegal_windows_characters_rejected():
    """Verify < > \" | ? * characters in filenames are rejected."""
    for bad_char in ['<', '>', '"', '|', '?', '*']:
        with pytest.raises(SafetyViolationError, match="illegal Windows characters"):
            validate_safe_filename(f"file{bad_char}name.pdf")


def test_null_byte_injection_rejected():
    """Verify null bytes in filenames are caught immediately."""
    with pytest.raises(SafetyViolationError, match="null byte"):
        validate_safe_filename("document.pdf\0.exe")


def test_extremely_long_filename_rejected():
    """Verify filenames exceeding 255 characters are rejected."""
    too_long = "a" * 256 + ".txt"
    with pytest.raises(SafetyViolationError, match="exceeds maximum allowed"):
        validate_safe_filename(too_long)


# ---------------------------------------------------------------------------
# 2. File Collision & Zero-Overwrite Invariants
# ---------------------------------------------------------------------------

def test_zero_overwrite_guarantee(tmp_path: Path):
    """Ensure existing destination files are NEVER overwritten under any circumstance."""
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    source = downloads / "report.pdf"
    source.write_text("NEW CONTENT")

    dest_dir = downloads / "Documents" / "PDF"
    dest_dir.mkdir(parents=True)
    existing_dest = dest_dir / "report.pdf"
    existing_dest.write_text("ORIGINAL SACRED CONTENT")

    final_dest, _ = atomic_collision_safe_move(source, existing_dest, boundary=downloads)

    # Original sacred destination must remain 100% untouched
    assert existing_dest.read_text() == "ORIGINAL SACRED CONTENT"
    # Moved file must be collision-safely renamed
    assert final_dest.name == "report (1).pdf"
    assert final_dest.read_text() == "NEW CONTENT"


def test_multiple_sequential_collisions_handled(tmp_path: Path):
    """Verify multiple existing collisions resolve to incrementing numbers."""
    target = tmp_path / "photo.png"
    target.write_text("v0")
    (tmp_path / "photo (1).png").write_text("v1")
    (tmp_path / "photo (2).png").write_text("v2")

    safe = generate_collision_safe_path(target)
    assert safe.name == "photo (3).png"


def test_unicode_and_zero_byte_files_handled_safely(tmp_path: Path):
    """Verify unicode, special characters, and zero-byte files are handled properly."""
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    unicode_file = downloads / "📄_レポート_résumé_2026.pdf"
    unicode_file.write_text("")  # zero-byte
    assert unicode_file.stat().st_size == 0

    dest = downloads / "Documents" / "PDF" / unicode_file.name
    actual_dest, file_hash = atomic_collision_safe_move(unicode_file, dest, downloads)

    assert actual_dest.exists()
    assert actual_dest.stat().st_size == 0
    # SHA-256 of empty file is e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    assert file_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


# ---------------------------------------------------------------------------
# 3. Incomplete & Active Download Protection
# ---------------------------------------------------------------------------

def test_incomplete_download_extensions_rejected():
    """Verify active browser downloads are never classified or moved."""
    incomplete_samples = [
        Path("setup.exe.crdownload"),
        Path("video.mp4.part"),
        Path("data.zip.tmp"),
        Path("archive.tar.download"),
        Path("movie.mkv.!ut"),
    ]
    for p in incomplete_samples:
        assert is_incomplete_download(p) is True


# ---------------------------------------------------------------------------
# 4. Configuration Security & Schema Validation
# ---------------------------------------------------------------------------

def test_malicious_subfolder_traversal_rejected():
    """Ensure subfolders in rules cannot contain traversal or absolute paths."""
    bad_subfolders = [
        "../Windows/System32",
        "..\\..\\",
        "C:\\Windows",
        "/usr/bin",
        "CON/PDF",
        "folder:stream",
        "sub/folder/nested/deeply/extra/layer",  # exceeds max depth
    ]
    for bad in bad_subfolders:
        with pytest.raises(ConfigurationError):
            validate_subfolder_path(bad)


def test_malicious_extension_regex_validation():
    """Ensure rule extensions are strictly alphanumeric and cannot contain scripts or separators."""
    bad_exts = [
        "pdf;rm -rf /",
        "exe|calc",
        "../txt",
        "docx\0",
        "",
        "a" * 33,  # exceeds max extension length
    ]
    for bad in bad_exts:
        with pytest.raises(ConfigurationError):
            validate_extension_string(bad)


def test_oversized_config_file_rejected(tmp_path: Path):
    """Ensure configuration parser rejects oversized JSON files to prevent DoS."""
    cfg_file = tmp_path / "config.json"
    # Create 600 KB file (limit is 512 KB)
    cfg_file.write_text(" " * (600 * 1024))

    mgr = ConfigManager(config_path=cfg_file)
    with pytest.raises(ConfigurationError, match="exceeds safe limit"):
        mgr.load(raise_on_error=True)


def test_malformed_json_config_falls_back_safely(tmp_path: Path):
    """Ensure malformed JSON falls back gracefully to default rules."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text("{ this is not valid json :(")

    mgr = ConfigManager(config_path=cfg_file)
    # Normal load: falls back safely to default config
    assert len(mgr.config.rules) > 0

    # Strict load: raises ConfigurationError
    with pytest.raises(ConfigurationError, match="Malformed JSON"):
        mgr.load(raise_on_error=True)


# ---------------------------------------------------------------------------
# 5. SQL Injection & Database Resilience
# ---------------------------------------------------------------------------

def test_sqlite_sql_injection_payload_in_filename(tmp_path: Path):
    """Ensure SQL injection strings in filenames or categories cannot corrupt database."""
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    sqli_name = "test'; DROP TABLE operations; --.pdf"
    # Create valid physical file
    file_path = downloads / sqli_name
    file_path.write_text("test pdf content")

    rules = [RuleConfig(**r) for r in DEFAULT_RULES]
    config = AppConfig(rules=rules, downloads_dir=str(downloads), min_file_age_seconds=0)
    db_path = tmp_path / "sqli_test.db"
    history_db = HistoryDB(db_path=db_path)
    organizer = Organizer(config=config, history_db=history_db)

    # Perform organization
    res = organizer.organize(dry_run=False)
    assert res.successful_moves == 1

    # Table operations must still exist and contain the record!
    batch = history_db.get_batch(res.batch_id)
    assert batch is not None
    ops = history_db.get_operations_for_batch(res.batch_id)
    assert len(ops) == 1
    assert "DROP TABLE" in ops[0].original_path


# ---------------------------------------------------------------------------
# 6. Undo Integrity & Tamper Resistance
# ---------------------------------------------------------------------------

def test_undo_refuses_restoring_modified_file(tmp_path: Path):
    """Verify undo engine rejects restoring a file whose SHA-256 hash was altered."""
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    test_file = downloads / "document.pdf"
    test_file.write_text("authentic original content")

    rules = [RuleConfig(**r) for r in DEFAULT_RULES]
    config = AppConfig(rules=rules, downloads_dir=str(downloads), min_file_age_seconds=0)
    db_path = tmp_path / "tamper_test.db"
    history_db = HistoryDB(db_path=db_path)
    organizer = Organizer(config=config, history_db=history_db)

    res = organizer.organize(dry_run=False)
    assert res.successful_moves == 1

    dest_file = downloads / "Documents" / "PDF" / "document.pdf"
    assert dest_file.exists()

    # Tamper with the file at destination!
    dest_file.write_text("MALICIOUS MODIFIED CONTENT OVERWRITE")

    # Attempt undo
    undo_engine = UndoEngine(history_db=history_db, boundary=downloads)
    undo_res = undo_engine.undo_last()

    assert undo_res is not None
    # Must fail because integrity verification failed
    assert undo_res.fail_count == 1
    assert undo_res.success_count == 0
    assert "integrity verification failed" in undo_res.failed_files[0].reason

    # Destination file must remain untouched in its location
    assert dest_file.exists()


def test_undo_refuses_corrupted_system_paths_in_db(tmp_path: Path):
    """Verify undo engine refuses to restore to restricted system paths even if DB was tampered."""
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    test_file = downloads / "malicious.dll"
    test_file.write_text("fake dll")

    db_path = tmp_path / "tampered_db.db"
    history_db = HistoryDB(db_path=db_path)

    batch_id = history_db.start_batch(total_files=1)
    # Simulate attacker tampering with history.db to restore into System32
    history_db.record_operation(
        batch_id=batch_id,
        original_path=r"C:\Windows\System32\malicious.dll",
        destination_path=str(test_file),
        file_size=8,
        file_extension="dll",
        category="System",
        status="MOVED",
    )

    undo_engine = UndoEngine(history_db=history_db, boundary=downloads)
    undo_res = undo_engine.undo_batch(batch_id)

    assert undo_res.fail_count == 1
    assert undo_res.success_count == 0
    assert "violates system security" in undo_res.failed_files[0].reason or "escapes" in undo_res.failed_files[0].reason


# ---------------------------------------------------------------------------
# 7. Scheduler Security
# ---------------------------------------------------------------------------

def test_scheduler_rejects_malicious_task_name():
    """Verify WindowsScheduler constructor rejects task names containing command injection characters."""
    bad_names = [
        "Task; calc.exe",
        "Task && whoami",
        "Task | dir",
        "Task/Name",
        "Task\\Name",
        "a" * 65,  # too long
        "",
    ]
    for bad in bad_names:
        with pytest.raises(ValueError, match="Invalid task name"):
            WindowsScheduler(task_name=bad)
