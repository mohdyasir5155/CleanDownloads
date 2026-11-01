# CleanDownloads — Threat Model & Security Posture

## 1. Executive Summary

CleanDownloads is a specialized Windows utility engineered to organize users' `Downloads` directories automatically. Because it operates directly upon personal, potentially untrusted files (files recently downloaded from arbitrary internet locations), security and filesystem integrity are critical requirements.

This document formally establishes the application's **Assets**, **Trust Boundaries**, **Threat Actors**, **Attack Surfaces**, and **Defensive Mitigations**.

---

## 2. Assets & Security Objectives

| Asset | Sensitivity | Objective |
|---|---|---|
| **User Personal Files** | Critical | Must never be deleted, truncated, corrupted, or overwritten. |
| **Filesystem Integrity** | Critical | File operations must remain strictly bounded inside the target directory. |
| **System Configuration & PATH** | High | Installation, scheduling, and execution must never alter global system settings or require administrative elevation. |
| **History & Undo Log** | High | SQLite logs must remain consistent, transactional, and protected against path manipulation. |
| **Privacy & Metadata** | High | File contents and names must never be transmitted externally (100% local operation). |

---

## 3. Trust Boundaries

```
+--------------------------------------------------------------------------+
|                        UNTRUSTED EXTERNAL WORLD                          |
|  - Malicious files downloaded from web (zip slip, ADS, special characters)|
|  - Third-party NPM packages / Webview DOM                                 |
+--------------------------------------------------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------------+
|                      TRUST BOUNDARY 1: Webview / IPC                     |
|  - Tauri frontend (HTML/CSS/TS) <---> Rust IPC Handler                   |
|  - Mitigation: Subcommand allowlist, strict argument token filtering    |
+--------------------------------------------------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------------+
|                  TRUST BOUNDARY 2: Core Python Engine                    |
|  - CLI & Scheduler (`cleandownloads`)                                    |
|  - Scanner, Classifier, Organizer, Undo Engine                           |
|  - Mitigation: Canonical path checking, DoS config limits, Win32 calls   |
+--------------------------------------------------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------------+
|                 TRUST BOUNDARY 3: Windows Filesystem (NTFS)              |
|  - User Downloads Folder                                                 |
|  - LocalAppData (`%LOCALAPPDATA%\CleanDownloads`)                        |
|  - Mitigation: MoveFileExW (no overwrite), Reparse Point filtering       |
+--------------------------------------------------------------------------+
```

### Boundary 1: Untrusted Download Inflow
Files arriving in `Downloads` originate from arbitrary web endpoints. They may have:
- Malicious filenames designed to exploit path traversal (`../../`).
- NTFS Alternate Data Streams (`file.pdf:hidden.exe`).
- Windows reserved device names (`CON.pdf`, `NUL`, `AUX`, `COM1`).
- Active downloads in progress (`.crdownload`, `.part`).

### Boundary 2: Webview Frontend to Native Backend
The optional desktop UI uses Tauri. If an XSS vulnerability exists in frontend dependencies, the frontend must not be permitted to execute arbitrary shell commands.

### Boundary 3: Configuration & History Store
`config.json` and `history.db` reside in `%LOCALAPPDATA%\CleanDownloads`. Neither can be trusted unconditionally when read; both must undergo schema and boundary validation before use.

---

## 4. Threat Actors & Attacker Profiles

1. **Remote Adversary (Drive-by Web Download)**:
   - *Goal*: Craft a file that, when organized by CleanDownloads, executes arbitrary code, overwrites sensitive files, or escapes the directory.
   - *Capabilities*: Can deliver files with arbitrary names, extensions, or attributes into the user's `Downloads` folder.

2. **Compromised Frontend Dependency (Supply-Chain Threat)**:
   - *Goal*: Exploit the IPC bridge between the Webview and native desktop application to launch shell commands.
   - *Capabilities*: Can send arbitrary IPC messages to the Tauri native backend.

3. **Local Unprivileged Malicious Script**:
   - *Goal*: Tamper with local configuration or database to trick CleanDownloads into moving system files on the next run or during `undo`.
   - *Capabilities*: Can write to files within the user's profile.

---

## 5. Threat Analysis & Mitigation Matrix

| Threat ID | Threat Scenario | Potential Impact | Invariant / Mitigation Strategy | Verification Test |
|---|---|---|---|---|
| **T-01** | Path Traversal via Filename (`../../evil.txt`) | Arbitrary filesystem write / escape | Canonical `resolve()` boundary check; explicit rejection of `/`, `\`, and `..` in basenames. | `test_path_traversal_dot_dot_rejected` |
| **T-02** | NTFS Alternate Data Streams (`doc.pdf:stream.exe`) | Hidden executable code injection | Basename validation strictly rejects `:` colons. | `test_ntfs_alternate_data_stream_rejected` |
| **T-03** | Windows Reserved Device Names (`CON`, `NUL`, `AUX`) | OS freeze, blue-screen, or filesystem error | `validate_safe_filename` checks base stem against `WINDOWS_RESERVED_NAMES`. | `test_windows_reserved_device_names_rejected` |
| **T-04** | Accidental File Overwrite | Permanent loss of user data | Atomic collision-safe move loop using Win32 `MoveFileExW` without `MOVEFILE_REPLACE_EXISTING` on Windows (and atomic link/exclusive-create on POSIX). | `test_zero_overwrite_guarantee` |
| **T-05** | Symlink / Junction Boundary Escape | Moving files outside the allowed downloads folder | `is_reparse_point_or_symlink` checks for `FILE_ATTRIBUTE_REPARSE_POINT (0x400)` and resolves canonical targets. | `test_validate_move_paths_raises_on_escape` |
| **T-06** | Incomplete Download Corruption | Corrupting files actively written by browsers | Extensions like `.crdownload`, `.part`, `.tmp` are ignored; `is_file_locked()` checks sharing violations. | `test_incomplete_download_extensions_rejected` |
| **T-07** | Configuration Denial of Service (DoS) | Memory exhaustion / CPU hang | Maximum config size capped at 512 KB; max 200 rules; max 4 folder depth. | `test_oversized_config_file_rejected` |
| **T-08** | SQL Injection via Filenames / Categories | SQLite database corruption or tampering | 100% parameterized queries with SQLite parameters (`?`); zero string interpolation. | `test_sqlite_sql_injection_payload_in_filename` |
| **T-09** | Undo Path Hijacking via Modified History | Moving files into Windows / System32 on undo | Undo engine validates both source and destination against boundary and explicit restricted system roots. | `test_undo_refuses_corrupted_system_paths_in_db` |
| **T-10** | Accidental Modified File Restoration via Undo | Restoring a file that was modified or corrupted after organization | SHA-256 integrity checksum verification before restoring files (detects accidental modification; not tamper-proof against deliberate SQLite DB edits; overridable via `--force-modified` with confirmation). | `test_undo_refuses_restoring_modified_file` |
| **T-11** | Command Injection in Task Scheduler | Arbitrary command execution on scheduled trigger | Strict alphanumeric regex on `task_name`; absolute path resolution of `schtasks.exe`; `shell=False`. | `test_scheduler_rejects_malicious_task_name` |
| **T-12** | Tauri IPC Command Injection | Arbitrary command execution from webview | Rust backend enforces strict allowlist of subcommands (`scan`, `organize`, etc.) and permitted flag arguments. | `main.rs` Rust validation |
| **T-13** | Installer Zip Slip Attack | Overwriting arbitrary files during install | `install.ps1` checks all zip entries for `..`, `:`, and leading slashes before extracting. | `install.ps1` archive verification |

---

## 6. Privacy & Data Minimization

CleanDownloads adheres to strict privacy and data minimization principles:
- **No Telemetry**: No tracking, phone-home, or remote metrics.
- **No Cloud Dependency**: All classification, scanning, and history tracking are 100% local.
- **No Content Scanning**: Classification is performed exclusively based on file extensions and metadata. File contents are never parsed for classification purposes.
- **Data Minimization in History**: `history.db` only retains file paths, sizes, categories, timestamps, and SHA-256 hashes needed for undo operations.
