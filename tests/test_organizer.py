"""Tests for organization coordinator and batch execution."""

from pathlib import Path

import pytest

from cleandownloads.config import DEFAULT_RULES, AppConfig, RuleConfig
from cleandownloads.history import HistoryDB
from cleandownloads.organizer import Organizer


@pytest.fixture
def test_setup(tmp_path: Path):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    # Create test files
    (downloads / "doc.pdf").write_text("pdf content")
    (downloads / "pic.png").write_text("png content")
    (downloads / "tool.exe").write_text("exe content")

    rules = [RuleConfig(**r) for r in DEFAULT_RULES]
    config = AppConfig(rules=rules, downloads_dir=str(downloads))
    db_path = tmp_path / "test_history.db"
    history_db = HistoryDB(db_path=db_path)

    organizer = Organizer(config=config, history_db=history_db)
    return downloads, history_db, organizer


def test_dry_run_leaves_files_untouched(test_setup):
    downloads, history_db, organizer = test_setup

    res = organizer.organize(dry_run=True)

    assert res.is_dry_run
    assert res.total_files == 3
    assert res.batch_id is None

    # Files must still exist in root
    assert (downloads / "doc.pdf").exists()
    assert (downloads / "pic.png").exists()
    assert (downloads / "tool.exe").exists()

    # Destination directories must not have been created
    assert not (downloads / "Documents" / "PDF" / "doc.pdf").exists()
    assert history_db.get_last_batch() is None


def test_real_organize_moves_files_and_logs(test_setup):
    downloads, history_db, organizer = test_setup

    res = organizer.organize(dry_run=False)

    assert not res.is_dry_run
    assert res.successful_moves == 3
    assert res.failed_moves == 0
    assert res.batch_id is not None

    # Files should now be in respective subdirectories
    dest_pdf = downloads / "Documents" / "PDF" / "doc.pdf"
    dest_png = downloads / "Images" / "PNG" / "pic.png"
    dest_exe = downloads / "Software" / "EXE" / "tool.exe"

    assert dest_pdf.exists()
    assert dest_png.exists()
    assert dest_exe.exists()

    # Root files should be moved
    assert not (downloads / "doc.pdf").exists()
    assert not (downloads / "pic.png").exists()
    assert not (downloads / "tool.exe").exists()

    # Verify SQLite logging
    batch = history_db.get_batch(res.batch_id)
    assert batch is not None
    assert batch.status == "COMPLETED"
    assert batch.successful_moves == 3

    ops = history_db.get_operations_for_batch(res.batch_id)
    assert len(ops) == 3
    for op in ops:
        assert op.status == "MOVED"


def test_collision_safe_organize(tmp_path: Path):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    # Create root file to organize
    (downloads / "notes.pdf").write_text("new notes")

    # Pre-create destination with same name
    dest_dir = downloads / "Documents" / "PDF"
    dest_dir.mkdir(parents=True)
    existing_file = dest_dir / "notes.pdf"
    existing_file.write_text("old notes")

    rules = [RuleConfig(**r) for r in DEFAULT_RULES]
    config = AppConfig(rules=rules, downloads_dir=str(downloads))
    history_db = HistoryDB(db_path=tmp_path / "hist.db")
    organizer = Organizer(config=config, history_db=history_db)

    res = organizer.organize(dry_run=False)

    assert res.successful_moves == 1
    # Original destination file must still exist untouched
    assert existing_file.read_text() == "old notes"

    # Newly organized file must be renamed to notes (1).pdf
    renamed_dest = dest_dir / "notes (1).pdf"
    assert renamed_dest.exists()
    assert renamed_dest.read_text() == "new notes"
