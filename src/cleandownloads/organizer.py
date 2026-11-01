"""Core organization coordinator for moving files cleanly and safely."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from cleandownloads.config import AppConfig
from cleandownloads.history import HistoryDB
from cleandownloads.safety import (
    SingleInstanceLock,
    atomic_collision_safe_move,
    generate_collision_safe_path,
)
from cleandownloads.scanner import ScannedFile, Scanner, ScanResult


@dataclass
class PlannedMove:
    """A move planned during dry-run or organization."""
    source: Path
    destination: Path
    file_size: int
    category: str
    extension: str


@dataclass
class MovePlan:
    """Complete dry-run execution plan."""
    downloads_dir: Path
    planned_moves: list[PlannedMove] = field(default_factory=list)
    total_files: int = 0
    total_bytes: int = 0


@dataclass
class ExecutedMove:
    """Result of an individual file move."""
    source: Path
    destination: Path
    file_size: int
    category: str
    operation_id: int


@dataclass
class FailedMove:
    """Details of a failed move attempt."""
    source: Path
    target_destination: Path
    error: str
    category: str


@dataclass
class MoveResult:
    """Outcome of an organization execution."""
    batch_id: str | None
    total_files: int
    successful_moves: int
    failed_moves: int
    moved_items: list[ExecutedMove] = field(default_factory=list)
    failed_items: list[FailedMove] = field(default_factory=list)
    is_dry_run: bool = False


class Organizer:
    """Coordinates scanning, safety validation, atomic moving, and SQLite history logging."""

    def __init__(
        self,
        config: AppConfig,
        history_db: HistoryDB | None = None,
        scanner: Scanner | None = None,
        lock: SingleInstanceLock | None = None,
    ) -> None:
        self.config = config
        self.history_db = history_db or HistoryDB()
        self.scanner = scanner or Scanner(config)
        self.lock = lock or SingleInstanceLock()

    def plan(self, scan_result: ScanResult | None = None) -> MovePlan:
        """Generate a dry-run plan without moving any files."""
        if scan_result is None:
            scan_result = self.scanner.scan()

        downloads_dir = scan_result.downloads_dir
        planned_moves: list[PlannedMove] = []

        for f in scan_result.ready_files:
            ideal_dest = downloads_dir / f.destination_relative_path
            safe_dest = generate_collision_safe_path(ideal_dest)

            planned_moves.append(
                PlannedMove(
                    source=f.path,
                    destination=safe_dest,
                    file_size=f.size_bytes,
                    category=f.category,
                    extension=f.extension,
                )
            )

        return MovePlan(
            downloads_dir=downloads_dir,
            planned_moves=planned_moves,
            total_files=len(planned_moves),
            total_bytes=sum(m.file_size for m in planned_moves),
        )

    def organize(
        self,
        dry_run: bool = False,
        scan_result: ScanResult | None = None,
        on_progress: Callable[[ScannedFile, Path], None] | None = None,
        on_error: Callable[[ScannedFile, Exception], None] | None = None,
    ) -> MoveResult:
        """Organize the Downloads folder according to classification rules."""
        if scan_result is None:
            scan_result = self.scanner.scan()

        if dry_run:
            plan = self.plan(scan_result)
            return MoveResult(
                batch_id=None,
                total_files=plan.total_files,
                successful_moves=plan.total_files,
                failed_moves=0,
                moved_items=[
                    ExecutedMove(
                        source=m.source,
                        destination=m.destination,
                        file_size=m.file_size,
                        category=m.category,
                        operation_id=0,
                    )
                    for m in plan.planned_moves
                ],
                failed_items=[],
                is_dry_run=True,
            )

        with self.lock:
            downloads_dir = scan_result.downloads_dir
            ready_files = scan_result.ready_files

            if not ready_files:
                return MoveResult(
                    batch_id=None,
                    total_files=0,
                    successful_moves=0,
                    failed_moves=0,
                    is_dry_run=False,
                )

            batch_id = self.history_db.start_batch(
                total_files=len(ready_files),
                notes="Organized via CleanDownloads",
            )

            successful_moves: list[ExecutedMove] = []
            failed_moves: list[FailedMove] = []

            for f in ready_files:
                target_dest = downloads_dir / f.destination_relative_path
                try:
                    actual_dest, file_hash = atomic_collision_safe_move(
                        source=f.path,
                        destination=target_dest,
                        boundary=downloads_dir,
                    )

                    op_id = self.history_db.record_operation(
                        batch_id=batch_id,
                        original_path=str(f.path),
                        destination_path=str(actual_dest),
                        file_size=f.size_bytes,
                        file_extension=f.extension,
                        category=f.category,
                        status="MOVED",
                        file_hash=file_hash,
                    )

                    item = ExecutedMove(
                        source=f.path,
                        destination=actual_dest,
                        file_size=f.size_bytes,
                        category=f.category,
                        operation_id=op_id,
                    )
                    successful_moves.append(item)

                    if on_progress:
                        on_progress(f, actual_dest)

                except Exception as exc:
                    # Catch move failures (e.g. safety violations, file locks, permissions, OSError)
                    # and record each as a failed operation in history rather than aborting the entire batch.
                    err_msg = str(exc)
                    self.history_db.record_operation(
                        batch_id=batch_id,
                        original_path=str(f.path),
                        destination_path=str(target_dest),
                        file_size=f.size_bytes,
                        file_extension=f.extension,
                        category=f.category,
                        status="FAILED",
                        error_info=err_msg,
                    )

                    failed_moves.append(
                        FailedMove(
                            source=f.path,
                            target_destination=target_dest,
                            error=err_msg,
                            category=f.category,
                        )
                    )

                    if on_error:
                        on_error(f, exc)

            # Finalize batch in history
            self.history_db.finish_batch(
                batch_id=batch_id,
                successful_moves=len(successful_moves),
                failed_moves=len(failed_moves),
            )

            return MoveResult(
                batch_id=batch_id,
                total_files=len(ready_files),
                successful_moves=len(successful_moves),
                failed_moves=len(failed_moves),
                moved_items=successful_moves,
                failed_items=failed_moves,
                is_dry_run=False,
            )
