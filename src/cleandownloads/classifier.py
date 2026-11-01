"""Intelligent file classification engine for CleanDownloads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cleandownloads.config import AppConfig, RuleConfig
from cleandownloads.safety import split_extension


@dataclass
class ClassificationResult:
    """Result of classifying a file."""
    filename: str
    extension: str
    category: str
    subfolder: str
    rule_name: str
    is_matched: bool

    @property
    def target_relative_path(self) -> Path:
        """Target relative path under Downloads for this file."""
        return Path(self.subfolder) / self.filename


class Classifier:
    """Classifies files into categories and destination folder structures."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._build_index()

    def _build_index(self) -> None:
        """Build fast lookup map from lowercase extension to RuleConfig."""
        self._extension_map: dict[str, RuleConfig] = {}
        for rule in self.config.rules:
            for ext in rule.extensions:
                clean_ext = ext.lower().lstrip(".")
                if clean_ext and clean_ext not in self._extension_map:
                    self._extension_map[clean_ext] = rule

    def classify_filename(self, filename: str) -> ClassificationResult:
        """Classify a file by its name or extension."""
        stem, ext = split_extension(filename)
        # ext has leading dot e.g. '.pdf' or '.tar.gz', or empty
        clean_ext = ext.lower().lstrip(".")

        rule = self._extension_map.get(clean_ext)
        if not rule and "." in clean_ext:
            # Check secondary segment if compound extension not directly mapped
            last_part = clean_ext.split(".")[-1]
            rule = self._extension_map.get(last_part)

        if rule:
            return ClassificationResult(
                filename=filename,
                extension=clean_ext,
                category=rule.category,
                subfolder=rule.subfolder,
                rule_name=rule.name,
                is_matched=True,
            )

        # Fallback to default uncategorized folder
        fallback_folder = self.config.default_fallback_folder or "Other"
        return ClassificationResult(
            filename=filename,
            extension=clean_ext,
            category="Other",
            subfolder=fallback_folder,
            rule_name="Other",
            is_matched=False,
        )

    def classify_path(self, path: Path) -> ClassificationResult:
        """Classify a Path object."""
        return self.classify_filename(path.name)

    def get_supported_extensions(self) -> dict[str, list[str]]:
        """Return a mapping of category -> list of supported extensions."""
        categories: dict[str, list[str]] = {}
        for rule in self.config.rules:
            if rule.category not in categories:
                categories[rule.category] = []
            for ext in rule.extensions:
                if ext not in categories[rule.category]:
                    categories[rule.category].append(ext)
        return categories
