"""Tests for configuration persistence and modification."""

from pathlib import Path

from cleandownloads.config import ConfigManager


def test_config_defaults(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    mgr = ConfigManager(config_path=cfg_file)

    assert mgr.config.version == "1.0.0"
    assert not mgr.config.recursive
    assert mgr.config.min_file_size_bytes == 0
    assert len(mgr.config.rules) > 0


def test_config_save_and_reload(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    mgr = ConfigManager(config_path=cfg_file)

    custom_dir = tmp_path / "MyDownloads"
    custom_dir.mkdir()
    mgr.set_downloads_dir(custom_dir)
    mgr.set_recursive(True)

    mgr.add_custom_rule(
        name="CAD Drawings",
        category="Design",
        subfolder="CAD/Drawings",
        extensions=["dwg", "dxf"],
    )

    # Reload from disk in a new instance
    mgr2 = ConfigManager(config_path=cfg_file)
    assert mgr2.config.downloads_dir == str(custom_dir.resolve())
    assert mgr2.config.recursive is True

    cad_rule = next((r for r in mgr2.config.rules if r.name == "CAD Drawings"), None)
    assert cad_rule is not None
    assert cad_rule.category == "Design"
    assert cad_rule.subfolder == "CAD/Drawings"
    assert cad_rule.extensions == ["dwg", "dxf"]


def test_config_remove_rule(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    mgr = ConfigManager(config_path=cfg_file)

    initial_rules_count = len(mgr.config.rules)
    removed = mgr.remove_rule("PDF Documents")
    assert removed is True
    assert len(mgr.config.rules) == initial_rules_count - 1

    # Reload and verify persistence
    mgr2 = ConfigManager(config_path=cfg_file)
    assert len(mgr2.config.rules) == initial_rules_count - 1


def test_config_reset_to_defaults(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    mgr = ConfigManager(config_path=cfg_file)
    mgr.set_recursive(True)
    mgr.reset_to_defaults()

    assert mgr.config.recursive is False
