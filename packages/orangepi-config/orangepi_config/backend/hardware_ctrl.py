"""
Hardware Control and Feature Toggles for Orange Pi Zero (Allwinner H2+/H3).
Handles CPU governors, CPU core hotplugging, LED triggers, and peripheral modules.
"""

from __future__ import annotations

import glob
import os
import subprocess
from typing import Dict, List, Optional, Tuple


class HardwareController:
    @staticmethod
    def get_available_governors() -> List[str]:
        """Returns list of supported CPU governors."""
        gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors"
        if os.path.isfile(gov_file):
            try:
                with open(gov_file, "r") as f:
                    return f.read().strip().split()
            except OSError:
                pass
        return ["schedutil", "performance", "ondemand", "powersave", "conservative"]

    @staticmethod
    def get_current_governor() -> str:
        """Returns current CPU governor."""
        gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        if os.path.isfile(gov_file):
            try:
                with open(gov_file, "r") as f:
                    return f.read().strip()
            except OSError:
                pass
        return "unknown"

    @staticmethod
    def get_persistent_governor() -> str:
        """Reads persisted governor from /etc/default/cpufreq if present."""
        conf = "/etc/default/cpufreq"
        if os.path.isfile(conf):
            try:
                with open(conf, "r") as f:
                    for line in f:
                        if line.startswith("GOVERNOR="):
                            return line.split("=", 1)[1].strip().strip('"\'')
            except OSError:
                pass
        return "performance"

    @staticmethod
    def set_governor(governor: str) -> Tuple[bool, str]:
        """Sets scaling governor for all CPU cores with Orange Pi Zero failsafe protection."""
        # Failsafe for Orange Pi Zero (H2+) discrete regulator brownout
        is_opi_zero = False
        if os.path.isfile("/proc/device-tree/model"):
            try:
                with open("/proc/device-tree/model", "r") as f:
                    is_opi_zero = "Orange Pi Zero" in f.read()
            except OSError:
                pass

        if is_opi_zero and governor.lower() in ("powersave", "conservative"):
            return False, (
                "Failsafe Protection: 'powersave'/'conservative' triggers a 1.10V discrete regulator "
                "brownout on Orange Pi Zero H2+. Governor kept at safe voltage (performance/schedutil)."
            )

        success_count = 0
        error_msg = ""
        for gov_path in glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"):
            try:
                with open(gov_path, "w") as f:
                    f.write(governor)
                success_count += 1
            except Exception as e:
                error_msg = str(e)
        if success_count > 0:
            # Persist governor choice across reboots
            try:
                os.makedirs("/etc/default", exist_ok=True)
                with open("/etc/default/cpufreq", "w") as f:
                    f.write(f'# Managed by orangepi-config\nGOVERNOR="{governor}"\n')
                subprocess.run(["systemctl", "enable", "cpufreq-governor.service"], capture_output=True)
            except Exception:
                pass
            return True, f"Governor set to '{governor}' across {success_count} core(s) (persisted across reboots)."
        return False, f"Failed to set governor: {error_msg} (Are you root?)"

    @staticmethod
    def get_core_states() -> List[Dict[str, Any]]:
        """Returns online/offline state for each core."""
        cores: List[Dict[str, Any]] = []
        for i in range(8):
            core_dir = f"/sys/devices/system/cpu/cpu{i}"
            if not os.path.isdir(core_dir):
                break
            if i == 0:
                # cpu0 is always online
                cores.append({"core": 0, "online": True, "can_toggle": False})
            else:
                online_path = f"{core_dir}/online"
                online = True
                if os.path.isfile(online_path):
                    try:
                        with open(online_path, "r") as f:
                            online = f.read().strip() == "1"
                    except OSError:
                        pass
                cores.append({"core": i, "online": online, "can_toggle": True})
        return cores

    @staticmethod
    def set_core_online(core_id: int, online: bool) -> Tuple[bool, str]:
        """Hotplug core online (True) or offline (False). Core 0 cannot be disabled."""
        if core_id == 0:
            return False, "CPU core 0 is the primary boot core and cannot be disabled."
        online_path = f"/sys/devices/system/cpu/cpu{core_id}/online"
        if not os.path.isfile(online_path):
            return False, f"CPU{core_id} does not support hotplug."
        try:
            with open(online_path, "w") as f:
                f.write("1" if online else "0")
            state_str = "online" if online else "offline"
            return True, f"CPU{core_id} is now {state_str}."
        except Exception as e:
            return False, f"Failed to set CPU{core_id}: {e}"

    @staticmethod
    def get_leds() -> List[Dict[str, Any]]:
        """Discovers on-board LEDs and returns current triggers and brightness."""
        leds: List[Dict[str, Any]] = []
        base_dir = "/sys/class/leds"
        if not os.path.isdir(base_dir):
            return leds

        for led_name in sorted(os.listdir(base_dir)):
            led_path = os.path.join(base_dir, led_name)
            trigger_file = os.path.join(led_path, "trigger")
            brightness_file = os.path.join(led_path, "brightness")

            current_trigger = "none"
            available_triggers: List[str] = []
            if os.path.isfile(trigger_file):
                try:
                    with open(trigger_file, "r") as f:
                        raw = f.read().strip().split()
                        for item in raw:
                            if item.startswith("[") and item.endswith("]"):
                                current_trigger = item[1:-1]
                                available_triggers.append(current_trigger)
                            else:
                                available_triggers.append(item)
                except OSError:
                    pass

            brightness = 0
            if os.path.isfile(brightness_file):
                try:
                    with open(brightness_file, "r") as f:
                        brightness = int(f.read().strip())
                except (OSError, ValueError):
                    pass

            # Friendly name mapping
            friendly_name = led_name
            if "red" in led_name or "status" in led_name:
                friendly_name = "Red LED (Status)"
            elif "green" in led_name or "pwr" in led_name:
                friendly_name = "Green LED (Power)"

            leds.append({
                "sysfs_name": led_name,
                "name": friendly_name,
                "current_trigger": current_trigger,
                "available_triggers": available_triggers,
                "brightness": brightness,
            })
        return leds

    @staticmethod
    def set_led_trigger(led_name: str, trigger: str) -> Tuple[bool, str]:
        """Sets trigger mode for an on-board LED."""
        trigger_path = f"/sys/class/leds/{led_name}/trigger"
        if not os.path.isfile(trigger_path):
            return False, f"LED {led_name} not found."
        try:
            with open(trigger_path, "w") as f:
                f.write(trigger)
            return True, f"LED {led_name} trigger set to '{trigger}'."
        except Exception as e:
            return False, f"Failed to set LED trigger: {e}"

    @staticmethod
    def set_led_brightness(led_name: str, brightness: int) -> Tuple[bool, str]:
        """Sets brightness for an on-board LED (0 or 1)."""
        brightness_path = f"/sys/class/leds/{led_name}/brightness"
        if not os.path.isfile(brightness_path):
            return False, f"LED {led_name} not found."
        try:
            with open(brightness_path, "w") as f:
                f.write(str(brightness))
            return True, f"LED {led_name} brightness set to {brightness}."
        except Exception as e:
            return False, f"Failed to set LED brightness: {e}"

    @staticmethod
    def get_wifi_state() -> Dict[str, Any]:
        """Checks if WiFi interface (wlan0) is UP and driver loaded."""
        driver_loaded = False
        try:
            with open("/proc/modules", "r") as f:
                modules = f.read()
                driver_loaded = "xradio_wlan" in modules or "xr819" in modules
        except Exception:
            pass

        interface_present = os.path.isdir("/sys/class/net/wlan0")
        is_up = False
        if interface_present:
            state_file = "/sys/class/net/wlan0/operstate"
            if os.path.isfile(state_file):
                try:
                    with open(state_file, "r") as f:
                        is_up = f.read().strip() == "up"
                except OSError:
                    pass

        return {
            "driver_loaded": driver_loaded,
            "interface_present": interface_present,
            "is_up": is_up,
        }

    @staticmethod
    def toggle_wifi(up: bool) -> Tuple[bool, str]:
        """Brings wlan0 interface up or down."""
        try:
            action = "up" if up else "down"
            res = subprocess.run(
                ["ip", "link", "set", "wlan0", action],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                return True, f"WiFi (wlan0) brought {action}."
            return False, f"Error: {res.stderr.strip()}"
        except Exception as e:
            return False, str(e)
