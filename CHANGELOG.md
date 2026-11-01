# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-11-01

### Fixed & Improved
- **Installer & Verification (Task 1)**:
  - Switched default verification path in `install.ps1` to mandatory SHA-256 checksums from `checksums.txt` (fails closed if missing or mismatched) plus GitHub build provenance attestation via `gh attestation verify` when `gh` CLI is available.
  - Made Authenticode signature verification opt-in via `-RequireSignature`.
  - Removed fallback that hardcoded version "1.0.0" and skipped checksums.
  - Fixed stale repository parameter documentation default to `mohdyasir5155/CleanDownloads`.
  - Updated README, INSTALLATION.md, and SECURITY_ARCHITECTURE.md to reflect verified installer behavior.
- **Filename Validation (Task 2)**:
  - `validate_safe_filename` in `safety.py` no longer rejects legitimate filenames with double dots (e.g., `report..final.pdf`, `v1.2..3.zip`).
  - Precisely rejects: empty names, `.` / `..`, path separators, null bytes, `:`, `<>"|?*`, Windows reserved device names (`CON`, `NUL`, etc.), and trailing dots/spaces.
- **Concurrency & SQLite Robustness (Task 3)**:
  - Added single-instance process lock for `organize` and `undo` via `SingleInstanceLock` in `safety.py` (`msvcrt.locking` on Windows, `fcntl.flock` on POSIX).
  - Concurrent manual runs exit with code 1; scheduled background runs exit quietly with code 0.
  - Configured SQLite connection in `history.py` with `timeout=30`, `PRAGMA journal_mode=WAL`, and `PRAGMA busy_timeout=30000`.
- **Minimum File Age Filter (Task 4)**:
  - Added `min_file_age_seconds` configuration to `AppConfig` (default 300 seconds).
  - Skips files newer than the threshold with reason `too_new`.
  - Added `--min-age` CLI argument to `scan`, `preview`, and `organize`.
  - Updated documentation and default rules configuration.
- **Scheduler Locale Independence (Task 5)**:
  - Replaced localized text parsing of `schtasks /Query` with XML parsing via `xml.etree.ElementTree` (`schtasks /Query /TN <name> /XML`).
  - Created scheduled tasks run hidden and only when the user is logged on.
- **Hashing Cost & Undo Override (Task 6)**:
  - Eliminated redundant file reads by combining sharing lock inspection and SHA-256 hashing into a single open (`check_lock_and_hash`).
  - Added `undo --force-modified` with explicit confirmation prompt or `-y`/`--yes` to restore altered files, recording `OVERRIDE_MODIFIED` in history.
- **Honest Security Claims & POSIX Parity (Task 7)**:
  - Implemented atomic no-overwrite move on POSIX (`os.link` then `os.unlink`, with `O_CREAT | O_EXCL` cross-filesystem fallback).
  - Revised documentation across README, SECURITY.md, and docs/ to clarify that SQLite SHA-256 detects accidental modification rather than acting as tamper-proof against local database edits.
  - Removed "kernel-level" and "cryptographic undo" phrasing and softened "guaranteed" language around the 14 invariants.
  - Updated `pyproject.toml` classifier to "4 - Beta".
  - Replaced static test badge with live GitHub Actions CI badge.
- **Test Hygiene & CI Consolidation (Task 8)**:
  - Fixed Linux test failures in `scanner.py` (case-insensitive folder lookup via directory listing) and `test_security_attacks.py` (platform-aware system path validation).
  - Consolidated `ci.yml` and `tests.yml` into a unified cross-platform workflow testing on `windows-latest` and `ubuntu-latest` across Python 3.11, 3.12, and 3.13.
  - Added `timeout-minutes` to every job, pinned all third-party actions by full commit SHA with version comments, and set `persist-credentials: false`.
  - Added `ruff` and `bandit` to `dev` extra in `pyproject.toml`.
  - Added JSON contract tests (`tests/test_contracts.py`) covering `scan`, `preview`, `organize`, `undo`, `history`, and `status` matching `desktop/src/types.ts`.
  - Replaced redundant exception tuple in `organizer.py` with `except Exception` and clear rationale comment.

## [1.0.0] - 2026-11-01

### Added
- **Core Organization Engine**:
  - Out-of-the-box rule classification for 13+ standard categories (Documents, Images, Videos, Audio, Archives, Software, Code, Spreadsheets, Presentations, E-Books, Fonts, System, and Fallback).
  - Multi-part file extension parsing (e.g., `.tar.gz`, `.tar.bz2`, `.user.js`).
  - Safe file collision resolution with automatic sequence numbering `file (1).pdf`.
  - Kernel-level overwrite prevention using Windows `MoveFileExW` without `MOVEFILE_REPLACE_EXISTING`.
- **Safety Invariants & Defensive Model**:
  - Incomplete download detection (`.crdownload`, `.part`, `.tmp`, `.download`, `.aria2`, `.opdownload`).
  - Active file lock detection using Win32 `CreateFileW` with `GENERIC_READ | GENERIC_WRITE` and exclusive sharing test.
  - Strict path traversal (`..`), UNC path escape, and device name validation (`CON`, `PRN`, `AUX`, `NUL`, etc.).
  - NTFS Alternate Data Stream (ADS) filtering (`:`).
  - NTFS directory junction and symlink containment check.
- **Rollback & History System**:
  - Atomic transaction recording in local SQLite database (`%LOCALAPPDATA%\CleanDownloads\history.db`).
  - SHA-256 pre-move integrity hashing (64 KB chunked streaming).
  - 1-click batch undo command (`cleandownloads undo`) with pre-restore hash verification.
  - Automatic corrupt database archiving and seamless recovery.
- **CLI Commands**:
  - `cleandownloads scan`: Non-mutating analysis of Downloads directory.
  - `cleandownloads preview`: Dry-run before/after path preview.
  - `cleandownloads organize`: Execute file movements (`--dry-run` flag supported).
  - `cleandownloads undo`: Restore organized files to original locations.
  - `cleandownloads history`: View past organization runs and file operations.
  - `cleandownloads status`: System environment, folder paths, and scheduler overview.
  - `cleandownloads config`: View, customize, or reset classification rules.
  - `cleandownloads schedule`: Automated background task scheduling via Windows Task Scheduler (30m, hourly, daily, logon).
  - `cleandownloads uninstall`: Clean uninstallation instructions and trigger.
- **Packaging & Distribution**:
  - Standalone x64 Windows executable built with PyInstaller (`dist/cleandownloads.exe`).
  - Windows Setup Wizard installer built with Inno Setup 6 (`CleanDownloads-Setup-1.0.0.exe`).
  - Authenticode digital signature integration and verification.
  - One-line PowerShell bootstrapper (`install.ps1`).
  - Microsoft WinGet manifest package (`CleanDownloads.CleanDownloads`).
  - Clean uninstallation script (`uninstall.ps1`).
- **Security & Quality Assurance**:
  - 50 automated pytest unit and security regression tests passing with 100% success rate.
  - Windows filesystem attack test suite (`test_security_attacks.py`).
  - DevSecOps CI workflows for Ruff linting, Bandit SAST scanning, and pip-audit.
