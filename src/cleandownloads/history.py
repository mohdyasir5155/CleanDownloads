import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cleandownloads.safety import get_app_data_dir

HISTORY_DB_FILENAME = "history.db"


@dataclass
class OperationRecord:
    """Record of a single file move or attempt."""
    id: int | None
    batch_id: str
    original_path: str
    destination_path: str
    file_size: int
    file_extension: str
    category: str
    timestamp: str
    status: str  # 'MOVED', 'UNDONE', 'FAILED'
    error_info: str | None = None
    file_hash: str | None = None


@dataclass
class BatchRecord:
    """Record of an organization run containing multiple operations."""
    id: str
    timestamp: str
    total_files: int
    successful_moves: int
    failed_moves: int
    status: str  # 'COMPLETED', 'PARTIALLY_COMPLETED', 'UNDONE', 'FAILED'
    notes: str | None = None


class HistoryDB:
    """Manages SQLite persistence for operation batches and file moves."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = get_app_data_dir() / HISTORY_DB_FILENAME

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Yield a connection with row factory enabled and close on exit."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema with proper indexes and migrations."""
        try:
            self._create_schema()
        except sqlite3.DatabaseError:
            # Corrupted database recovery: archive corrupted file and reinitialize fresh
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            corrupt_backup = self.db_path.with_name(f"{self.db_path.name}.corrupt.{timestamp}")
            try:
                if self.db_path.exists():
                    self.db_path.rename(corrupt_backup)
            except OSError:
                pass
            self._create_schema()

    def _create_schema(self) -> None:
        """Create tables, migrations, and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batches (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    total_files INTEGER NOT NULL,
                    successful_moves INTEGER NOT NULL,
                    failed_moves INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL,
                    original_path TEXT NOT NULL,
                    destination_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_extension TEXT NOT NULL,
                    category TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_info TEXT,
                    file_hash TEXT,
                    FOREIGN KEY (batch_id) REFERENCES batches (id)
                )
            """)
            # Schema migration: ensure file_hash column exists if upgrading older DB
            cursor.execute("PRAGMA table_info(operations)")
            columns = [row[1] for row in cursor.fetchall()]
            if "file_hash" not in columns:
                cursor.execute("ALTER TABLE operations ADD COLUMN file_hash TEXT")

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_ops_batch ON operations(batch_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_ops_status ON operations(status)"
            )
            conn.commit()

    def start_batch(self, total_files: int = 0, notes: str | None = None) -> str:
        """Create and start a new operation batch, returning the unique batch ID."""
        batch_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO batches (id, timestamp, total_files, successful_moves, failed_moves, status, notes)
                VALUES (?, ?, ?, 0, 0, 'IN_PROGRESS', ?)
                """,
                (batch_id, timestamp, total_files, notes),
            )
            conn.commit()
        return batch_id

    def record_operation(
        self,
        batch_id: str,
        original_path: str,
        destination_path: str,
        file_size: int,
        file_extension: str,
        category: str,
        status: str = "MOVED",
        error_info: str | None = None,
        file_hash: str | None = None,
    ) -> int:
        """Record an individual file move or failure."""
        timestamp = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO operations (
                    batch_id, original_path, destination_path, file_size,
                    file_extension, category, timestamp, status, error_info, file_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch_id,
                    original_path,
                    destination_path,
                    file_size,
                    file_extension,
                    category,
                    timestamp,
                    status,
                    error_info,
                    file_hash,
                ),
            )
            op_id = cursor.lastrowid or 0
            conn.commit()
        return op_id

    def finish_batch(
        self,
        batch_id: str,
        successful_moves: int,
        failed_moves: int,
        status: str | None = None,
    ) -> None:
        """Finalize an operation batch with move counts and status."""
        if status is None:
            if failed_moves == 0:
                status = "COMPLETED"
            elif successful_moves > 0:
                status = "PARTIALLY_COMPLETED"
            else:
                status = "FAILED"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE batches
                SET successful_moves = ?, failed_moves = ?, status = ?
                WHERE id = ?
                """,
                (successful_moves, failed_moves, status, batch_id),
            )
            conn.commit()

    def update_operation_status(
        self, op_id: int, status: str, error_info: str | None = None
    ) -> None:
        """Update the status of an existing operation (e.g. to 'UNDONE')."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE operations
                SET status = ?, error_info = COALESCE(?, error_info)
                WHERE id = ?
                """,
                (status, error_info, op_id),
            )
            conn.commit()

    def update_batch_status(self, batch_id: str, status: str) -> None:
        """Update batch status (e.g. to 'UNDONE')."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE batches SET status = ? WHERE id = ?",
                (status, batch_id),
            )
            conn.commit()

    def get_last_batch(self) -> BatchRecord | None:
        """Fetch the most recent operation batch."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, timestamp, total_files, successful_moves, failed_moves, status, notes
                FROM batches
                ORDER BY timestamp DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row:
                return BatchRecord(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    total_files=row["total_files"],
                    successful_moves=row["successful_moves"],
                    failed_moves=row["failed_moves"],
                    status=row["status"],
                    notes=row["notes"],
                )
        return None

    def get_batch(self, batch_id: str) -> BatchRecord | None:
        """Fetch a specific batch by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, timestamp, total_files, successful_moves, failed_moves, status, notes
                FROM batches
                WHERE id = ?
                """,
                (batch_id,),
            )
            row = cursor.fetchone()
            if row:
                return BatchRecord(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    total_files=row["total_files"],
                    successful_moves=row["successful_moves"],
                    failed_moves=row["failed_moves"],
                    status=row["status"],
                    notes=row["notes"],
                )
        return None

    def get_operations_for_batch(
        self, batch_id: str, status_filter: str | None = None
    ) -> list[OperationRecord]:
        """Fetch all operations associated with a batch."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status_filter:
                cursor.execute(
                    """
                    SELECT id, batch_id, original_path, destination_path, file_size,
                           file_extension, category, timestamp, status, error_info, file_hash
                    FROM operations
                    WHERE batch_id = ? AND status = ?
                    ORDER BY id ASC
                    """,
                    (batch_id, status_filter),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, batch_id, original_path, destination_path, file_size,
                           file_extension, category, timestamp, status, error_info, file_hash
                    FROM operations
                    WHERE batch_id = ?
                    ORDER BY id ASC
                    """,
                    (batch_id,),
                )
            rows = cursor.fetchall()
            return [
                OperationRecord(
                    id=row["id"],
                    batch_id=row["batch_id"],
                    original_path=row["original_path"],
                    destination_path=row["destination_path"],
                    file_size=row["file_size"],
                    file_extension=row["file_extension"],
                    category=row["category"],
                    timestamp=row["timestamp"],
                    status=row["status"],
                    error_info=row["error_info"],
                    file_hash=row["file_hash"] if "file_hash" in row.keys() else None,
                )
                for row in rows
            ]

    def get_recent_batches(self, limit: int = 10) -> list[BatchRecord]:
        """Fetch recent batches ordered by latest first."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, timestamp, total_files, successful_moves, failed_moves, status, notes
                FROM batches
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                BatchRecord(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    total_files=row["total_files"],
                    successful_moves=row["successful_moves"],
                    failed_moves=row["failed_moves"],
                    status=row["status"],
                    notes=row["notes"],
                )
                for row in rows
            ]

    def get_overall_stats(self) -> dict[str, Any]:
        """Aggregate total moves, undone count, and categorized totals."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM batches")
            total_batches = cursor.fetchone()["count"]

            cursor.execute(
                "SELECT COUNT(*) as count FROM operations WHERE status = 'MOVED'"
            )
            active_organized = cursor.fetchone()["count"]

            cursor.execute(
                "SELECT COUNT(*) as count FROM operations WHERE status = 'UNDONE'"
            )
            total_undone = cursor.fetchone()["count"]

            cursor.execute(
                "SELECT COUNT(*) as count FROM operations WHERE status = 'FAILED'"
            )
            total_failed = cursor.fetchone()["count"]

            cursor.execute(
                """
                SELECT category, COUNT(*) as count
                FROM operations
                WHERE status = 'MOVED'
                GROUP BY category
                """
            )
            category_counts = {row["category"]: row["count"] for row in cursor.fetchall()}

        return {
            "total_batches": total_batches,
            "active_organized_files": active_organized,
            "total_undone_files": total_undone,
            "total_failed_moves": total_failed,
            "category_breakdown": category_counts,
        }
