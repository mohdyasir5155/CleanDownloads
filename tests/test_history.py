"""Tests for SQLite history database, batching, and statistics."""

from pathlib import Path

from cleandownloads.history import HistoryDB


def test_history_batch_lifecycle(tmp_path: Path):
    db_file = tmp_path / "hist.db"
    db = HistoryDB(db_path=db_file)

    batch_id = db.start_batch(total_files=2, notes="Test batch")
    assert batch_id is not None

    op1 = db.record_operation(
        batch_id=batch_id,
        original_path="C:/Downloads/a.pdf",
        destination_path="C:/Downloads/Documents/PDF/a.pdf",
        file_size=1024,
        file_extension="pdf",
        category="Documents",
        status="MOVED",
    )
    assert op1 > 0

    op2 = db.record_operation(
        batch_id=batch_id,
        original_path="C:/Downloads/b.png",
        destination_path="C:/Downloads/Images/PNG/b.png",
        file_size=2048,
        file_extension="png",
        category="Images",
        status="MOVED",
    )
    assert op2 > 0

    db.finish_batch(batch_id=batch_id, successful_moves=2, failed_moves=0)

    last_batch = db.get_last_batch()
    assert last_batch is not None
    assert last_batch.id == batch_id
    assert last_batch.status == "COMPLETED"
    assert last_batch.successful_moves == 2

    ops = db.get_operations_for_batch(batch_id)
    assert len(ops) == 2
    assert ops[0].status == "MOVED"

    stats = db.get_overall_stats()
    assert stats["total_batches"] == 1
    assert stats["active_organized_files"] == 2
    assert stats["total_undone_files"] == 0
    assert stats["category_breakdown"]["Documents"] == 1
    assert stats["category_breakdown"]["Images"] == 1


def test_corrupted_database_auto_recovery(tmp_path: Path):
    """Ensure a corrupted database file is automatically archived and recovered."""
    db_file = tmp_path / "corrupt_test.db"
    db_file.write_text("NOT A SQLITE DATABASE", encoding="utf-8")

    db = HistoryDB(db_path=db_file)
    batch_id = db.start_batch(total_files=1)
    assert batch_id is not None

    # Verify corrupt file was archived
    archived = list(tmp_path.glob("corrupt_test.db.corrupt.*"))
    assert len(archived) == 1

