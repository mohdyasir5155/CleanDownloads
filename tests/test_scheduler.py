"""Tests for Windows Task Scheduler integration and locale-independent XML parsing."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

from cleandownloads.scheduler import WindowsScheduler

SAMPLE_XML_ENGLISH = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>CleanDownloads automated downloads organization</Description>
    <Author>DESKTOP-TEST\\User</Author>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>2026-01-01T12:00:00</StartBoundary>
      <Repetition>
        <Interval>PT1H</Interval>
      </Repetition>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
  </Settings>
  <LastRunTime>2026-11-01T21:30:00</LastRunTime>
</Task>"""

SAMPLE_XML_DISABLED = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T09:00:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <Enabled>false</Enabled>
    <Hidden>true</Hidden>
  </Settings>
</Task>"""

# German locale sample with localized descriptions and non-ASCII characters
SAMPLE_XML_NON_ENGLISH_GERMAN = """<?xml version="1.0" encoding="UTF-16"?>
<!-- \\CleanDownloads_AutoOrganize -->
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Automatische Bereinigung des Download-Ordners für Downloads</Description>
    <Author>BÜRO-RECHNER\\Jürgen</Author>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>2026-01-01T08:00:00</StartBoundary>
      <Repetition>
        <Interval>PT30M</Interval>
      </Repetition>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
  </Settings>
  <LastRunTime>2026-11-01T22:15:00</LastRunTime>
</Task>"""

# Chinese locale sample with non-ASCII characters
SAMPLE_XML_NON_ENGLISH_CHINESE = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>CleanDownloads 自动整理下载文件夹任务</Description>
    <Author>工作电脑\\张伟</Author>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger />
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
  </Settings>
</Task>"""


def test_scheduler_get_status_xml_parsing(monkeypatch):
    """Verify locale-independent XML query correctly extracts enabled, last run, and frequency."""
    monkeypatch.setattr(sys, "platform", "win32")

    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=["schtasks", "/Query", "/TN", "CleanDownloads_AutoOrganize", "/XML"],
        returncode=0,
        stdout=SAMPLE_XML_ENGLISH,
        stderr="",
    ))
    monkeypatch.setattr(subprocess, "run", mock_run)

    scheduler = WindowsScheduler()
    status = scheduler.get_status()

    assert status.is_registered is True
    assert status.is_enabled is True
    assert status.frequency == "hourly"
    assert status.last_run_time == "2026-11-01T21:30:00"
    assert "Start: 2026-01-01T12:00:00" in (status.next_run_time or "")

    # Verify command invoked schtasks /Query /TN <name> /XML
    mock_run.assert_called_once()
    called_cmd = mock_run.call_args[0][0]
    assert "/XML" in called_cmd
    assert "/Query" in called_cmd


def test_scheduler_get_status_disabled_task(monkeypatch):
    """Verify disabled task is parsed properly from XML Settings/Enabled."""
    monkeypatch.setattr(sys, "platform", "win32")

    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=SAMPLE_XML_DISABLED,
        stderr="",
    ))
    monkeypatch.setattr(subprocess, "run", mock_run)

    scheduler = WindowsScheduler()
    status = scheduler.get_status()

    assert status.is_registered is True
    assert status.is_enabled is False
    assert status.frequency == "daily"


def test_scheduler_get_status_non_english_german(monkeypatch):
    """Verify non-English (German) system output parses correctly."""
    monkeypatch.setattr(sys, "platform", "win32")

    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=SAMPLE_XML_NON_ENGLISH_GERMAN,
        stderr="",
    ))
    monkeypatch.setattr(subprocess, "run", mock_run)

    scheduler = WindowsScheduler()
    status = scheduler.get_status()

    assert status.is_registered is True
    assert status.is_enabled is True
    assert status.frequency == "30m"
    assert status.last_run_time == "2026-11-01T22:15:00"


def test_scheduler_get_status_non_english_chinese(monkeypatch):
    """Verify non-English (Chinese logon trigger) system output parses correctly."""
    monkeypatch.setattr(sys, "platform", "win32")

    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=SAMPLE_XML_NON_ENGLISH_CHINESE,
        stderr="",
    ))
    monkeypatch.setattr(subprocess, "run", mock_run)

    scheduler = WindowsScheduler()
    status = scheduler.get_status()

    assert status.is_registered is True
    assert status.is_enabled is True
    assert status.frequency == "logon"
    assert status.next_run_time == "On user logon"


def test_scheduler_get_status_fallback_on_unparseable_xml(monkeypatch):
    """Verify fallback to 'registered, details unavailable' when XML is invalid."""
    monkeypatch.setattr(sys, "platform", "win32")

    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="Some custom non-XML text from third-party schtasks replacement",
        stderr="",
    ))
    monkeypatch.setattr(subprocess, "run", mock_run)

    scheduler = WindowsScheduler()
    status = scheduler.get_status()

    assert status.is_registered is True
    assert status.is_enabled is True
    assert status.raw_info == "registered, details unavailable"


def test_scheduler_get_status_not_registered(monkeypatch):
    """Verify schtasks non-zero returncode indicates task not registered."""
    monkeypatch.setattr(sys, "platform", "win32")

    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="ERROR: The system cannot find the file specified.",
    ))
    monkeypatch.setattr(subprocess, "run", mock_run)

    scheduler = WindowsScheduler()
    status = scheduler.get_status()

    assert status.is_registered is False
    assert status.is_enabled is False


def test_scheduler_register_creates_hidden_and_interactive_task(monkeypatch):
    """Verify task registration creates XML configured to run hidden and with InteractiveToken."""
    monkeypatch.setattr(sys, "platform", "win32")

    captured_xml: list[str] = []

    def mock_run(cmd, **kwargs):
        if "/Create" in cmd and "/XML" in cmd:
            xml_path = cmd[cmd.index("/XML") + 1]
            content = Path(xml_path).read_text(encoding="utf-16")
            captured_xml.append(content)
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="SUCCESS", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    scheduler = WindowsScheduler()

    for freq in ["30m", "hourly", "daily", "logon"]:
        captured_xml.clear()
        success, msg = scheduler.register(freq)
        assert success is True
        assert len(captured_xml) == 1
        xml = captured_xml[0]
        # Must run hidden
        assert "<Hidden>true</Hidden>" in xml
        # Must run only when user is logged on
        assert "<LogonType>InteractiveToken</LogonType>" in xml
