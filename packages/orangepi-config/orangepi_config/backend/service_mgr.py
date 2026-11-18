"""
Systemd unit & service management backend for orangepi-config.
"""

from __future__ import annotations

import subprocess
from typing import Dict, List, Tuple


ALLOWED_ACTIONS = {"start", "stop", "restart", "enable", "disable"}


class ServiceManager:
    """Lists and controls systemd units and services."""

    @staticmethod
    def list_units(unit_type: str = "service", filter_text: str = "") -> List[Dict[str, str]]:
        """
        Returns a sorted list of systemd units merged from unit-files (boot state)
        and runtime units (active/sub state).
        """
        units: Dict[str, Dict[str, str]] = {}
        type_args = [f"--type={unit_type}"] if unit_type and unit_type != "all" else []

        # 1. Boot enablement states
        try:
            res_files = subprocess.run(
                ["systemctl", "list-unit-files", "--no-pager", "--no-legend"] + type_args,
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in res_files.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    name, enable_state = parts[0], parts[1]
                    if "@" in name and name.endswith(f"@.{unit_type}"):
                        continue
                    units[name] = {
                        "unit": name,
                        "enable_state": enable_state,
                        "active": "inactive",
                        "sub": "dead",
                        "description": "",
                    }
        except Exception:
            pass

        # 2. Active/loaded runtime states
        try:
            res_active = subprocess.run(
                ["systemctl", "list-units", "--all", "--no-pager", "--no-legend"] + type_args,
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in res_active.stdout.splitlines():
                cleaned = line.lstrip("● ").strip()
                if not cleaned:
                    continue
                parts = cleaned.split(None, 4)
                if len(parts) >= 4:
                    name, _load, active, sub = parts[0], parts[1], parts[2], parts[3]
                    desc = parts[4] if len(parts) > 4 else ""
                    entry = units.setdefault(
                        name,
                        {
                            "unit": name,
                            "enable_state": "static",
                            "active": active,
                            "sub": sub,
                            "description": desc,
                        },
                    )
                    entry["active"] = active
                    entry["sub"] = sub
                    if desc:
                        entry["description"] = desc
        except Exception:
            pass

        flt = filter_text.strip().lower()
        result = []
        for info in units.values():
            if flt and flt not in info["unit"].lower() and flt not in info["description"].lower():
                continue
            result.append(info)

        # Sort active units first, then alphabetically
        result.sort(key=lambda x: (0 if x["active"] == "active" else (1 if x["active"] == "failed" else 2), x["unit"]))
        return result

    @staticmethod
    def control_unit(unit: str, action: str) -> Tuple[bool, str]:
        """Executes start/stop/restart/enable/disable on a systemd unit."""
        if action not in ALLOWED_ACTIONS:
            return False, f"Unsupported systemd action: {action}"
        if not unit or any(ch.isspace() for ch in unit):
            return False, f"Invalid unit name: {unit}"

        try:
            res = subprocess.run(
                ["systemctl", action, unit],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if res.returncode == 0:
                return True, f"Successfully ran 'systemctl {action} {unit}'."
            err = res.stderr.strip() or res.stdout.strip() or f"Exit code {res.returncode}"
            return False, f"Failed '{action}' on {unit}: {err}"
        except Exception as e:
            return False, f"Error running 'systemctl {action} {unit}': {e}"

    @staticmethod
    def get_unit_status(unit: str) -> str:
        """Returns compact systemctl status output for a unit."""
        try:
            res = subprocess.run(
                ["systemctl", "status", unit, "--no-pager", "-n", "8"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return (res.stdout or res.stderr).strip()
        except Exception as e:
            return f"Failed to fetch status: {e}"
