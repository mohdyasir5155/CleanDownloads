"""Configuration management and schema validation for CleanDownloads."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from cleandownloads.safety import (
    WINDOWS_RESERVED_NAMES,
    SafetyViolationError,
    get_app_data_dir,
    get_default_downloads_dir,
)

CONFIG_FILENAME = "config.json"
MAX_CONFIG_FILE_SIZE = 512 * 1024  # 512 KB limit to prevent DoS
MAX_RULES_COUNT = 200
MAX_SUBFOLDER_DEPTH = 4
MAX_SUBFOLDER_LENGTH = 100
EXTENSION_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


class ConfigurationError(SafetyViolationError):
    """Raised when configuration validation or parsing fails."""


def validate_extension_string(ext: str) -> str:
    """Validate and normalize a file extension."""
    cleaned = ext.strip().lower().lstrip(".")
    if not cleaned:
        raise ConfigurationError("Extension cannot be empty.")
    if len(cleaned) > 32:
        raise ConfigurationError(f"Extension '{cleaned}' exceeds 32 characters.")
    if not EXTENSION_REGEX.match(cleaned):
        raise ConfigurationError(
            f"Extension '{cleaned}' contains illegal characters (only alphanumeric, -, _, . allowed)."
        )
    return cleaned


def validate_subfolder_path(subfolder: str) -> str:
    """Validate that a target subfolder is safe, relative, and non-escaping.
    
    Raises ConfigurationError if invalid.
    """
    cleaned = subfolder.strip().replace("\\", "/")
    if not cleaned:
        raise ConfigurationError("Subfolder path cannot be empty.")

    if len(cleaned) > MAX_SUBFOLDER_LENGTH:
        raise ConfigurationError(
            f"Subfolder path '{cleaned}' exceeds maximum length ({MAX_SUBFOLDER_LENGTH})."
        )

    # Reject absolute paths, drive letters, and UNC prefixes
    if cleaned.startswith("/") or ":" in cleaned or cleaned.startswith("//"):
        raise ConfigurationError(
            f"Subfolder path '{cleaned}' must be relative, not absolute or drive-qualified."
        )

    # Reject path traversal
    parts = [p for p in cleaned.split("/") if p]
    if not parts:
        raise ConfigurationError("Subfolder path contains no valid directories.")

    if len(parts) > MAX_SUBFOLDER_DEPTH:
        raise ConfigurationError(
            f"Subfolder path depth ({len(parts)}) exceeds maximum allowed ({MAX_SUBFOLDER_DEPTH})."
        )

    for part in parts:
        if part in (".", ".."):
            raise ConfigurationError(
                f"Subfolder path '{cleaned}' contains illegal traversal element '{part}'."
            )
        if re.search(r'[<>"|?*:\0]', part):
            raise ConfigurationError(
                f"Subfolder component '{part}' contains illegal characters."
            )
        base_name = part.split(".")[0].lower()
        if base_name in WINDOWS_RESERVED_NAMES:
            raise ConfigurationError(
                f"Subfolder component '{part}' uses a Windows reserved name."
            )

    return "/".join(parts)


@dataclass
class RuleConfig:
    """A classification rule mapping file extensions to a category and destination folder."""
    name: str
    category: str
    subfolder: str
    extensions: list[str]

    def __post_init__(self) -> None:
        # Validate and sanitize subfolder
        self.subfolder = validate_subfolder_path(self.subfolder)
        # Normalize and validate extensions
        validated_exts: list[str] = []
        for ext in self.extensions:
            try:
                clean_ext = validate_extension_string(ext)
                if clean_ext not in validated_exts:
                    validated_exts.append(clean_ext)
            except SafetyViolationError:
                continue
        self.extensions = validated_exts


@dataclass
class AppConfig:
    """Application-wide settings and classification rules."""
    version: str = "1.0.0"
    downloads_dir: str | None = None
    recursive: bool = False
    min_file_size_bytes: int = 0
    max_file_size_bytes: int | None = None
    conflict_strategy: str = "rename"
    ignored_extensions: list[str] = field(default_factory=lambda: [
        "crdownload",
        "part",
        "tmp",
        "download",
        "aria2",
        "opdownload",
        "!ut",
    ])
    excluded_directories: list[str] = field(default_factory=lambda: [
        "Documents",
        "Images",
        "Videos",
        "Audio",
        "Archives",
        "Software",
        "Code",
        "Other",
        ".git",
        ".clean_history",
    ])
    rules: list[RuleConfig] = field(default_factory=list)
    default_fallback_folder: str = "Other"

    def __post_init__(self) -> None:
        if self.default_fallback_folder:
            self.default_fallback_folder = validate_subfolder_path(self.default_fallback_folder)

    def get_resolved_downloads_dir(self) -> Path:
        """Resolve the active Downloads directory."""
        if self.downloads_dir:
            p = Path(self.downloads_dir).expanduser().resolve()
            if p.exists() and p.is_dir():
                return p
        env_dir = os.environ.get("CLEANDOWNLOADS_DOWNLOADS_DIR")
        if env_dir:
            p = Path(env_dir).expanduser().resolve()
            if p.exists() and p.is_dir():
                return p
        return get_default_downloads_dir()


DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "name": "PDF Documents",
        "category": "Documents",
        "subfolder": "Documents/PDF",
        "extensions": ["pdf"],
    },
    {
        "name": "Word Documents",
        "category": "Documents",
        "subfolder": "Documents/Word",
        "extensions": ["doc", "docx", "odt", "rtf"],
    },
    {
        "name": "Excel Spreadsheets",
        "category": "Documents",
        "subfolder": "Documents/Excel",
        "extensions": ["xls", "xlsx", "csv"],
    },
    {
        "name": "PowerPoint Presentations",
        "category": "Documents",
        "subfolder": "Documents/PowerPoint",
        "extensions": ["ppt", "pptx"],
    },
    {
        "name": "PNG Images",
        "category": "Images",
        "subfolder": "Images/PNG",
        "extensions": ["png"],
    },
    {
        "name": "Other Images",
        "category": "Images",
        "subfolder": "Images",
        "extensions": ["jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico"],
    },
    {
        "name": "Videos",
        "category": "Videos",
        "subfolder": "Videos",
        "extensions": ["mp4", "mkv", "mov", "avi", "webm"],
    },
    {
        "name": "Audio",
        "category": "Audio",
        "subfolder": "Audio",
        "extensions": ["mp3", "wav", "flac", "aac", "m4a"],
    },
    {
        "name": "ZIP Archives",
        "category": "Archives",
        "subfolder": "Archives/ZIP",
        "extensions": ["zip"],
    },
    {
        "name": "Other Archives",
        "category": "Archives",
        "subfolder": "Archives",
        "extensions": ["rar", "7z", "tar", "gz"],
    },
    {
        "name": "Executable Software",
        "category": "Software",
        "subfolder": "Software/EXE",
        "extensions": ["exe"],
    },
    {
        "name": "Installers & Packages",
        "category": "Software",
        "subfolder": "Software",
        "extensions": ["msi", "msix"],
    },
    {
        "name": "Python Scripts",
        "category": "Code",
        "subfolder": "Code/Python",
        "extensions": ["py", "ipynb"],
    },
    {
        "name": "Web Development",
        "category": "Code",
        "subfolder": "Code/Web Development",
        "extensions": ["html", "css", "js", "ts", "jsx", "tsx"],
    },
    {
        "name": "Programming Languages",
        "category": "Code",
        "subfolder": "Code/Programming",
        "extensions": ["java", "cpp", "c", "cs", "go", "rs"],
    },
]


class ConfigManager:
    """Manages loading, validating, updating, and atomically saving configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = get_app_data_dir() / CONFIG_FILENAME

        self._config: AppConfig = self.load()

    @property
    def config(self) -> AppConfig:
        return self._config

    def load(self, raise_on_error: bool = False) -> AppConfig:
        """Load configuration from JSON with strict size and schema validation."""
        if self.config_path.exists():
            file_size = self.config_path.stat().st_size
            if file_size > MAX_CONFIG_FILE_SIZE:
                if raise_on_error:
                    raise ConfigurationError(
                        f"Configuration file size ({file_size} bytes) exceeds safe limit ({MAX_CONFIG_FILE_SIZE} bytes)."
                    )
                return self._build_default_config()

            try:
                with open(self.config_path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)

                if isinstance(data, dict):
                    return self._parse_config_dict(data)
                elif raise_on_error:
                    raise ConfigurationError("Configuration root must be a JSON object.")
            except Exception as e:
                if raise_on_error:
                    raise ConfigurationError(f"Malformed JSON configuration: {e}")

        return self._build_default_config()

    def _build_default_config(self) -> AppConfig:
        """Build the default configuration instance."""
        rules = [RuleConfig(**r) for r in DEFAULT_RULES]
        return AppConfig(rules=rules)

    def _parse_config_dict(self, data: dict[str, Any]) -> AppConfig:
        """Parse configuration dictionary into AppConfig with strict security checks."""
        raw_rules = data.get("rules", [])
        rules: list[RuleConfig] = []

        if isinstance(raw_rules, list):
            for r in raw_rules[:MAX_RULES_COUNT]:
                if not isinstance(r, dict):
                    continue
                try:
                    name = str(r.get("name", "Custom Rule"))[:64]
                    category = str(r.get("category", "Other"))[:32]
                    subfolder = validate_subfolder_path(str(r.get("subfolder", "Other")))
                    exts_raw = r.get("extensions", [])
                    if isinstance(exts_raw, list):
                        rule = RuleConfig(
                            name=name,
                            category=category,
                            subfolder=subfolder,
                            extensions=[str(e) for e in exts_raw],
                        )
                        if rule.extensions:
                            rules.append(rule)
                except Exception:
                    continue

        if not rules:
            rules = [RuleConfig(**r) for r in DEFAULT_RULES]

        fallback = "Other"
        try:
            if "default_fallback_folder" in data:
                fallback = validate_subfolder_path(str(data["default_fallback_folder"]))
        except Exception:
            fallback = "Other"

        ignored_exts: list[str] = []
        for e in data.get("ignored_extensions", []):
            try:
                ignored_exts.append(validate_extension_string(str(e)))
            except Exception:
                continue

        excluded_dirs: list[str] = []
        for d in data.get("excluded_directories", []):
            try:
                clean_d = str(d).strip().replace("\\", "/").strip("/")
                if clean_d and not any(c in clean_d for c in '<>:"|?*..'):
                    excluded_dirs.append(clean_d)
            except Exception:
                continue

        # Validate downloads_dir if specified
        custom_dl = data.get("downloads_dir")
        validated_dl: str | None = None
        if custom_dl and isinstance(custom_dl, str):
            try:
                p = Path(custom_dl).expanduser().resolve()
                if p.exists() and p.is_dir():
                    validated_dl = str(p)
            except Exception:
                validated_dl = None

        return AppConfig(
            version=str(data.get("version", "1.0.0")),
            downloads_dir=validated_dl,
            recursive=bool(data.get("recursive", False)),
            min_file_size_bytes=max(0, int(data.get("min_file_size_bytes", 0))),
            max_file_size_bytes=(
                max(0, int(data["max_file_size_bytes"]))
                if data.get("max_file_size_bytes") is not None
                else None
            ),
            conflict_strategy="rename",
            ignored_extensions=ignored_exts or [
                "crdownload",
                "part",
                "tmp",
                "download",
                "aria2",
                "opdownload",
                "!ut",
            ],
            excluded_directories=excluded_dirs or [
                "Documents",
                "Images",
                "Videos",
                "Audio",
                "Archives",
                "Software",
                "Code",
                "Other",
                ".git",
                ".clean_history",
            ],
            rules=rules,
            default_fallback_folder=fallback,
        )

    def save(self) -> None:
        """Atomically persist configuration to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self._config)

        # Write to temporary file first, then atomically replace
        temp_path = self.config_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.replace(str(temp_path), str(self.config_path))

    def reset_to_defaults(self) -> None:
        """Reset configuration to built-in factory defaults."""
        self._config = self._build_default_config()
        self.save()

    def set_downloads_dir(self, path: Path | None) -> None:
        """Set a custom downloads directory or None for default."""
        if path:
            resolved = path.resolve()
            if not resolved.exists() or not resolved.is_dir():
                raise SafetyViolationError(f"Directory does not exist: {path}")
            self._config.downloads_dir = str(resolved)
        else:
            self._config.downloads_dir = None
        self.save()

    def set_recursive(self, recursive: bool) -> None:
        """Toggle recursive scanning."""
        self._config.recursive = bool(recursive)
        self.save()

    def add_custom_rule(
        self,
        name: str,
        category: str,
        subfolder: str,
        extensions: list[str]
    ) -> None:
        """Add or update a classification rule with validation."""
        rule = RuleConfig(
            name=name[:64],
            category=category[:32],
            subfolder=validate_subfolder_path(subfolder),
            extensions=extensions,
        )
        if not rule.extensions:
            raise SafetyViolationError("Rule must contain at least one valid extension.")

        # Remove existing rule with same name if any
        self._config.rules = [r for r in self._config.rules if r.name.lower() != name.lower()]
        self._config.rules.append(rule)
        self.save()

    def remove_rule(self, name: str) -> bool:
        """Remove a classification rule by name."""
        initial_len = len(self._config.rules)
        self._config.rules = [r for r in self._config.rules if r.name.lower() != name.lower()]
        if len(self._config.rules) < initial_len:
            self.save()
            return True
        return False
