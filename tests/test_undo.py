"""Tests for the Undo engine."""

from pathlib import Path

import pytest

from cleandownloads.config import DEFAULT_RULES, AppConfig, RuleConfig
from cleandownloads.history import HistoryDB
from cleandownloads.organizer import Organizer
from cleandownloads.undo import UndoEngine


@pytest.fixture
def organized_setup(tmp_path: Path, monkeypatch):
    app_data = tmp_path / "appdata"
    monkeypatch.setenv("CLEANDOWNLOADS_DATA_DIR", str(app_data))
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    (downloads / "resume.pdf").write_text("my resume")
    (downloads / "avatar.png").write_text("my avatar")

    rules = [RuleConfig(**r) for r in DEFAULT_RULES]
    config = AppConfig(rules=rules, downloads_dir=str(downloads), min_file_age_seconds=0)
    history_db = HistoryDB()
    organizer = Organizer(config=config, history_db=history_db)

    # Perform organize
    res = organizer.organize(dry_run=False)
    assert res.successful_moves == 2

    return downloads, history_db, organizer, res.batch_id


def test_undo_restores_files_to_original_location(organized_setup):
    downloads, history_db, organizer, batch_id = organized_setup

    dest_pdf = downloads / "Documents" / "PDF" / "resume.pdf"
    dest_png = downloads / "Images" / "PNG" / "avatar.png"
    assert dest_pdf.exists()
    assert dest_png.exists()

    undo_engine = UndoEngine(history_db)
    undo_res = undo_engine.undo_last()

    assert undo_res is not None
    assert undo_res.success_count == 2
    assert undo_res.fail_count == 0

    # Files must be restored to root
    orig_pdf = downloads / "resume.pdf"
    orig_png = downloads / "avatar.png"

    assert orig_pdf.exists()
    assert orig_pdf.read_text() == "my resume"
    assert orig_png.exists()
    assert orig_png.read_text() == "my avatar"

    # Destination files should no longer be present
    assert not dest_pdf.exists()
    assert not dest_png.exists()

    # DB records updated
    ops = history_db.get_operations_for_batch(batch_id)
    for op in ops:
        assert op.status == "UNDONE"

    batch = history_db.get_batch(batch_id)
    assert batch is not None
    assert batch.status == "UNDONE"


def test_undo_collision_handling(organized_setup):
    downloads, history_db, organizer, batch_id = organized_setup

    # User manually placed a new file at the original location
    root_pdf = downloads / "resume.pdf"
    root_pdf.write_text("new freshly downloaded resume")

    undo_engine = UndoEngine(history_db)
    undo_res = undo_engine.undo_last()

    assert undo_res is not None
    assert undo_res.success_count == 2

    # The freshly downloaded file must not be overwritten!
    assert root_pdf.read_text() == "new freshly downloaded resume"

    # The restored file should be collision safe: resume (1).pdf
    restored_pdf = downloads / "resume (1).pdf"
    assert restored_pdf.exists()
    assert restored_pdf.read_text() == "my resume"


def test_undo_missing_file_handled_gracefully(organized_setup):
    downloads, history_db, organizer, batch_id = organized_setup

    # Simulate user deleting or moving the PDF outside CleanDownloads
    dest_pdf = downloads / "Documents" / "PDF" / "resume.pdf"
    dest_pdf.unlink()

    undo_engine = UndoEngine(history_db)
    undo_res = undo_engine.undo_last()

    assert undo_res is not None
    assert undo_res.success_count == 1  # avatar.png restored
    assert undo_res.fail_count == 1     # resume.pdf missing

    failed_reasons = [ff.reason for ff in undo_res.failed_files]
    assert any("deleted, renamed, or moved" in r for r in failed_reasons)


def test_undo_strict_mode_rejects_modified_file(organized_setup):
    downloads, history_db, organizer, batch_id = organized_setup

    dest_pdf = downloads / "Documents" / "PDF" / "resume.pdf"
    assert dest_pdf.exists()

    # Modify the file content after organize
    dest_pdf.write_text("modified resume text that changed hash")

    undo_engine = UndoEngine(history_db)
    # Default strict mode (force_modified=False)
    undo_res = undo_engine.undo_last(force_modified=False)

    assert undo_res is not None
    assert undo_res.fail_count == 1
    assert "hash mismatch" in undo_res.failed_files[0].reason
    assert dest_pdf.exists()


def test_undo_force_modified_override(organized_setup):
    downloads, history_db, organizer, batch_id = organized_setup

    dest_pdf = downloads / "Documents" / "PDF" / "resume.pdf"
    assert dest_pdf.exists()

    # Modify the file content after organize
    dest_pdf.write_text("modified resume text that changed hash")

    undo_engine = UndoEngine(history_db)
    # Force modified override mode
    undo_res = undo_engine.undo_last(force_modified=True)

    assert undo_res is not None
    assert undo_res.fail_count == 0
    assert undo_res.success_count == 2

    # Modified file restored back to original path with modified content intact
    orig_pdf = downloads / "resume.pdf"
    assert orig_pdf.exists()
    assert orig_pdf.read_text() == "modified resume text that changed hash"

    # History recorded OVERRIDE_MODIFIED
    ops = history_db.get_operations_for_batch(batch_id)
    pdf_op = next(op for op in ops if "resume.pdf" in op.original_path)
    assert pdf_op.status == "UNDONE"
    assert pdf_op.error_info == "OVERRIDE_MODIFIED"

    batch = history_db.get_batch(batch_id)
    assert batch is not None
    assert "force-modified" in (batch.notes or "")


def test_cli_undo_force_modified_prompt_cancelled(organized_setup, monkeypatch, capsys):
    from cleandownloads.cli import main

    downloads, history_db, organizer, batch_id = organized_setup
    dest_pdf = downloads / "Documents" / "PDF" / "resume.pdf"
    dest_pdf.write_text("altered content")

    # Prompt user and user enters 'n'
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    monkeypatch.setattr("sys.argv", ["cleandownloads", "undo", "--force-modified"])

    main()

    # File was NOT moved back because user cancelled
    assert dest_pdf.exists()
    assert not (downloads / "resume.pdf").exists()


def test_cli_undo_force_modified_with_yes(organized_setup, monkeypatch, capsys):
    from cleandownloads.cli import main

    downloads, history_db, organizer, batch_id = organized_setup
    dest_pdf = downloads / "Documents" / "PDF" / "resume.pdf"
    dest_pdf.write_text("altered content")

    monkeypatch.setattr("sys.argv", ["cleandownloads", "undo", "--force-modified", "--yes"])

    main()

    # File was restored back
    assert not dest_pdf.exists()
    assert (downloads / "resume.pdf").exists()
    assert (downloads / "resume.pdf").read_text() == "altered content"


def test_single_pass_hashing_and_lock_check(tmp_path: Path):
    from cleandownloads.safety import atomic_collision_safe_move

    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    source = downloads / "single_pass.pdf"
    source.write_text("single pass content")
    dest = downloads / "Documents" / "PDF" / "single_pass.pdf"

    # Track how many times open is called on source
    open_calls: list[Path] = []
    original_open = open

    def tracking_open(file, *args, **kwargs):
        if str(file) == str(source):
            open_calls.append(file)
        return original_open(file, *args, **kwargs)

    import builtins
    builtins.open = tracking_open
    try:
        final_dest, file_hash = atomic_collision_safe_move(
            source=source,
            destination=dest,
            boundary=downloads,
        )
    finally:
        builtins.open = original_open

    # Must only open source once for both lock check and hash calculation
    assert len(open_calls) == 1
    assert final_dest.exists()
