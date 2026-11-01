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
| `min_file_size_bytes` | integer | Minimum file size in bytes to organize | `0` |
| `max_file_size_bytes` | integer or null | Maximum file size in bytes to organize | `null` |
| `conflict_strategy` | string | Strategy for name collisions (`"rename"` appends `(1)`, `(2)`) | `"rename"` |
| `ignored_extensions` | list of string | File extensions to skip completely | Incomplete downloads |
| `excluded_directories` | list of string | Directory names under Downloads to never touch | Target folders, `.git` |
| `rules` | list of objects | Extension mapping rules with category and subfolder | Default rules |
| `default_fallback_folder`| string | Folder for unrecognized file extensions | `"Other"` |

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
