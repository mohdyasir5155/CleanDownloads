# Security Policy & Defensive Model — CleanDownloads

CleanDownloads operates directly upon files in your personal `Downloads` directory. Because personal data integrity is the highest priority, CleanDownloads implements strict security, privacy, and data protection invariants.

---

## 1. Supported Versions

| Version | Supported | Security Maintenance |
|---|---|---|
| **1.0.x** | :white_check_mark: Yes | Active vulnerability patching, dependency audits, and security updates |
| **< 1.0.0** | :x: No | Unsupported |

---

## 2. Core Security & Data Integrity Invariants

### 1. Zero Deletion Invariant
CleanDownloads will **never** permanently delete user files. There is no code path or command that invokes unlinking or deleting user files.

### 2. Zero-Overwrite Invariant
Existing files are never overwritten. When destination names collide, CleanDownloads resolves collisions using Win32 `MoveFileExW` without the `MOVEFILE_REPLACE_EXISTING` flag on Windows (and atomic `os.link` / exclusive-create `O_CREAT | O_EXCL` on POSIX), atomically resolving conflicts via incremented numbering (e.g., `file (1).pdf`, `file (2).pdf`).

### 3. Zero Execution Invariant
CleanDownloads **never** executes, runs, or spawns processes for downloaded files. Downloaded files are treated purely as passive data bytes.

### 4. Canonical Path Boundary Enforcement
All source and destination paths are resolved to their canonical targets using `Path.resolve()`. Any path attempting directory traversal (`..`), absolute path escape, or UNC escape outside the permitted boundary is rejected immediately.

### 5. Windows Device Name & ADS Defense
Filenames matching Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`) and NTFS Alternate Data Streams (`:`) are strictly rejected.

### 6. Directory Junction & Reparse Point Containment
NTFS directory junctions (`FILE_ATTRIBUTE_REPARSE_POINT 0x400`) and symlinks are inspected; CleanDownloads refuses to traverse or move items through links escaping the allowed boundary.

### 7. Active & Incomplete Download Protection
Incomplete downloads (e.g., `.crdownload`, `.part`, `.tmp`, `.aria2`, `.opdownload`) and actively locked files (`ERROR_SHARING_VIOLATION` 32, `ERROR_LOCK_VIOLATION` 33) are detected and left untouched.

### 8. Hash-Verified Undo Accidental Modification Detection
Every organized file's SHA-256 hash is computed in 64 KB chunks and recorded in `history.db`. During `undo`, the file hash is re-verified before restoring to detect whether the file was altered or corrupted while organized. If modified, `undo` refuses to restore by default (overridable with `--force-modified` after confirmation). Note: The SHA-256 hash in `history.db` detects accidental file modification only; it is not tamper-proof against deliberate local modifications of the database.

### 9. 100% Local Privacy (Zero Telemetry)
All classification rules, metadata, and history are stored locally in `%LOCALAPPDATA%\CleanDownloads\history.db`. CleanDownloads sends **zero network requests** during normal operation and collects **zero telemetry or file metadata**.

### 10. Non-Privileged Execution
CleanDownloads runs entirely in standard user space without requiring administrator privileges or elevated tokens.

---

## 3. Security Documentation

For detailed analysis, architectures, and audit reports, refer to:
- [Threat Model](file:///docs/THREAT_MODEL.md) — Assets, trust boundaries, attacker profiles, and mitigation matrix.
- [Security Architecture](file:///docs/SECURITY_ARCHITECTURE.md) — Defense-in-depth layers and safety invariants.
- [Security Audit Report](file:///docs/SECURITY_AUDIT.md) — Comprehensive vulnerability audit, remediations, and test results.

---

## 4. Reporting a Vulnerability

If you discover a security vulnerability or safety flaw in CleanDownloads, please report it responsibly:

- **Email**: Send technical details to `security@cleandownloads.local` or open a confidential security advisory on GitHub.
- **Please Include**:
  - Description of the vulnerability.
  - Minimal proof of concept or reproduction steps.
  - Observed vs. expected behavior.
  - Affected platform / Windows version.
- **Response Commitment**: We will acknowledge receipt within 48 hours and work with you on a swift fix before any public disclosure.
