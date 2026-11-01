"""Contract tests for CLI JSON outputs against desktop/src/types.ts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cleandownloads.cli import main


@pytest.fixture
def env_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Set up isolated app data and downloads folder for CLI contract testing."""
    app_data = tmp_path / "app_data"
    app_data.mkdir()
    monkeypatch.setenv("CLEANDOWNLOADS_DATA_DIR", str(app_data))

    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    # Create dummy files for organization
    (downloads / "document.pdf").write_text("dummy pdf", encoding="utf-8")
    (downloads / "photo.png").write_text("dummy png", encoding="utf-8")
    (downloads / "partial.crdownload").write_text("downloading", encoding="utf-8")

    return downloads


def run_cli_json(capsys: pytest.CaptureFixture[str], args: list[str]) -> dict[str, Any]:
    """Execute CLI command and return parsed JSON output."""
    main(args)
    captured = capsys.readouterr()
    return json.loads(captured.out)


def test_scan_json_contract(env_setup: Path, capsys: pytest.CaptureFixture[str]):
    """Verify scan --json output conforms to ScanResponse in desktop/src/types.ts."""
    data = run_cli_json(capsys, ["scan", "-d", str(env_setup), "--min-age", "0", "--json"])

    # Required keys and types
    assert isinstance(data["downloads_dir"], str)
    assert isinstance(data["total_ready"], int)
    assert isinstance(data["total_ready_bytes"], int)
    assert isinstance(data["already_organized_count"], int)
    assert isinstance(data["category_breakdown"], dict)
    assert isinstance(data["ready_files"], list)
    assert isinstance(data["skipped_files"], list)

    for rf in data["ready_files"]:
        assert isinstance(rf["filename"], str)
        assert isinstance(rf["extension"], str)
        assert isinstance(rf["category"], str)
        assert isinstance(rf["subfolder"], str)
        assert isinstance(rf["size_bytes"], int)
        assert isinstance(rf["source_path"], str)
        assert isinstance(rf["target_relative_path"], str)

    for sf in data["skipped_files"]:
        assert isinstance(sf["path"], str)
        assert isinstance(sf["reason"], str)


def test_preview_json_contract(env_setup: Path, capsys: pytest.CaptureFixture[str]):
    """Verify preview --json output conforms to PreviewResponse in desktop/src/types.ts."""
    data = run_cli_json(capsys, ["preview", "-d", str(env_setup), "--min-age", "0", "--json"])

    assert isinstance(data["downloads_dir"], str)
    assert isinstance(data["total_files"], int)
    assert isinstance(data["total_bytes"], int)
    assert isinstance(data["planned_moves"], list)

    for pm in data["planned_moves"]:
        assert isinstance(pm["source"], str)
        assert isinstance(pm["destination"], str)
        assert isinstance(pm["file_size"], int)
        assert isinstance(pm["category"], str)
        assert isinstance(pm["extension"], str)


def test_organize_and_undo_and_history_and_status_contracts(
    env_setup: Path, capsys: pytest.CaptureFixture[str]
):
    """Verify organize, undo, history, and status --json outputs."""
    # 1. Organize
    org_data = run_cli_json(
        capsys,
        ["organize", "-d", str(env_setup), "--min-age", "0", "--json"],
    )
    assert isinstance(org_data["batch_id"], str)
    assert isinstance(org_data["total_files"], int)
    assert isinstance(org_data["successful_moves"], int)
    assert isinstance(org_data["failed_moves"], int)
    assert isinstance(org_data["is_dry_run"], bool)
    assert isinstance(org_data["moved_items"], list)
    assert isinstance(org_data["failed_items"], list)

    for mi in org_data["moved_items"]:
        assert isinstance(mi["source"], str)
        assert isinstance(mi["destination"], str)
        assert isinstance(mi["file_size"], int)
        assert isinstance(mi["category"], str)
        assert isinstance(mi["operation_id"], int)

    for fi in org_data["failed_items"]:
        assert isinstance(fi["source"], str)
        assert isinstance(fi["target_destination"], str)
        assert isinstance(fi["error"], str)
        assert isinstance(fi["category"], str)

    # 2. History
    hist_data = run_cli_json(capsys, ["history", "--json"])
    assert isinstance(hist_data["batches"], list)
    assert len(hist_data["batches"]) >= 1
    for b in hist_data["batches"]:
        assert isinstance(b["id"], str)
        assert isinstance(b["timestamp"], str)
        assert isinstance(b["total_files"], int)
        assert isinstance(b["successful_moves"], int)
        assert isinstance(b["failed_moves"], int)
        assert isinstance(b["status"], str)
        assert b["notes"] is None or isinstance(b["notes"], str)

    # 3. Status
    stat_data = run_cli_json(capsys, ["status", "-d", str(env_setup), "--json"])
    assert isinstance(stat_data["version"], str)
    assert isinstance(stat_data["downloads_dir"], str)
    assert isinstance(stat_data["app_data_dir"], str)
    assert isinstance(stat_data["recursive"], bool)
    assert isinstance(stat_data["rules_count"], int)

    stats = stat_data["stats"]
    assert isinstance(stats["total_batches"], int)
    assert isinstance(stats["active_organized_files"], int)
    assert isinstance(stats["total_undone_files"], int)
    assert isinstance(stats["total_failed_moves"], int)
    assert isinstance(stats["category_breakdown"], dict)

    sched = stat_data["scheduler"]
    assert isinstance(sched["is_registered"], bool)
    assert isinstance(sched["is_enabled"], bool)
    assert sched["next_run_time"] is None or isinstance(sched["next_run_time"], str)
    assert sched["last_run_time"] is None or isinstance(sched["last_run_time"], str)

    # 4. Undo
    undo_data = run_cli_json(capsys, ["undo", "-y", "--json"])
    assert isinstance(undo_data["batch_id"], str)
    assert isinstance(undo_data["total_attempted"], int)
    assert isinstance(undo_data["success_count"], int)
    assert isinstance(undo_data["fail_count"], int)
    assert isinstance(undo_data["restored_files"], list)
    assert isinstance(undo_data["failed_files"], list)

    for rf in undo_data["restored_files"]:
        assert isinstance(rf["operation_id"], int)
        assert isinstance(rf["original_path"], str)
        assert isinstance(rf["moved_from_path"], str)
        assert isinstance(rf["actual_restored_path"], str)

    for ff in undo_data["failed_files"]:
        assert isinstance(ff["operation_id"], int)
        assert isinstance(ff["moved_from_path"], str)
        assert isinstance(ff["target_path"], str)
        assert isinstance(ff["reason"], str)
