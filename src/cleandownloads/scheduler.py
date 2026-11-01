"""Windows Task Scheduler integration for automated downloads organization."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
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

    def get_status(self) -> ScheduleStatus:
        """Query the status of the scheduled task using schtasks.exe."""
        if sys.platform != "win32":
            return ScheduleStatus(
                is_registered=False,
                is_enabled=False,
                raw_info="Task scheduler is only supported on Windows.",
            )

        cmd = [_get_schtasks_path(), "/Query", "/TN", self.task_name, "/FO", "LIST", "/V"]
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

            output = res.stdout
            is_enabled = "Disabled" not in output
            next_run = None
            last_run = None
            last_res = None

            for line in output.splitlines():
                line_stripped = line.strip()
                if line_stripped.startswith("Next Run Time:"):
                    next_run = line_stripped.split(":", 1)[1].strip()
                elif line_stripped.startswith("Last Run Time:"):
                    last_run = line_stripped.split(":", 1)[1].strip()
                elif line_stripped.startswith("Last Result:"):
                    last_res = line_stripped.split(":", 1)[1].strip()

            return ScheduleStatus(
                is_registered=True,
                is_enabled=is_enabled,
                next_run_time=next_run,
                last_run_time=last_run,
                last_result=last_res,
                raw_info=output,
            )
        except Exception as e:
            return ScheduleStatus(
                is_registered=False,
                is_enabled=False,
                raw_info=str(e),
            )

    def register(self, frequency_key: str = "hourly") -> tuple[bool, str]:
        """Register or update a user-level scheduled task."""
        if sys.platform != "win32":
            return False, "Scheduled tasks are only supported on Windows."

        freq_info = self.FREQUENCIES.get(frequency_key.lower())
        if not freq_info:
            valid_keys = ", ".join(self.FREQUENCIES.keys())
            return False, f"Invalid frequency '{frequency_key}'. Valid options: {valid_keys}"

        action_cmd = self._get_executable_command()
        sc = freq_info["sc"]
        mo = freq_info["mo"]

        cmd = [
            _get_schtasks_path(),
            "/Create",
            "/F",  # Force overwrite if exists
            "/TN",
            self.task_name,
            "/TR",
            action_cmd,
            "/SC",
            sc,
        ]

        if mo:
            cmd.extend(["/MO", mo])

        if sc == "DAILY":
            cmd.extend(["/ST", "09:00"])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
            if res.returncode == 0:
                return True, f"Successfully scheduled task '{self.task_name}' ({freq_info['desc']})."
            else:
                return False, f"Failed to create scheduled task: {res.stderr or res.stdout}"
        except Exception as e:
            return False, f"Error executing schtasks: {e}"

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
