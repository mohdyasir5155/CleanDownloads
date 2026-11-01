"""Windows Task Scheduler integration for automated downloads organization."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

TASK_NAME = "CleanDownloads_AutoOrganize"
SAFE_TASK_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


def _get_schtasks_path() -> str:
    """Resolve absolute path to system schtasks.exe to avoid PATH hijacking."""
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    schtasks_exe = Path(system_root) / "System32" / "schtasks.exe"
    if schtasks_exe.is_file():
        return str(schtasks_exe)
    return "schtasks.exe"


@dataclass
class ScheduleStatus:
    """Status of scheduled organization task."""
    is_registered: bool
    is_enabled: bool
    frequency: str | None = None
    next_run_time: str | None = None
    last_run_time: str | None = None
    last_result: str | None = None
    raw_info: str | None = None


class WindowsScheduler:
    """Manages user-level Windows Scheduled Tasks for CleanDownloads."""

    FREQUENCIES: dict[str, dict[str, str]] = {
        "30m": {"sc": "MINUTE", "mo": "30", "desc": "Every 30 minutes"},
        "hourly": {"sc": "HOURLY", "mo": "1", "desc": "Every 1 hour"},
        "daily": {"sc": "DAILY", "mo": "1", "desc": "Daily at 09:00"},
        "logon": {"sc": "ONLOGON", "mo": "", "desc": "On user login"},
    }

    def __init__(self, task_name: str = TASK_NAME) -> None:
        if not SAFE_TASK_NAME_RE.match(task_name):
            raise ValueError(f"Invalid task name '{task_name}'. Must match [a-zA-Z0-9_-]{{1,64}}.")
        self.task_name = task_name

    def _get_executable_command(self) -> str:
        """Locate cleandownloads executable or wrapper command safely."""
        cleandownloads_path = shutil.which("cleandownloads")
        if cleandownloads_path and Path(cleandownloads_path).is_file():
            resolved = str(Path(cleandownloads_path).resolve())
            return f'"{resolved}" organize --scheduled'

        # Fallback to current python executing cleandownloads module
        python_exe = str(Path(sys.executable).resolve())
        return f'"{python_exe}" -m cleandownloads.cli organize --scheduled'

    def _generate_task_xml(self, frequency_key: str) -> str:
        """Generate XML definition for scheduled task running hidden and only when logged on."""
        freq_key = frequency_key.lower()

        cleandownloads_path = shutil.which("cleandownloads")
        if cleandownloads_path and Path(cleandownloads_path).is_file():
            cmd = str(Path(cleandownloads_path).resolve())
            args = "organize --scheduled"
        else:
            cmd = str(Path(sys.executable).resolve())
            args = "-m cleandownloads.cli organize --scheduled"

        if freq_key == "30m":
            trigger_xml = """    <TimeTrigger>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Repetition>
        <Interval>PT30M</Interval>
      </Repetition>
    </TimeTrigger>"""
        elif freq_key == "hourly":
            trigger_xml = """    <TimeTrigger>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Repetition>
        <Interval>PT1H</Interval>
      </Repetition>
    </TimeTrigger>"""
        elif freq_key == "daily":
            trigger_xml = """    <CalendarTrigger>
      <StartBoundary>2026-01-01T09:00:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>"""
        elif freq_key == "logon":
            trigger_xml = "    <LogonTrigger />"
        else:
            raise ValueError(f"Unknown frequency: {frequency_key}")

        return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>CleanDownloads automated downloads organization</Description>
  </RegistrationInfo>
  <Triggers>
{trigger_xml}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{cmd}</Command>
      <Arguments>{args}</Arguments>
    </Exec>
  </Actions>
</Task>"""

    def get_status(self) -> ScheduleStatus:
        """Query the status of the scheduled task using schtasks.exe /XML (locale-independent)."""
        if sys.platform != "win32":
            return ScheduleStatus(
                is_registered=False,
                is_enabled=False,
                raw_info="Task scheduler is only supported on Windows.",
            )

        cmd = [_get_schtasks_path(), "/Query", "/TN", self.task_name, "/XML"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                shell=False,
            )
            if res.returncode != 0:
                return ScheduleStatus(is_registered=False, is_enabled=False)

            output = res.stdout.strip()
            try:
                # Local XML generated by system schtasks.exe
                root = ET.fromstring(output)  # nosec B314
            except Exception:
                return ScheduleStatus(
                    is_registered=True,
                    is_enabled=True,
                    raw_info="registered, details unavailable",
                )

            # 1. Enabled status
            enabled_elem = root.find(".//{*}Settings/{*}Enabled")
            if enabled_elem is None:
                enabled_elem = root.find(".//{*}Enabled")
            is_enabled = True
            if enabled_elem is not None and enabled_elem.text:
                is_enabled = enabled_elem.text.strip().lower() not in ("false", "0")

            # 2. LastRunTime
            last_run_elem = root.find(".//{*}LastRunTime")
            if last_run_elem is None:
                last_run_elem = root.find(".//{*}LastRun")
            last_run = last_run_elem.text.strip() if (last_run_elem is not None and last_run_elem.text) else None

            # 3. NextRunTime and Trigger data
            next_run_elem = root.find(".//{*}NextRunTime")
            if next_run_elem is None:
                next_run_elem = root.find(".//{*}NextRun")
            next_run = next_run_elem.text.strip() if (next_run_elem is not None and next_run_elem.text) else None

            frequency = None
            triggers_elem = root.find(".//{*}Triggers")
            if triggers_elem is not None:
                cal_trigger = triggers_elem.find(".//{*}CalendarTrigger")
                daily_trigger = triggers_elem.find(".//{*}DailyTrigger")
                logon_trigger = triggers_elem.find(".//{*}LogonTrigger")

                start_boundary = triggers_elem.findtext(".//{*}StartBoundary")
                repetition = triggers_elem.findtext(".//{*}Repetition/{*}Interval")

                if repetition:
                    rep_upper = repetition.upper()
                    if "30M" in rep_upper:
                        frequency = "30m"
                    elif "1H" in rep_upper:
                        frequency = "hourly"
                elif cal_trigger is not None or daily_trigger is not None:
                    frequency = "daily"
                elif logon_trigger is not None:
                    frequency = "logon"

                if not next_run:
                    if start_boundary and repetition:
                        next_run = f"Start: {start_boundary}, Interval: {repetition}"
                    elif start_boundary:
                        next_run = f"Start: {start_boundary}"
                    elif logon_trigger is not None:
                        next_run = "On user logon"

            return ScheduleStatus(
                is_registered=True,
                is_enabled=is_enabled,
                frequency=frequency,
                next_run_time=next_run,
                last_run_time=last_run,
                raw_info=output,
            )
        except Exception as e:
            return ScheduleStatus(
                is_registered=False,
                is_enabled=False,
                raw_info=str(e),
            )

    def register(self, frequency_key: str = "hourly") -> tuple[bool, str]:
        """Register or update a user-level scheduled task running hidden and only when logged on."""
        if sys.platform != "win32":
            return False, "Scheduled tasks are only supported on Windows."

        freq_info = self.FREQUENCIES.get(frequency_key.lower())
        if not freq_info:
            valid_keys = ", ".join(self.FREQUENCIES.keys())
            return False, f"Invalid frequency '{frequency_key}'. Valid options: {valid_keys}"

        xml_content = self._generate_task_xml(frequency_key)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".xml", encoding="utf-16", delete=False
            ) as tmp_file:
                tmp_file.write(xml_content)
                tmp_path = Path(tmp_file.name)

            cmd = [
                _get_schtasks_path(),
                "/Create",
                "/TN",
                self.task_name,
                "/XML",
                str(tmp_path),
                "/F",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
            if res.returncode == 0:
                return True, f"Successfully scheduled task '{self.task_name}' ({freq_info['desc']})."
            else:
                return False, f"Failed to create scheduled task: {res.stderr or res.stdout}"
        except Exception as e:
            return False, f"Error executing schtasks: {e}"
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def disable(self) -> tuple[bool, str]:
        """Disable scheduled task without deleting it."""
        if sys.platform != "win32":
            return False, "Not supported on this platform."

        cmd = [_get_schtasks_path(), "/Change", "/TN", self.task_name, "/DISABLE"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
            if res.returncode == 0:
                return True, "Scheduled task has been disabled."
            return False, f"Failed to disable task: {res.stderr or res.stdout}"
        except Exception as e:
            return False, str(e)

    def enable(self) -> tuple[bool, str]:
        """Enable previously disabled scheduled task."""
        if sys.platform != "win32":
            return False, "Not supported on this platform."

        cmd = [_get_schtasks_path(), "/Change", "/TN", self.task_name, "/ENABLE"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
            if res.returncode == 0:
                return True, "Scheduled task has been enabled."
            return False, f"Failed to enable task: {res.stderr or res.stdout}"
        except Exception as e:
            return False, str(e)

    def delete(self) -> tuple[bool, str]:
        """Delete scheduled task completely."""
        if sys.platform != "win32":
            return False, "Not supported on this platform."

        cmd = [_get_schtasks_path(), "/Delete", "/TN", self.task_name, "/F"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
            if res.returncode == 0:
                return True, "Scheduled task removed successfully."
            return False, f"Failed to remove task: {res.stderr or res.stdout}"
        except Exception as e:
            return False, str(e)
