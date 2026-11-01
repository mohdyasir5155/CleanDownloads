# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
