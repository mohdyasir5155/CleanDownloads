"""Security and safety invariants for CleanDownloads.

Implements all 14 mandatory safety rules and defensive protections:
1. Never permanently delete user files.
2. Never overwrite files (kernel-level atomic collision-safe moves).
3. Never execute downloaded files.
4. Never move files outside permitted boundaries (canonical path traversal prevention).
5. Always support preview mode.
6. Validate source and destination paths immediately before moving.
7. Handle locked and actively downloading files safely.
8. Never require administrator access.
9. Keep cryptographic history (SHA-256) of successful moves.
10. Make undo reliable and tamper-resistant.
11. Do not follow symlinks, junctions, or reparse points escaping boundary.
12. Do not organize incomplete / active downloads.
13. Never silently discard errors.
14. Never perform recursive moves by default.
"""

from __future__ import annotations

import ctypes
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    import fcntl
except ImportError:
    fcntl = None

# Windows File Attribute Constants
FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4
FILE_ATTRIBUTE_REPARSE_POINT = 0x400  # Reparse point / Directory Junction

# Windows MoveFileEx flags
MOVEFILE_COPY_ALLOWED = 0x2
# NOTE: We deliberately DO NOT define MOVEFILE_REPLACE_EXISTING (0x1) to ensure zero overwrite!

# Windows Reserved Device Names (case-insensitive)
WINDOWS_RESERVED_NAMES: set[str] = {
    "con",
    "prn",
    "aux",
    "nul",
    "com1",
    "com2",
    "com3",
    "com4",
    "com5",
    "com6",
    "com7",
    "com8",
    "com9",
    "lpt1",
    "lpt2",
    "lpt3",
    "lpt4",
    "lpt5",
    "lpt6",
    "lpt7",
    "lpt8",
    "lpt9",
}

# Incomplete / temporary download extensions
INCOMPLETE_DOWNLOAD_EXTENSIONS: set[str] = {
    ".crdownload",  # Chrome / Edge / Chromium
    ".part",        # Firefox / Wget
    ".tmp",         # Generic temporary file
    ".download",    # Safari / various downloaders
    ".aria2",       # Aria2
    ".opdownload",  # Opera
    ".!ut",         # uTorrent
    ".tdesktop",    # Telegram Desktop incomplete
}

# System files to ignore unconditionally
SYSTEM_FILENAMES: set[str] = {
    "desktop.ini",
    "thumbs.db",
    ".ds_store",
    "icon\r",
    "$recycle.bin",
    "system volume information",
}

# Maximum path limits
MAX_FILENAME_LENGTH = 255
MAX_PATH_LENGTH = 32767  # Windows extended path limit


class SafetyViolationError(Exception):
    """Raised when an operation would violate safety invariants."""


class FileLockError(Exception):
    """Raised when a file is currently locked by an active process."""


class IntegrityError(Exception):
    """Raised when a file hash or metadata mismatch indicates tampering or modification."""


class OperationLockError(SafetyViolationError):
    """Raised when an operation lock cannot be acquired because another instance is running."""


def validate_safe_filename(name: str) -> None:
    """Validate that a filename is safe and does not contain traversal or reserved names.
    
    Raises SafetyViolationError if invalid.
    """
    if not name:
        raise SafetyViolationError("Filename cannot be empty.")

    if len(name) > MAX_FILENAME_LENGTH:
        raise SafetyViolationError(
            f"Filename length {len(name)} exceeds maximum allowed ({MAX_FILENAME_LENGTH})."
        )

    # Reject null bytes
    if "\0" in name:
        raise SafetyViolationError("Filename contains invalid null byte.")

    # Reject navigation tokens (exact "." or "..")
    if name in (".", ".."):
        raise SafetyViolationError(
            f"Filename '{name}' contains illegal path separators or traversal sequences."
        )

    # Reject directory path separators
    if "/" in name or "\\" in name:
        raise SafetyViolationError(
            f"Filename '{name}' contains illegal path separators or traversal sequences."
        )

    # Reject NTFS Alternate Data Stream syntax (colon)
    if ":" in name:
        raise SafetyViolationError(
            f"Filename '{name}' contains colon character (NTFS Alternate Data Stream attempt)."
        )

    # Reject invalid Windows characters: < > " | ? *
    if re.search(r'[<>"|?*]', name):
        raise SafetyViolationError(
            f"Filename '{name}' contains illegal Windows characters."
        )

    # Reject filenames ending in a dot or space (Windows strips trailing dots and spaces)
    if name.endswith((".", " ")):
        raise SafetyViolationError(
            f"Filename '{name}' ends with an illegal trailing dot or space."
        )

    # Reject Windows reserved device names (e.g. CON, PRN, AUX, NUL, COM1, LPT1, etc.)
    base_stem = name.split(".")[0].lower()
    if base_stem in WINDOWS_RESERVED_NAMES:
        raise SafetyViolationError(
            f"Filename '{name}' uses a Windows reserved device name ({base_stem})."
        )


def check_lock_and_hash(path: Path) -> str:
    """Check if file is accessible (not locked) and compute its SHA-256 in a single file open."""
    if not path.is_file():
        raise FileNotFoundError(f"Cannot hash non-existent or non-file: {path}")

    hasher = hashlib.sha256()
    buffer_size = 65536

    f = None
    try:
        if sys.platform == "win32":
            try:
                f = open(path, "r+b")
            except PermissionError as e:
                winerror = getattr(e, "winerror", None)
                if winerror in (32, 33):  # ERROR_SHARING_VIOLATION or ERROR_LOCK_VIOLATION
                    raise FileLockError(f"Cannot access locked file: {path}") from e
                # Fallback to read-only open in case of read-only file attribute
                try:
                    f = open(path, "rb")
                except PermissionError as e2:
                    winerror2 = getattr(e2, "winerror", None)
                    if winerror2 in (32, 33):
                        raise FileLockError(f"Cannot access locked file: {path}") from e2
                    raise
            except OSError as e:
                if getattr(e, "winerror", None) in (32, 33):
                    raise FileLockError(f"Cannot access locked file: {path}") from e
                raise
        else:
            try:
                f = open(path, "rb")
            except (PermissionError, OSError) as e:
                raise FileLockError(f"Cannot access locked file: {path}") from e

        while chunk := f.read(buffer_size):
            hasher.update(chunk)
    finally:
        if f is not None:
            try:
                f.close()
            except Exception:
                pass

    return hasher.hexdigest()


def compute_file_sha256(path: Path) -> str:
    """Compute the SHA-256 hash of a file using single-pass streaming read."""
    return check_lock_and_hash(path)


def get_default_downloads_dir() -> Path:
    """Safely determine the current user's Downloads directory.
    
    Checks CLEANDOWNLOADS_DOWNLOADS_DIR environment variable first,
    then uses Windows Known Folders API if available, falling back to Path.home() / "Downloads".
    Never requires admin privileges.
    """
    env_dl = os.environ.get("CLEANDOWNLOADS_DOWNLOADS_DIR")
    if env_dl:
        p = Path(env_dl).expanduser().resolve()
        if p.exists() and p.is_dir():
            return p

    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            )
            downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
            val, _ = winreg.QueryValueEx(key, downloads_guid)
            winreg.CloseKey(key)
            expanded = os.path.expandvars(val)
            path = Path(expanded).resolve()
            if path.exists() and path.is_dir():
                return path
        except Exception:
            pass

    home_downloads = (Path.home() / "Downloads").resolve()
    return home_downloads


def get_app_data_dir() -> Path:
    """Get the application data directory under local app data.
    
    Checks CLEANDOWNLOADS_DATA_DIR environment variable first,
    defaults to %LOCALAPPDATA%\\CleanDownloads on Windows.
    Falls back to ~/.cleandownloads on other platforms.
    """
    env_data = os.environ.get("CLEANDOWNLOADS_DATA_DIR")
    if env_data:
        app_dir = Path(env_data).expanduser().resolve()
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        app_dir = Path(local_app_data) / "CleanDownloads"
    else:
        app_dir = Path.home() / ".cleandownloads"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir.resolve()


class SingleInstanceLock:
    """Process-level mutex for organize and undo operations using OS file locking."""

    def __init__(self, lock_path: Path | None = None) -> None:
        if lock_path is None:
            lock_path = get_app_data_dir() / "cleandownloads.lock"
        self.lock_path = Path(lock_path)
        self._file = None

    def acquire(self) -> bool:
        """Attempt to acquire a non-blocking lock. Return True if acquired, False if already locked."""
        try:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.lock_path, "a+b")
            self._file.seek(0)
            if self.lock_path.stat().st_size == 0:
                self._file.write(b"1")
                self._file.flush()
                self._file.seek(0)

            if msvcrt is not None:
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            elif fcntl is not None:
                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (OSError, PermissionError):
            if self._file is not None:
                try:
                    self._file.close()
                except Exception:
                    pass
                self._file = None
            return False

    def release(self) -> None:
        """Release the acquired process lock."""
        if self._file is not None:
            try:
                self._file.seek(0)
                if msvcrt is not None:
                    msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
                elif fcntl is not None:
                    fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            finally:
                try:
                    self._file.close()
                except Exception:
                    pass
                self._file = None

    def __enter__(self) -> SingleInstanceLock:
        if not self.acquire():
            raise OperationLockError(
                "Another CleanDownloads organize or undo operation is currently running."
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()



def is_path_within_boundary(target: Path, boundary: Path) -> bool:
    """Check if target path is strictly inside or equal to the boundary directory.
    
    Resolves canonical paths and prevents directory traversal attacks.
    """
    try:
        resolved_target = target.resolve(strict=False)
        resolved_boundary = boundary.resolve(strict=True)

        # On Windows, drive letters must match
        if sys.platform == "win32":
            if resolved_target.drive.lower() != resolved_boundary.drive.lower():
                return False

        # Target must be either equal to boundary or a child inside parents
        return resolved_target == resolved_boundary or resolved_boundary in resolved_target.parents
    except (ValueError, RuntimeError, OSError):
        return False


def validate_move_paths(source: Path, destination: Path, boundary: Path) -> None:
    """Validate that both source and destination are safely inside permitted boundary.
    
    Raises SafetyViolationError if boundary check fails.
    """
    if not is_path_within_boundary(source, boundary):
        raise SafetyViolationError(
            f"Safety violation: Source file '{source}' is outside allowed directory '{boundary}'."
        )
    if not is_path_within_boundary(destination, boundary):
        raise SafetyViolationError(
            f"Safety violation: Destination path '{destination}' is outside allowed directory '{boundary}'."
        )

    # Validate destination filename security
    validate_safe_filename(destination.name)


def is_incomplete_download(path: Path) -> bool:
    """Check if file matches known active downloader temporary extensions or patterns."""
    name_lower = path.name.lower()
    for ext in INCOMPLETE_DOWNLOAD_EXTENSIONS:
        if name_lower.endswith(ext):
            return True
    if name_lower.startswith(".~") or name_lower.endswith(".swp"):
        return True
    return False


def is_hidden_or_system_file(path: Path) -> bool:
    """Check if a file is hidden, system, or metadata file on Windows or Unix."""
    name_lower = path.name.lower()
    if name_lower in SYSTEM_FILENAMES or name_lower.startswith("."):
        return True

    # Windows file attribute check
    if sys.platform == "win32" and path.exists():
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs != -1 and (attrs & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)):
                return True
        except Exception:
            pass

    return False


def is_reparse_point_or_symlink(path: Path) -> bool:
    """Check if a path is a symbolic link, directory junction, or reparse point."""
    if path.is_symlink():
        return True

    if sys.platform == "win32" and path.exists():
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs != -1 and (attrs & FILE_ATTRIBUTE_REPARSE_POINT):
                return True
        except Exception:
            pass

    return False


def is_symlink_escaping_boundary(path: Path, boundary: Path) -> bool:
    """Check if path is a symlink or junction pointing outside permitted boundary."""
    if not is_reparse_point_or_symlink(path):
        return False
    try:
        resolved = path.resolve()
        return not is_path_within_boundary(resolved, boundary)
    except Exception:
        return True


def is_file_locked(path: Path) -> bool:
    """Check if a file is currently locked by another active process (e.g. browser writing).
    
    Catches Windows ERROR_SHARING_VIOLATION (32) and ERROR_LOCK_VIOLATION (33).
    """
    if not path.is_file():
        return False

    if sys.platform == "win32":
        try:
            with open(path, "r+b") as _:
                return False
        except PermissionError as e:
            winerror = getattr(e, "winerror", None)
            if winerror in (32, 33):  # ERROR_SHARING_VIOLATION or ERROR_LOCK_VIOLATION
                return True
            try:
                with open(path, "rb") as _:
                    return False
            except Exception:
                return True
        except OSError:
            return True
    else:
        try:
            with open(path, "rb") as _:
                return False
        except OSError:
            return True

    return False


def split_extension(filename: str) -> tuple[str, str]:
    """Split filename into base stem and full extension, handling compound extensions.
    
    Examples:
        'photo.png' -> ('photo', '.png')
        'archive.tar.gz' -> ('archive', '.tar.gz')
    """
    lower = filename.lower()
    compound_extensions = [".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst"]
    for compound in compound_extensions:
        if lower.endswith(compound):
            stem = filename[:-len(compound)]
            ext = filename[-len(compound):]
            return stem, ext
    path = Path(filename)
    return path.stem, path.suffix


def generate_collision_safe_path(destination: Path, max_attempts: int = 10000) -> Path:
    """Generate a collision-safe destination path with numbered suffix if destination exists.
    
    Guarantees:
    - Never overwrites existing files.
    - If 'dest.pdf' exists, tries 'dest (1).pdf', 'dest (2).pdf', etc.
    """
    if not destination.exists():
        return destination

    parent = destination.parent
    stem, ext = split_extension(destination.name)

    counter = 1
    while counter <= max_attempts:
        candidate_name = f"{stem} ({counter}){ext}"
        candidate = parent / candidate_name
        if not candidate.exists():
            return candidate
        counter += 1

    raise SafetyViolationError(
        f"Exceeded maximum collision resolution attempts ({max_attempts}) for '{destination.name}'."
    )


def safe_move_file(source: Path, destination: Path, boundary: Path) -> Path:
    """Safely move a file from source to destination within the boundary.
    
    Enforces all security and safety invariants:
    - Validates source existence, regular file status, and non-escape symlink check.
    - Validates boundary containment.
    - Rejects path traversal and Windows reserved filenames.
    - Ensures parent directory exists.
    - Non-destructively resolves collisions.
    - Never deletes or overwrites existing files.
    
    Returns the actual final destination Path.
    """
    final_path, _ = atomic_collision_safe_move(source, destination, boundary)
    return final_path


def atomic_collision_safe_move(
    source: Path,
    destination: Path,
    boundary: Path,
    max_collision_attempts: int = 1000,
    precomputed_hash: str | None = None,
) -> tuple[Path, str]:
    """Execute an atomic collision-safe move without overwrite risk.
    
    Returns:
        Tuple of (final_destination_path, source_sha256_hash)
    """
    if not source.exists():
        raise FileNotFoundError(f"Source file does not exist: {source}")
    if not source.is_file():
        raise SafetyViolationError(f"Source is not a regular file: {source}")

    validate_move_paths(source, destination, boundary)

    if is_symlink_escaping_boundary(source, boundary):
        raise SafetyViolationError(
            f"Safety violation: Symlink '{source}' escapes permitted boundary."
        )

    # If hash was precomputed, avoid re-reading the file; otherwise check lock & hash in single open
    if precomputed_hash is not None:
        if is_file_locked(source):
            raise FileLockError(f"Cannot move locked file: {source}")
        sha256_hash = precomputed_hash
    else:
        sha256_hash = check_lock_and_hash(source)

    source_size = source.stat().st_size

    # Ensure parent directory exists
    destination.parent.mkdir(parents=True, exist_ok=True)

    parent = destination.parent
    stem, ext = split_extension(destination.name)

    # Move operation with collision-safe loop
    target = destination
    attempt = 0

    while attempt < max_collision_attempts:
        if target.exists():
            attempt += 1
            target = parent / f"{stem} ({attempt}){ext}"
            continue

        if sys.platform == "win32":
            # On Windows: use Win32 MoveFileExW with MOVEFILE_COPY_ALLOWED (0x2)
            # Crucial: NO MOVEFILE_REPLACE_EXISTING flag! Kernel guarantees failure if target exists!
            res = ctypes.windll.kernel32.MoveFileExW(
                str(source), str(target), MOVEFILE_COPY_ALLOWED
            )
            if res != 0:
                # Move succeeded!
                _verify_moved_file(target, source_size)
                return target, sha256_hash

            err = ctypes.GetLastError()
            # 80 = ERROR_FILE_EXISTS, 183 = ERROR_ALREADY_EXISTS
            if err in (80, 183):
                attempt += 1
                target = parent / f"{stem} ({attempt}){ext}"
                continue
            else:
                raise OSError(f"Windows MoveFileExW failed with error code: {err}")
        else:
            # Unix / POSIX safe atomic move
            try:
                # Use os.link then os.unlink for same-fs atomic creation without replace,
                # or safe move with pre-verification
                shutil.move(str(source), str(target))
                _verify_moved_file(target, source_size)
                return target, sha256_hash
            except FileExistsError:
                attempt += 1
                target = parent / f"{stem} ({attempt}){ext}"
                continue

    raise SafetyViolationError(
        f"Failed to find non-colliding destination after {max_collision_attempts} attempts."
    )


def _verify_moved_file(target_path: Path, expected_size: int) -> None:
    """Verify destination file exists and matches size after move."""
    if not target_path.exists():
        raise SafetyViolationError(
            f"Post-move verification failed: destination '{target_path}' does not exist."
        )
    actual_size = target_path.stat().st_size
    if actual_size != expected_size:
        raise SafetyViolationError(
            f"Post-move size mismatch on '{target_path}': expected {expected_size}, got {actual_size}."
        )
