"""Tests for process concurrency locking and SQLite robustness."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from cleandownloads.config import DEFAULT_RULES, AppConfig, RuleConfig
from cleandownloads.history import HistoryDB
from cleandownloads.organizer import Organizer
from cleandownloads.safety import OperationLockError, SingleInstanceLock


def test_sqlite_wal_and_timeout(tmp_path: Path):
    """Verify SQLite opens with WAL mode and busy_timeout."""
    db_file = tmp_path / "test_wal.db"
    db = HistoryDB(db_path=db_file)

    with db._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode;")
        journal_mode = cur.fetchone()[0]
        cur.execute("PRAGMA busy_timeout;")
        busy_timeout = cur.fetchone()[0]

    assert journal_mode.lower() == "wal"
    assert busy_timeout == 30000


def test_concurrent_organize_refused(tmp_path: Path, monkeypatch):
    """Verify a second concurrent organize attempt is refused while first holds lock."""
    lock_file = tmp_path / "app_data" / "cleandownloads.lock"
    monkeypatch.setenv("CLEANDOWNLOADS_DATA_DIR", str(tmp_path / "app_data"))

    lock1 = SingleInstanceLock(lock_path=lock_file)
    assert lock1.acquire()

    # Second lock attempt must fail
    lock2 = SingleInstanceLock(lock_path=lock_file)
    assert not lock2.acquire()
    with pytest.raises(OperationLockError):
        with lock2:
            pass

    # Organizer organize attempt must be refused with OperationLockError
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    (downloads / "doc.pdf").write_text("sample")

    rules = [RuleConfig(**r) for r in DEFAULT_RULES]
    config = AppConfig(rules=rules, downloads_dir=str(downloads), min_file_age_seconds=0)
    history_db = HistoryDB(db_path=tmp_path / "hist.db")
    organizer = Organizer(config=config, history_db=history_db, lock=lock2)

    with pytest.raises(OperationLockError, match="currently running"):
        organizer.organize(dry_run=False)

    # Release lock1
    lock1.release()

    # Now organize succeeds
    res = organizer.organize(dry_run=False)
    assert res.successful_moves == 1


def test_stale_lock_from_dead_process_does_not_block(tmp_path: Path):
    """Verify an abrupt exit of a process automatically releases the lock file."""
    lock_file = tmp_path / "app_data" / "cleandownloads.lock"

    # Spawn subprocess that acquires the lock and waits
    code = f"""
from cleandownloads.safety import SingleInstanceLock
from pathlib import Path
import time, sys

lock = SingleInstanceLock(lock_path=Path(r"{lock_file}"))
if lock.acquire():
    sys.stdout.write("ACQUIRED\\n")
    sys.stdout.flush()
    time.sleep(10)
"""
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "-c", code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    try:
        assert proc.stdout is not None
        line = proc.stdout.readline().strip()
        assert line == "ACQUIRED"

        # While process is running, lock cannot be acquired
        parent_lock = SingleInstanceLock(lock_path=lock_file)
        assert not parent_lock.acquire()

        # Abruptly kill the subprocess (simulating a crash/dead process)
        proc.kill()
        proc.wait()

        # Windows handle cleanup is asynchronous after process termination, retry briefly
        import time

        acquired = False
        for _ in range(50):
            if parent_lock.acquire():
                acquired = True
                break
            time.sleep(0.05)

        assert acquired
        parent_lock.release()
    finally:
        if proc.poll() is None:
            proc.kill()


def test_cli_scheduled_exits_quietly_when_locked(tmp_path: Path, monkeypatch):
    """Verify cleandownloads organize --scheduled exits with code 75 when locked."""
    lock_file = tmp_path / "app_data" / "cleandownloads.lock"
    monkeypatch.setenv("CLEANDOWNLOADS_DATA_DIR", str(tmp_path / "app_data"))

    lock1 = SingleInstanceLock(lock_path=lock_file)
    assert lock1.acquire()

    try:
        env = os.environ.copy()
        env["CLEANDOWNLOADS_DATA_DIR"] = str(tmp_path / "app_data")
        res = subprocess.run(
            [sys.executable, "-m", "cleandownloads.cli", "organize", "--scheduled"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert res.returncode == 75
        assert res.stdout == ""
        assert res.stderr == ""
    finally:
        lock1.release()
