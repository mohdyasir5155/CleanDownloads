"""Safe and reliable undo engine for reversing file organization."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from cleandownloads.history import BatchRecord, HistoryDB
from cleandownloads.safety import (
    SafetyViolationError,
    atomic_collision_safe_move,
    compute_file_sha256,
    get_default_downloads_dir,
    is_file_locked,
    is_path_within_boundary,
    is_symlink_escaping_boundary,
    validate_safe_filename,
)


@dataclass
class RestoredFile:
    """Details of a successfully restored file."""
    operation_id: int
    original_path: Path
    moved_from_path: Path
    actual_restored_path: Path


@dataclass
class FailedUndo:
    """Details of a file that could not be restored."""
    operation_id: int
    moved_from_path: Path
    target_path: Path
    reason: str


@dataclass
class UndoResult:
    """Complete summary of an undo execution."""
    batch_id: str
    total_attempted: int
    restored_files: list[RestoredFile] = field(default_factory=list)
    failed_files: list[FailedUndo] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return len(self.restored_files)

    @property
    def fail_count(self) -> int:
        return len(self.failed_files)


def get_restricted_system_roots() -> list[Path]:
    """Return paths to protected system directories where restoration is forbidden."""
    roots: list[Path] = []
    if sys.platform == "win32":
        for env_var in ("SystemRoot", "windir", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
            val = os.environ.get(env_var)
            if val:
                try:
                    roots.append(Path(val).resolve())
                except Exception:
                    pass
    else:
        for p in ("/bin", "/sbin", "/usr", "/etc", "/var", "/lib", "/sys", "/proc", "/dev"):
            try:
                roots.append(Path(p).resolve())
            except Exception:
                pass
    return roots


class UndoEngine:
    """Restores organized files to their original locations safely and reliably."""

    def __init__(
        self,
        history_db: HistoryDB | None = None,
        boundary: Path | None = None,
    ) -> None:
        self.history_db = history_db or HistoryDB()
        self.boundary = boundary

    def _determine_effective_boundary(
        self, orig_path: Path, current_dest: Path
    ) -> Path | None:
        """Determine and validate the containment boundary for undo operations."""
        if self.boundary:
            return self.boundary

        default_downloads = get_default_downloads_dir()
        if is_path_within_boundary(orig_path, default_downloads) and is_path_within_boundary(
            current_dest, default_downloads
        ):
            return default_downloads

        # Custom / testing boundary: find common ancestor directory
        try:
            res_orig = orig_path.resolve(strict=False)
            res_dest = current_dest.resolve(strict=False)
            common = Path(os.path.commonpath([str(res_orig), str(res_dest)]))
            # Must not be filesystem root (e.g. C:\ or /) or user profile directory directly
            if common == common.parent or common == Path.home().resolve():
                return None
            return common
        except Exception:
            return None

    def undo_last(self) -> UndoResult | None:
        """Undo the most recent organization batch that has active moved files."""
        batches = self.history_db.get_recent_batches(limit=10)
        target_batch: BatchRecord | None = None

        for b in batches:
            if b.status in ("COMPLETED", "PARTIALLY_COMPLETED"):
                ops = self.history_db.get_operations_for_batch(b.id, status_filter="MOVED")
                if ops:
                    target_batch = b
                    break

        if not target_batch:
            return None

        return self.undo_batch(target_batch.id)

    def undo_batch(self, batch_id: str) -> UndoResult:
        """Undo all moved operations for a specific batch ID."""
        operations = self.history_db.get_operations_for_batch(
            batch_id=batch_id, status_filter="MOVED"
        )

        result = UndoResult(
            batch_id=batch_id,
            total_attempted=len(operations),
        )

        restricted_roots = get_restricted_system_roots()

        for op in operations:
            if op.id is None:
                continue

            try:
                current_dest = Path(op.destination_path)
                orig_path = Path(op.original_path)
            except Exception as e:
                result.failed_files.append(
                    FailedUndo(
                        operation_id=op.id,
                        moved_from_path=Path("unknown"),
                        target_path=Path("unknown"),
                        reason=f"Invalid stored path in database: {e}",
                    )
                )
                continue

            # Validate filenames for traversal, null bytes, reserved names
            try:
                validate_safe_filename(current_dest.name)
                validate_safe_filename(orig_path.name)
            except SafetyViolationError as e:
                result.failed_files.append(
                    FailedUndo(
                        operation_id=op.id,
                        moved_from_path=current_dest,
                        target_path=orig_path,
                        reason=f"Suspicious path in history record rejected: {e}",
                    )
                )
                continue

            # Validate that neither path is within a restricted system directory
            res_orig = orig_path.resolve(strict=False)
            res_dest = current_dest.resolve(strict=False)
            in_restricted = any(
                res_orig == r or r in res_orig.parents or res_dest == r or r in res_dest.parents
                for r in restricted_roots
            )
            if in_restricted:
                result.failed_files.append(
                    FailedUndo(
                        operation_id=op.id,
                        moved_from_path=current_dest,
                        target_path=orig_path,
                        reason="Restoration path violates system security: forbidden restricted directory.",
                    )
                )
                continue

            # Determine containment boundary
            effective_boundary = self._determine_effective_boundary(orig_path, current_dest)
            if effective_boundary is None:
                result.failed_files.append(
                    FailedUndo(
                        operation_id=op.id,
                        moved_from_path=current_dest,
                        target_path=orig_path,
                        reason="Restoration path rejected: cannot establish safe containment boundary.",
                    )
                )
                continue

            if not is_path_within_boundary(orig_path, effective_boundary) or not is_path_within_boundary(
                current_dest, effective_boundary
            ):
                result.failed_files.append(
                    FailedUndo(
                        operation_id=op.id,
                        moved_from_path=current_dest,
                        target_path=orig_path,
                        reason="Restoration path rejected: path escapes permitted boundary.",
                    )
                )
                continue

            # Check if file still exists at destination
            if not current_dest.exists() or not current_dest.is_file():
                result.failed_files.append(
                    FailedUndo(
                        operation_id=op.id,
                        moved_from_path=current_dest,
                        target_path=orig_path,
                        reason="File was deleted, renamed, or moved outside CleanDownloads.",
                    )
                )
                continue

            # Check for symlink / junction escaping boundary
            if is_symlink_escaping_boundary(current_dest, effective_boundary):
                result.failed_files.append(
                    FailedUndo(
                        operation_id=op.id,
                        moved_from_path=current_dest,
                        target_path=orig_path,
                        reason="Refusing undo: file is a symlink or junction escaping permitted directory.",
                    )
                )
                continue

            # Check if locked
            if is_file_locked(current_dest):
                result.failed_files.append(
                    FailedUndo(
                        operation_id=op.id,
                        moved_from_path=current_dest,
                        target_path=orig_path,
                        reason="File is currently open or locked by another process.",
                    )
                )
                continue

            # SHA-256 integrity check if hash was recorded
            if op.file_hash:
                try:
                    current_hash = compute_file_sha256(current_dest)
                    if current_hash.lower() != op.file_hash.lower():
                        result.failed_files.append(
                            FailedUndo(
                                operation_id=op.id,
                                moved_from_path=current_dest,
                                target_path=orig_path,
                                reason="File integrity verification failed: file content was modified after organization (hash mismatch).",
                            )
                        )
                        continue
                except Exception as exc:
                    result.failed_files.append(
                        FailedUndo(
                            operation_id=op.id,
                            moved_from_path=current_dest,
                            target_path=orig_path,
                            reason=f"Failed to verify file integrity: {exc}",
                        )
                    )
                    continue

            try:
                # Ensure destination parent exists
                orig_path.parent.mkdir(parents=True, exist_ok=True)

                # Move back collision-safely without overwriting existing files
                actual_restored_path, _ = atomic_collision_safe_move(
                    source=current_dest,
                    destination=orig_path,
                    boundary=effective_boundary,
                )

                # Update database record
                self.history_db.update_operation_status(
                    op_id=op.id,
                    status="UNDONE",
                )

                result.restored_files.append(
                    RestoredFile(
                        operation_id=op.id,
                        original_path=orig_path,
                        moved_from_path=current_dest,
                        actual_restored_path=actual_restored_path,
                    )
                )

            except Exception as e:
                result.failed_files.append(
                    FailedUndo(
                        operation_id=op.id,
                        moved_from_path=current_dest,
                        target_path=orig_path,
                        reason=f"Move failed: {e}",
                    )
                )

        # Update batch status
        if result.total_attempted > 0:
            if result.success_count == result.total_attempted:
                self.history_db.update_batch_status(batch_id=batch_id, status="UNDONE")
            elif result.success_count > 0:
                self.history_db.update_batch_status(batch_id=batch_id, status="PARTIALLY_UNDONE")

        return result
