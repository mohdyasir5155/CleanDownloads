"""Tests for the Undo engine."""

from pathlib import Path

import pytest

from cleandownloads.config import DEFAULT_RULES, AppConfig, RuleConfig
from cleandownloads.history import HistoryDB
from cleandownloads.organizer import Organizer
from cleandownloads.undo import UndoEngine


@pytest.fixture
def organized_setup(tmp_path: Path):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    (downloads / "resume.pdf").write_text("my resume")
    (downloads / "avatar.png").write_text("my avatar")

    rules = [RuleConfig(**r) for r in DEFAULT_RULES]
    config = AppConfig(rules=rules, downloads_dir=str(downloads), min_file_age_seconds=0)
    history_db = HistoryDB(db_path=tmp_path / "undo_test.db")
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
