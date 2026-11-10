"""
System Information and Diagnostics Collector for Orange Pi Zero / Sunxi SBCs.
Reads directly from Linux sysfs and procfs for zero overhead.
"""

from __future__ import annotations

import os
import shutil
import socket
import time
from typing import Any, Dict, List, Optional, Tuple


class SystemInfo:
    def __init__(self) -> None:
        self._last_cpu_times: Optional[List[Tuple[int, int]]] = None
        self._last_cpu_check: float = 0.0

    @staticmethod
    def get_soc_model() -> str:
        """Returns board model name from device tree or fallback."""
        model_paths = [
            "/sys/firmware/devicetree/base/model",
            "/proc/device-tree/model",
        ]
        for path in model_paths:
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        return f.read().strip().replace("\x00", "")
                except OSError:
                    pass
        return "Allwinner H2+/H3 (Orange Pi Zero)"

    @staticmethod
    def get_kernel_version() -> str:
        """Returns running kernel release."""
        try:
            return os.uname().release
        except Exception:
            return "Unknown"

    @staticmethod
    def get_hostname() -> str:
        """Returns system hostname."""
        try:
            return socket.gethostname()
        except Exception:
            return "localhost"

    @staticmethod
    def get_uptime() -> Tuple[str, float]:
        """Returns human-readable uptime and raw seconds."""
        try:
            with open("/proc/uptime", "r") as f:
                secs = float(f.readline().split()[0])
            mins, s = divmod(int(secs), 60)
            hours, m = divmod(mins, 60)
            days, h = divmod(hours, 24)
            parts = []
            if days > 0:
                parts.append(f"{days}d")
            if h > 0 or days > 0:
                parts.append(f"{h}h")
            parts.append(f"{m}m")
            parts.append(f"{s}s")
            return " ".join(parts), secs
        except Exception:
            return "N/A", 0.0

    @staticmethod
    def get_load_average() -> Tuple[float, float, float]:
        """Returns 1, 5, 15 minute system load averages."""
        try:
            with open("/proc/loadavg", "r") as f:
                parts = f.readline().split()
                return float(parts[0]), float(parts[1]), float(parts[2])
        except Exception:
            return 0.0, 0.0, 0.0

    @staticmethod
    def get_temperature() -> Optional[float]:
        """Reads SoC temperature in degrees Celsius."""
        thermal_zones = [
            "/sys/class/thermal/thermal_zone0/temp",
            "/sys/devices/virtual/thermal/thermal_zone0/temp",
        ]
        for path in thermal_zones:
            if os.path.isfile(path):
                try:
                    with open(path, "r") as f:
                        raw = f.read().strip()
                        return float(raw) / 1000.0
                except (OSError, ValueError):
                    pass
        return None

    def get_cpu_info(self) -> Dict[str, Any]:
        """
        Gathers core count, online status, current frequencies,
        governor, and calculates CPU usage percentage.
        """
        cores: List[Dict[str, Any]] = []
        base_path = "/sys/devices/system/cpu"
        
        # Discover cores (cpu0 .. cpu7)
        core_idx = 0
        while True:
            core_dir = os.path.join(base_path, f"cpu{core_idx}")
            if not os.path.isdir(core_dir):
                break
            
            # Check online status
            online = True
            online_path = os.path.join(core_dir, "online")
            if os.path.isfile(online_path):
                try:
                    with open(online_path, "r") as f:
                        online = f.read().strip() == "1"
                except OSError:
                    online = True
            
            # Check frequency
            freq_mhz = 0
            if online:
                freq_path = os.path.join(core_dir, "cpufreq", "scaling_cur_freq")
                if os.path.isfile(freq_path):
                    try:
                        with open(freq_path, "r") as f:
                            freq_mhz = int(f.read().strip()) // 1000
                    except (OSError, ValueError):
                        pass

            cores.append({
                "id": core_idx,
                "online": online,
                "freq_mhz": freq_mhz,
            })
            core_idx += 1

        # Current governor
        gov = "unknown"
        gov_path = os.path.join(base_path, "cpu0", "cpufreq", "scaling_governor")
        if os.path.isfile(gov_path):
            try:
                with open(gov_path, "r") as f:
                    gov = f.read().strip()
            except OSError:
                pass

        # CPU Usage calculation
        overall_usage = self._calc_cpu_usage()

        return {
            "cores": cores,
            "core_count": len(cores),
            "governor": gov,
            "usage_percent": overall_usage,
        }

    def _calc_cpu_usage(self) -> float:
        """Calculates instantaneous CPU busy percentage using /proc/stat."""
        try:
            with open("/proc/stat", "r") as f:
                for line in f:
                    if line.startswith("cpu "):
                        parts = [int(x) for x in line.split()[1:8]]
                        # user, nice, system, idle, iowait, irq, softirq
                        idle = parts[3] + parts[4]
                        total = sum(parts)
                        now = time.time()

                        if self._last_cpu_times is not None:
                            last_idle, last_total = self._last_cpu_times[0]
                            idle_delta = idle - last_idle
                            total_delta = total - last_total
                            self._last_cpu_times = [(idle, total)]
                            self._last_cpu_check = now
                            if total_delta > 0:
                                return max(0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta)))
                        else:
                            self._last_cpu_times = [(idle, total)]
                            self._last_cpu_check = now
                            return 0.0
        except Exception:
            pass
        return 0.0

    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        """Parses /proc/meminfo for memory and swap stats (in MB)."""
        mem: Dict[str, int] = {}
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0]
                        mem[key] = int(val) // 1024  # convert KiB to MiB
        except Exception:
            return {
                "total": 0, "used": 0, "free": 0, "available": 0,
                "swap_total": 0, "swap_used": 0, "swap_free": 0,
            }

        total = mem.get("MemTotal", 0)
        free = mem.get("MemFree", 0)
        available = mem.get("MemAvailable", free)
        used = max(0, total - available)
        
        swap_total = mem.get("SwapTotal", 0)
        swap_free = mem.get("SwapFree", 0)
        swap_used = max(0, swap_total - swap_free)

        used_pct = (used / total * 100.0) if total > 0 else 0.0
        swap_pct = (swap_used / swap_total * 100.0) if swap_total > 0 else 0.0

        return {
            "total_mb": total,
            "used_mb": used,
            "free_mb": free,
            "available_mb": available,
            "used_percent": used_pct,
            "swap_total_mb": swap_total,
            "swap_used_mb": swap_used,
            "swap_free_mb": swap_free,
            "swap_used_percent": swap_pct,
        }

    @staticmethod
    def get_disk_info(mount_point: str = "/") -> Dict[str, Any]:
        """Returns storage metrics for the specified mount point."""
        try:
            usage = shutil.disk_usage(mount_point)
            total_gb = usage.total / (1024 ** 3)
            used_gb = usage.used / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)
            pct = (usage.used / usage.total * 100.0) if usage.total > 0 else 0.0
            return {
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "used_percent": round(pct, 1),
            }
        except Exception:
            return {"total_gb": 0.0, "used_gb": 0.0, "free_gb": 0.0, "used_percent": 0.0}

    @staticmethod
    def get_network_interfaces() -> List[Dict[str, str]]:
        """Returns list of network interfaces and their primary IPv4 addresses."""
        interfaces: List[Dict[str, str]] = []
        net_dir = "/sys/class/net"
        if not os.path.isdir(net_dir):
            return interfaces

        for iface in sorted(os.listdir(net_dir)):
            if iface == "lo":
                continue
            operstate = "unknown"
            state_path = os.path.join(net_dir, iface, "operstate")
            if os.path.isfile(state_path):
                try:
                    with open(state_path, "r") as f:
                        operstate = f.read().strip()
                except OSError:
                    pass

            ip_addr = "No IP"
            # Get IP via socket or ip command
            try:
                import subprocess
                out = subprocess.check_output(
                    ["ip", "-4", "addr", "show", iface],
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                for line in out.splitlines():
                    line = line.strip()
                    if line.startswith("inet "):
                        ip_addr = line.split()[1]
                        break
            except Exception:
                pass

            interfaces.append({
                "name": iface,
                "state": operstate,
                "ip": ip_addr,
            })
        return interfaces
