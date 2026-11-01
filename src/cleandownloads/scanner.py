"""Downloads folder scanner with intelligent safety filters and classification."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from cleandownloads.classifier import ClassificationResult, Classifier
from cleandownloads.config import AppConfig
from cleandownloads.safety import (
    is_file_locked,
    is_hidden_or_system_file,
    is_incomplete_download,
    is_symlink_escaping_boundary,
)


@dataclass
class ScannedFile:
    """A file identified and verified ready for organization."""
    path: Path
    filename: str
    size_bytes: int
    classification: ClassificationResult
    destination_relative_path: Path

    @property
    def extension(self) -> str:
        return self.classification.extension

    @property
    def category(self) -> str:
        return self.classification.category


@dataclass
class SkippedFile:
    """A file that was skipped during scanning with safety rationale."""
    path: Path
    reason: str  # 'incomplete_download', 'locked', 'hidden_system', 'symlink_escape', 'size_limit', 'ignored_extension'


@dataclass
class ScanResult:
    """Complete summary of a scan operation."""
    downloads_dir: Path
    ready_files: list[ScannedFile] = field(default_factory=list)
    skipped_files: list[SkippedFile] = field(default_factory=list)
    already_organized_count: int = 0
    total_scanned: int = 0

    @property
    def total_ready(self) -> int:
        return len(self.ready_files)

    @property
    def total_ready_bytes(self) -> int:
        return sum(f.size_bytes for f in self.ready_files)

    @property
    def category_breakdown(self) -> dict[str, int]:
        """Counts of ready files grouped by category."""
        counts: dict[str, int] = {}
        for f in self.ready_files:
            cat = f.category
            counts[cat] = counts.get(cat, 0) + 1
        return counts


class Scanner:
    """Scans the Downloads directory and categorizes eligible files safely."""

    def __init__(self, config: AppConfig, classifier: Classifier | None = None) -> None:
        self.config = config
        self.classifier = classifier or Classifier(config)

    def scan(self, target_dir: Path | None = None) -> ScanResult:
        """Scan target directory (defaults to config downloads_dir)."""
        downloads_dir = (target_dir or self.config.get_resolved_downloads_dir()).resolve()

        result = ScanResult(downloads_dir=downloads_dir)
        if not downloads_dir.exists() or not downloads_dir.is_dir():
            return result

        # Compute set of excluded folder names (case-insensitive)
        excluded_names = {d.lower() for d in self.config.excluded_directories}
        # Also exclude top-level folders used by rules
        for rule in self.config.rules:
            top_folder = rule.subfolder.split("/")[0].split("\\")[0]
            if top_folder:
                excluded_names.add(top_folder.lower())
        if self.config.default_fallback_folder:
            top_fallback = self.config.default_fallback_folder.split("/")[0].split("\\")[0]
            if top_fallback:
                excluded_names.add(top_fallback.lower())

        ignored_exts = {ext.lower().lstrip(".") for ext in self.config.ignored_extensions}

        # Count already organized files inside excluded/organized folders for status reporting
        self._count_already_organized(downloads_dir, excluded_names, result)

        # Scan files
        if self.config.recursive:
            self._scan_recursive(downloads_dir, downloads_dir, excluded_names, ignored_exts, result)
        else:
            self._scan_root_only(downloads_dir, ignored_exts, result)

        return result

    def _count_already_organized(
        self, downloads_dir: Path, excluded_names: set[str], result: ScanResult
    ) -> None:
        """Count existing files in organized category folders."""
        for folder_name in excluded_names:
            folder_path = downloads_dir / folder_name
            if folder_path.is_dir() and not folder_path.is_symlink():
                try:
                    for root, _, files in os.walk(folder_path):
                        for f in files:
                            # skip hidden/system files in count
                            if not f.startswith("."):
                                result.already_organized_count += 1
                except Exception:
                    pass

    def _scan_root_only(
        self,
        downloads_dir: Path,
        ignored_exts: set[str],
        result: ScanResult,
    ) -> None:
        """Scan only the immediate root of Downloads directory (default behavior)."""
        try:
            entries = list(downloads_dir.iterdir())
        except (PermissionError, OSError):
            return

        for item in entries:
            result.total_scanned += 1
            if not item.is_file():
                # Root subdirectories are ignored in root-only mode
                continue

            self._process_file_candidate(item, downloads_dir, ignored_exts, result)

    def _scan_recursive(
        self,
        current_dir: Path,
        boundary: Path,
        excluded_names: set[str],
        ignored_exts: set[str],
        result: ScanResult,
    ) -> None:
        """Scan recursively when explicitly enabled by user."""
        try:
            entries = list(current_dir.iterdir())
        except (PermissionError, OSError):
            return

        for item in entries:
            result.total_scanned += 1

            # Check symlink boundary safety
            if is_symlink_escaping_boundary(item, boundary):
                result.skipped_files.append(
                    SkippedFile(path=item, reason="symlink_escape")
                )
                continue

            if item.is_dir():
                if item.name.lower() in excluded_names:
                    result.skipped_files.append(
                        SkippedFile(path=item, reason="excluded_dir")
                    )
                    continue
                # Traverse sub-folder
                self._scan_recursive(item, boundary, excluded_names, ignored_exts, result)
            elif item.is_file():
                self._process_file_candidate(item, boundary, ignored_exts, result)

    def _process_file_candidate(
        self,
        file_path: Path,
        boundary: Path,
        ignored_exts: set[str],
        result: ScanResult,
    ) -> None:
        """Evaluate a single candidate file against all safety checks and filters."""
        # 1. Symlink escape check
        if is_symlink_escaping_boundary(file_path, boundary):
            result.skipped_files.append(
                SkippedFile(path=file_path, reason="symlink_escape")
            )
            return

        # 2. Hidden / system file check
        if is_hidden_or_system_file(file_path):
            result.skipped_files.append(
                SkippedFile(path=file_path, reason="hidden_system")
            )
            return

        # 3. Incomplete download check
        if is_incomplete_download(file_path):
            result.skipped_files.append(
                SkippedFile(path=file_path, reason="incomplete_download")
            )
            return

        # 4. Ignored extensions check
        classification = self.classifier.classify_path(file_path)
        if classification.extension in ignored_exts:
            result.skipped_files.append(
                SkippedFile(path=file_path, reason="ignored_extension")
            )
            return

        # 5. File size and age filters
        try:
            stat = file_path.stat()
            size = stat.st_size
            mtime = stat.st_mtime
        except OSError:
            result.skipped_files.append(
                SkippedFile(path=file_path, reason="stat_error")
            )
            return

        # Minimum file age check (skips files modified within min_file_age_seconds)
        if self.config.min_file_age_seconds > 0:
            if (time.time() - mtime) < self.config.min_file_age_seconds:
                result.skipped_files.append(
                    SkippedFile(path=file_path, reason="too_new")
                )
                return

        if self.config.min_file_size_bytes > 0 and size < self.config.min_file_size_bytes:
            result.skipped_files.append(
                SkippedFile(path=file_path, reason="size_limit")
            )
            return

        if (
            self.config.max_file_size_bytes is not None
            and size > self.config.max_file_size_bytes
        ):
            result.skipped_files.append(
                SkippedFile(path=file_path, reason="size_limit")
            )
            return

        # 6. Active file lock check
        if is_file_locked(file_path):
            result.skipped_files.append(
                SkippedFile(path=file_path, reason="locked")
            )
            return

        # Calculate planned relative destination
        dest_rel = classification.target_relative_path

        result.ready_files.append(
            ScannedFile(
                path=file_path,
                filename=file_path.name,
                size_bytes=size,
                classification=classification,
                destination_relative_path=dest_rel,
            )
        )
