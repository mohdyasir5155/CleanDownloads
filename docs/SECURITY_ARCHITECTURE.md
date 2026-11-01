# CleanDownloads — Security Architecture & Invariants

## 1. Architectural Philosophy

CleanDownloads is architected around **defense-in-depth**, **least privilege**, and **fail-safe defaults**:
1. **A safe failure is always preferable to an unsafe successful operation.**
2. **Never permanently delete, truncate, or overwrite user files under any condition.**
3. **Never trust stored metadata, configuration values, or input filenames.**

---

## 2. Core Security Layers

```
+------------------------------------------------------------------------------------+
| Layer 6: Installation & Supply Chain                                               |
|  - HTTPS download enforcement                                                      |
|  - Mandatory SHA-256 checksum verification from checksums.txt (fails closed)       |
|  - GitHub build provenance attestation verification via gh CLI when available      |
|  - Opt-in Authenticode digital signature verification (-RequireSignature)         |
|  - Pre-extraction Zip Slip verification                                            |
|  - User-scope installation (never requests elevation)                              |
+------------------------------------------------------------------------------------+
                                         |
                                         v
+------------------------------------------------------------------------------------+
| Layer 5: IPC & Process Boundary                                                    |
|  - Rust native Tauri command validator with subcommand whitelist                   |
|  - Absolute path lookup for Windows system tools (%SystemRoot%\System32\schtasks)  |
|  - ANSI terminal escape sequence for screen clearing (no os.system("cls"))         |
+------------------------------------------------------------------------------------+
                                         |
                                         v
+------------------------------------------------------------------------------------+
| Layer 4: Configuration & Persistence Defense                                       |
|  - 512 KB DoS threshold limit on config files                                      |
|  - Strict regex validation for extensions and subfolder relative paths             |
|  - Atomic write pattern (write to tmp -> flush & fsync -> os.replace)              |
|  - Parameterized SQLite queries & automated schema migrations                      |
+------------------------------------------------------------------------------------+
                                         |
                                         v
+------------------------------------------------------------------------------------+
| Layer 3: Undo Engine & Integrity Verification                                      |
|  - Streaming 64 KB SHA-256 integrity calculation                                   |
|  - Verification of file integrity before restoration                               |
|  - Forbidden restoration to restricted Windows system directories                  |
+------------------------------------------------------------------------------------+
                                         |
                                         v
+------------------------------------------------------------------------------------+
| Layer 2: Boundary & Path Validation                                                |
|  - Canonical path resolution (Path.resolve())                                      |
|  - Reparse point and junction attribute checks (FILE_ATTRIBUTE_REPARSE_POINT 0x400)|
|  - Filename sanitization against Windows reserved devices (CON, NUL, AUX, etc.)   |
|  - NTFS Alternate Data Stream defense (rejection of colons in filenames)           |
+------------------------------------------------------------------------------------+
                                         |
                                         v
+------------------------------------------------------------------------------------+
| Layer 1: Kernel-Level Filesystem Guarantees                                        |
|  - Win32 MoveFileExW with MOVEFILE_COPY_ALLOWED (0x2)                              |
|  - Deliberate omission of MOVEFILE_REPLACE_EXISTING (0x1)                          |
|  - Non-destructive, bounded collision avoidance loop                              |
|  - Post-move size and destination verification                                     |
+------------------------------------------------------------------------------------+
```

---

## 3. Deep Dive into Critical Invariants

### 3.1 Kernel-Level Zero-Overwrite Guarantee
Standard file-move implementations in high-level languages often invoke POSIX `rename()` or Windows `MoveFileEx` with the replace flag. In Python on Windows, `shutil.move()` internally calls `os.replace()`, which will silently overwrite an existing destination file on the same volume.

CleanDownloads implements `atomic_collision_safe_move()` in `src/cleandownloads/safety.py`:
- Direct invocation of Win32 `MoveFileExW(source, destination, MOVEFILE_COPY_ALLOWED)`.
- The `MOVEFILE_REPLACE_EXISTING` flag (value `0x1`) is omitted.
- If the destination already exists, Windows kernel atomically aborts the call and returns `ERROR_ALREADY_EXISTS` (183) or `ERROR_FILE_EXISTS` (80).
- The algorithm catches these error codes and iterates to `filename (1).ext`, `filename (2).ext`, ensuring a collision cannot result in overwrite under race conditions.

### 3.2 Reparse Points & Directory Junctions
On NTFS, directory junctions and symlinks carry the reparse point attribute:
- Standard `Path.is_symlink()` in Python does NOT detect NTFS directory junctions created via `mklink /J`.
- CleanDownloads checks the Win32 file attribute flag `FILE_ATTRIBUTE_REPARSE_POINT` (`0x400`).
- If any folder or file is a reparse point whose canonical target escapes the user's Downloads directory, it is rejected before processing.

### 3.3 Path Traversal & Windows Device Name Defense
Incoming filenames are validated with `validate_safe_filename()`:
- Path separators (`/`, `\`) and traversal tokens (`..`) in basenames are rejected.
- Null bytes (`\0`) are rejected.
- NTFS Alternate Data Streams (`:`) are rejected.
- Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`) are rejected regardless of file extension (e.g. `CON.txt` or `nul.pdf`).

### 3.4 Cryptographic Undo Integrity
When a file is organized:
- CleanDownloads computes the SHA-256 hash in 64 KB chunks prior to moving.
- The hash is logged in `history.db` within the `operations` table.
- When an `undo` operation is requested:
  - The destination file's SHA-256 hash is recalculated.
  - If the hash differs (indicating the file was modified or replaced by external software), the undo operation is refused to prevent unintended regressions.
  - Distinguishes integrity verification from authentication.

### 3.5 Safe Subprocess Execution
- All subprocess invocations use explicit argument arrays (e.g. `[schtasks_path, "/Query", ...]`).
- `shell=False` is strictly enforced.
- System executables (`schtasks.exe`) are resolved to `%SystemRoot%\System32\schtasks.exe` to prevent PATH hijacking.
- Shell commands such as `os.system("cls")` have been completely eliminated in favor of ANSI terminal escape codes (`\033[2J\033[H`).

### 3.6 IPC Command Whitelist in Tauri
The desktop application frontend communicates with the Rust backend via IPC.
- `run_cleandownloads_cmd` validates the first token against an explicit allowlist: `["scan", "preview", "organize", "undo", "history", "status", "config"]`.
- Subsequent arguments are validated against an allowlist of permitted flags and numeric parameters.
- Shell metacharacters (`&`, `|`, `;`, `$`, `>`, `<`, `` ` ``, control characters) are strictly rejected.
- Content Security Policy (CSP) restricts script and connect destinations to `'self'` and local IPC.

---

## 4. Error Handling & Safe Failure Modes

CleanDownloads implements structured, non-fatal error handling across all modules:

| Failure Mode | Application Behavior |
|---|---|
| **Locked file during scan** | Logged as locked; automatically skipped; does not crash organization. |
| **Permission denied on file** | Recorded as `FAILED` in SQLite batch log; organization continues for remaining files. |
| **Corrupted config.json** | Falls back cleanly to secure built-in default rules; logs notice. |
| **Corrupted history.db** | Safe connection error handling; does not disrupt existing organized files. |
| **Interrupted organize / power loss** | Each move is individually committed; operations completed before interruption remain valid; incomplete batches are clearly identified in history. |
