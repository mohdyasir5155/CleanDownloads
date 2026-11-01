# Configuration Guide — CleanDownloads

CleanDownloads stores its configuration locally in JSON format at:
```text
%LOCALAPPDATA%\CleanDownloads\config.json
```

---

## Configuration Schema

```json
{
  "version": "1.0.0",
  "downloads_dir": null,
  "recursive": false,
  "min_file_age_seconds": 300,
  "min_file_size_bytes": 0,
  "max_file_size_bytes": null,
  "conflict_strategy": "rename",
  "ignored_extensions": [
    "crdownload",
    "part",
    "tmp",
    "download",
    "aria2",
    "opdownload",
    "!ut"
  ],
  "excluded_directories": [
    "Documents",
    "Images",
    "Videos",
    "Audio",
    "Archives",
    "Software",
    "Code",
    "Other",
    ".git",
    ".clean_history"
  ],
  "rules": [
    {
      "name": "PDF Documents",
      "category": "Documents",
      "subfolder": "Documents/PDF",
      "extensions": ["pdf"]
    },
    {
      "name": "Word Documents",
      "category": "Documents",
      "subfolder": "Documents/Word",
      "extensions": ["doc", "docx", "odt", "rtf"]
    }
  ],
  "default_fallback_folder": "Other"
}
```

---

## Settings Explained

| Key | Type | Description | Default |
|---|---|---|---|
| `downloads_dir` | string or null | Custom downloads directory path. If `null`, auto-detects user Downloads folder | `null` |
| `recursive` | boolean | Scan subfolders recursively (default is root-only) | `false` |
| `min_file_age_seconds` | integer | Minimum age in seconds before a file is organized (skips newer files) | `300` |
| `min_file_size_bytes` | integer | Minimum file size in bytes to organize | `0` |
| `max_file_size_bytes` | integer or null | Maximum file size in bytes to organize | `null` |
| `conflict_strategy` | string | Strategy for name collisions (`"rename"` appends `(1)`, `(2)`) | `"rename"` |
| `ignored_extensions` | list of string | File extensions to skip completely | Incomplete downloads |
| `excluded_directories` | list of string | Directory names under Downloads to never touch | Target folders, `.git` |
| `rules` | list of objects | Extension mapping rules with category and subfolder | Default rules |
| `default_fallback_folder`| string | Folder for unrecognized file extensions | `"Other"` |

---

## File Skip Reasons

When running `scan`, `preview`, or `organize`, CleanDownloads skips files that are unsafe or not ready to move. Common skip reasons shown in console summaries and JSON outputs include:

- `too_new`: File modified within `min_file_age_seconds` (default 300s). Can be overridden via `--min-age <seconds>`.
- `incomplete_download`: File has an in-progress download extension (e.g. `.crdownload`, `.part`, `.tmp`).
- `hidden_system`: File is a Windows system file or hidden item (e.g. `desktop.ini`, `Thumbs.db`).
- `already_organized`: File is located inside one of the managed category subfolders.
- `size_limit`: File size falls below `min_file_size_bytes` or exceeds `max_file_size_bytes`.
- `locked`: File is actively locked with exclusive access by another application.

---

## Adding Custom Rules

You can add custom categories and file extensions directly:

```json
{
  "name": "Photoshop Assets",
  "category": "Design",
  "subfolder": "Design/Photoshop",
  "extensions": ["psd", "psb"]
}
```

Or reset to defaults at any time:
```powershell
cleandownloads config --reset
```
