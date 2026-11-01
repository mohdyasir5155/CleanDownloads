# CleanDownloads Architecture & Safety Manifesto

CleanDownloads is engineered following SOLID principles, separation of concerns, and defensive Windows file system handling.

```
Downloads/ (Root)
   │
   ├── [Scanner] ──► Safety Filters (Incomplete downloads, locks, hidden/system, symlinks)
   │                      │
   │                      ▼
   │               [Classifier] ──► Matches extension & compound extensions (e.g. tar.gz)
   │                      │
   │                      ▼
   │               [Organizer]  ──► Collision-safe path generator (never overwrite)
   │                      │
   │                      ├── [shutil.move] ──► Atomic move to Documents/PDF, Images/PNG, etc.
   │                      │
   │                      └── [HistoryDB]   ──► SQLite transaction logging
   │
   └── [UndoEngine] ◄── Restores previous batch with collision check & audit status update
```

---

## Component Architecture

### 1. Safety Layer (`cleandownloads.safety`)
The foundation of the entire system. Enforces:
- Path boundary containment check (`is_path_within_boundary`). Prevents symlink escapes or relative path traversal (`..`).
- Active lock detection (`is_file_locked`). Tests for Windows file sharing violations (`ERROR_SHARING_VIOLATION 32`, `ERROR_LOCK_VIOLATION 33`) to prevent moving files being actively downloaded by browsers.
- Incomplete download detection (`is_incomplete_download`). Filters `.crdownload`, `.part`, `.tmp`, etc.
- Collision safe path generation (`generate_collision_safe_path`). Generates `filename (1).ext`, `filename (2).ext` if target exists.
- System file detection (`is_hidden_or_system_file`). Skips `desktop.ini`, `Thumbs.db`, `.DS_Store`, hidden attributes.

### 2. File Classification Engine (`cleandownloads.classifier`)
- Maps file extensions to categories and subfolders.
- Supports compound extensions (e.g. `archive.tar.gz` -> `Archives`).
- Fast lookup hash maps.
- Configurable fallback (`Other`).

### 3. Scanner (`cleandownloads.scanner`)
- **Root-only by default**: Never organizes inside subdirectories unless user explicitly enables `recursive: true`.
- Excludes category destination folders (`Documents`, `Images`, etc.) so previously organized files are not re-processed.
- Returns comprehensive `ScanResult` with ready files, category breakdown, and skipped files with reasons.

### 4. Organizer (`cleandownloads.organizer`)
- Supports full dry-run planning (`plan`).
- Executes safe file movements without data loss.
- Logs every operation in SQLite within an operation batch.
- Handles unexpected errors per-file without aborting remaining operations.

### 5. Undo Engine (`cleandownloads.undo`)
- Reverses operations by batch ID or latest run.
- Ensures original location is collision-safe before restoring.
- Verifies destination file existence and lock status.
- Updates SQLite status to `UNDONE`.

### 6. History Database (`cleandownloads.history`)
- SQLite database at `%LOCALAPPDATA%\CleanDownloads\history.db`.
- Tables: `batches` and `operations`.
- Indexed for fast queries.
- Zero network telemetry.

### 7. Scheduler (`cleandownloads.scheduler`)
- Non-admin integration with Windows Task Scheduler (`schtasks.exe`).
- Supports 30m, 1h, daily, and logon triggers.
- Provides enable, disable, remove, and status query commands.

### 8. CLI & Interactive Console (`cleandownloads.cli`)
- Interactive main menu with real-time stats and visual breakdown.
- Subcommands for terminal automation and scripts.
- UTF-8 Windows console safe formatting with ANSI colors.
