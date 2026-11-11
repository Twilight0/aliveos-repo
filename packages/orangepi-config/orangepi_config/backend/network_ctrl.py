"""
Network Controller and XR819 Wireless Driver Diagnostics for Orange Pi Zero.
Provides interface configuration (DHCP/Static IP), wireless SSID scanning,
connection management, and hardware bus/firmware recovery for Xunlong's XR819 WiFi.
"""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple


class NetworkController:
    @staticmethod
    def get_interfaces() -> List[Dict[str, Any]]:
        """Returns details for all detected network interfaces."""
        interfaces: List[Dict[str, Any]] = []
        base_net = "/sys/class/net"
        if not os.path.isdir(base_net):
            return interfaces

        # Default gateway and DNS
        default_gw = ""
        try:
            r = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True)
            m = re.search(r"default via ([0-9.]+)", r.stdout)
            if m:
                default_gw = m.group(1)
        except Exception:
            pass

        dns_servers: List[str] = []
        if os.path.isfile("/etc/resolv.conf"):
            try:
                with open("/etc/resolv.conf", "r") as f:
                    for line in f:
                        if line.startswith("nameserver"):
                            parts = line.split()
                            if len(parts) > 1:
                                dns_servers.append(parts[1])
            except Exception:
                pass

        for iface in sorted(os.listdir(base_net)):
            if iface == "lo":
                continue
            iface_dir = os.path.join(base_net, iface)

            # Interface type
            iface_type = "ethernet"
            if os.path.isdir(os.path.join(iface_dir, "wireless")) or os.path.isdir(os.path.join(iface_dir, "phy80211")):
                iface_type = "wireless"
            elif iface.startswith("wlan") or iface.startswith("wlp"):
                iface_type = "wireless"

            # Operstate
            operstate = "unknown"
            state_file = os.path.join(iface_dir, "operstate")
            if os.path.isfile(state_file):
                try:
                    with open(state_file, "r") as f:
                        operstate = f.read().strip()
                except OSError:
                    pass

            # Carrier (cable connected for ethernet)
            carrier = False
            carrier_file = os.path.join(iface_dir, "carrier")
            if os.path.isfile(carrier_file):
                try:
                    with open(carrier_file, "r") as f:
                        carrier = (f.read().strip() == "1")
                except OSError:
                    pass

            # MAC Address
            mac = "00:00:00:00:00:00"
            mac_file = os.path.join(iface_dir, "address")
            if os.path.isfile(mac_file):
                try:
                    with open(mac_file, "r") as f:
                        mac = f.read().strip()
                except OSError:
                    pass

            # IPv4 Address
            ipv4 = ""
            try:
                out = subprocess.check_output(["ip", "-4", "addr", "show", iface], text=True, stderr=subprocess.DEVNULL)
                m = re.search(r"inet ([0-9./]+)", out)
                if m:
                    ipv4 = m.group(1)
            except Exception:
                pass

            interfaces.append({
                "name": iface,
                "type": iface_type,
                "operstate": operstate,
                "carrier": carrier,
                "mac": mac,
                "ipv4": ipv4,
                "gateway": default_gw,
                "dns": dns_servers,
            })

        return interfaces

    @staticmethod
    def get_primary_wireless_interface() -> Optional[str]:
        """Detects the primary wireless interface name (e.g. wlan0, wld1, wlx...)."""
        base_net = "/sys/class/net"
        if not os.path.isdir(base_net):
            return None
        # Check standard wlan0 first
        if os.path.isdir(os.path.join(base_net, "wlan0")):
            return "wlan0"
        # Search for any wireless interface
        for iface in sorted(os.listdir(base_net)):
            iface_dir = os.path.join(base_net, iface)
            if os.path.isdir(os.path.join(iface_dir, "wireless")) or os.path.isdir(os.path.join(iface_dir, "phy80211")):
                return iface
            if iface.startswith(("wlan", "wl")):
                return iface
        return None

    @staticmethod
    def get_xr819_diagnostics() -> Dict[str, Any]:
        """Inspects Xunlong XR819 WiFi module state, firmware presence, and errors."""
        wlan_iface = NetworkController.get_primary_wireless_interface()
        diag: Dict[str, Any] = {
            "driver_loaded": False,
            "interface_name": wlan_iface or "wlan0",
            "interface_present": (wlan_iface is not None),
            "firmware_ok": False,
            "firmware_files": {},
            "rfkill_blocked": False,
            "powersave_off": False,
            "dmesg_errors": [],
        }

        # Check loaded modules
        try:
            with open("/proc/modules", "r") as f:
                mods = f.read()
                diag["driver_loaded"] = ("xradio_wlan" in mods or "xr819" in mods)
        except Exception:
            pass

        # Check firmware files in /lib/firmware/xr819
        fw_dir = "/lib/firmware/xr819"
        expected_fw = ["boot_xr819.bin", "fw_xr819.bin", "sdd_xr819.bin"]
        fw_status = {}
        for fw in expected_fw:
            path = os.path.join(fw_dir, fw)
            fw_status[fw] = os.path.isfile(path)
        diag["firmware_files"] = fw_status
        diag["firmware_ok"] = all(fw_status.values())

        # Check rfkill
        try:
            rf = subprocess.run(["rfkill", "list", "wifi"], capture_output=True, text=True)
            if "Soft blocked: yes" in rf.stdout or "Hard blocked: yes" in rf.stdout:
                diag["rfkill_blocked"] = True
        except Exception:
            pass

        # Check powersave mode (powersave causes XR819 SDIO sleep hangs)
        if wlan_iface:
            try:
                iw = subprocess.run(["iw", "dev", wlan_iface, "get", "power_save"], capture_output=True, text=True)
                if "Power save: off" in iw.stdout:
                    diag["powersave_off"] = True
            except Exception:
                pass

        # Check dmesg for xradio errors
        try:
            dm = subprocess.run(["dmesg"], capture_output=True, text=True)
            errors = []
            for line in dm.stdout.splitlines():
                if any(k in line.lower() for k in ["xradio", "xr819", "wlan0: error", "sdd_xr819"]):
                    errors.append(line.strip())
            diag["dmesg_errors"] = errors[-6:]  # Last 6 relevant lines
        except Exception:
            pass

        return diag

    @staticmethod
    def reload_xr819_driver() -> Tuple[bool, str]:
        """Resets the SDIO bus by unloading and reloading the xradio_wlan kernel driver."""
        try:
            subprocess.run(["modprobe", "-r", "xradio_wlan"], capture_output=True)
            subprocess.run(["sleep", "1"])
            res = subprocess.run(["modprobe", "xradio_wlan"], capture_output=True, text=True)
            if res.returncode == 0:
                return True, "Driver 'xradio_wlan' reloaded successfully."
            return False, f"Failed to reload xradio_wlan: {res.stderr.strip()}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def unblock_rfkill() -> Tuple[bool, str]:
        """Unblocks wireless devices using rfkill."""
        try:
            res = subprocess.run(["rfkill", "unblock", "wifi"], capture_output=True, text=True)
            if res.returncode == 0:
                return True, "RFKill wireless unblocked."
            return False, res.stderr.strip()
        except Exception as e:
            return False, str(e)

    @staticmethod
    def disable_wifi_powersave() -> Tuple[bool, str]:
        """Disables power management on wireless interface (fixes XR819 SDIO sleep timeout dropouts)."""
        if not shutil.which("iw"):
            return False, "'iw' utility is not installed. Please install it from Software tab."
        iface = NetworkController.get_primary_wireless_interface() or "wlan0"
        try:
            res = subprocess.run(["iw", "dev", iface, "set", "power_save", "off"], capture_output=True, text=True)
            if res.returncode == 0:
                return True, f"WiFi Power Save disabled on {iface} (XR819 keep-alive active)."
            return False, res.stderr.strip()
        except Exception as e:
            return False, str(e)

    @staticmethod
    def scan_wifi_networks() -> List[Dict[str, str]]:
        """Scans for nearby wireless networks using iw or wpa_cli."""
        if not shutil.which("iw"):
            return [{"ssid": "[iw utility not installed]", "signal": "-", "security": "Install 'iw'"}]

        iface = NetworkController.get_primary_wireless_interface()
        if not iface:
            return [{"ssid": "[Wireless interface not found]", "signal": "-", "security": "Module xradio_wlan not loaded"}]

        # Ensure interface is up before scanning
        subprocess.run(["ip", "link", "set", iface, "up"], capture_output=True)

        networks: List[Dict[str, str]] = []
        try:
            res = subprocess.run(["iw", "dev", iface, "scan"], capture_output=True, text=True, timeout=8)
            if res.returncode != 0:
                err = res.stderr.strip() or "Device busy or scanning error"
                return [{"ssid": f"[{err}]", "signal": "-", "security": "Error"}]

            current_net: Dict[str, str] = {}
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith("BSS "):
                    if current_net.get("ssid"):
                        networks.append(current_net)
                    current_net = {"ssid": "", "signal": "N/A", "security": "Open"}
                elif line.startswith("SSID:"):
                    ssid = line[5:].strip()
                    if ssid and not ssid.startswith("\\x00"):
                        current_net["ssid"] = ssid
                elif "signal:" in line:
                    m = re.search(r"signal:\s*(-?[0-9.]+)\s*dBm", line)
                    if m:
                        current_net["signal"] = f"{m.group(1)} dBm"
                elif "RSN:" in line or "WPA:" in line:
                    current_net["security"] = "WPA2/WPA3"

            if current_net.get("ssid"):
                networks.append(current_net)
        except subprocess.TimeoutExpired:
            return [{"ssid": "[Scan timed out]", "signal": "-", "security": "Hardware busy"}]
        except Exception as e:
            return [{"ssid": f"[Scan failed: {e}]", "signal": "-", "security": "Error"}]

        # Deduplicate SSIDs keeping strongest signal
        seen = set()
        deduped = []
        for n in networks:
            if n["ssid"] not in seen:
                seen.add(n["ssid"])
                deduped.append(n)

        return deduped

    @staticmethod
    def connect_wifi_wpa(ssid: str, passphrase: str) -> Tuple[bool, str]:
        """Configures wpa_supplicant for wireless interface with given SSID and passphrase."""
        if not ssid:
            return False, "SSID cannot be empty."

        iface = NetworkController.get_primary_wireless_interface() or "wlan0"
        wpa_dir = "/etc/wpa_supplicant"
        wpa_conf = os.path.join(wpa_dir, f"wpa_supplicant-{iface}.conf")
        try:
            os.makedirs(wpa_dir, exist_ok=True)
            
            # Generate wpa config with wpa_passphrase if available, else plain text
            conf_body = ""
            if passphrase and shutil.which("wpa_passphrase"):
                res = subprocess.run(["wpa_passphrase", ssid, passphrase], capture_output=True, text=True)
                if res.returncode == 0:
                    conf_body = (
                        "ctrl_interface=/run/wpa_supplicant\n"
                        "update_config=1\n"
                        f"{res.stdout.strip()}\n"
                    )
            
            if not conf_body:
                if passphrase:
                    net_block = (
                        f'network={{\n    ssid="{ssid}"\n    psk="{passphrase}"\n    key_mgmt=WPA-PSK\n}}\n'
                    )
                else:
                    net_block = f'network={{\n    ssid="{ssid}"\n    key_mgmt=NONE\n}}\n'
                conf_body = (
                    "ctrl_interface=/run/wpa_supplicant\n"
                    "update_config=1\n"
                    f"{net_block}"
                )

            with open(wpa_conf, "w") as f:
                f.write(conf_body)
            os.chmod(wpa_conf, 0o600)

            # Bring up interface and restart wpa_supplicant
            subprocess.run(["ip", "link", "set", iface, "up"], capture_output=True)
            subprocess.run(["systemctl", "enable", "--now", f"wpa_supplicant@{iface}"], capture_output=True)
            subprocess.run(["systemctl", "restart", f"wpa_supplicant@{iface}"], capture_output=True)

            return True, f"WiFi credentials for '{ssid}' saved on {iface}. wpa_supplicant restarted."
        except Exception as e:
            return False, f"Failed to configure WiFi: {e}"

    @staticmethod
    def get_dns_servers() -> List[str]:
        """Returns list of active DNS servers."""
        dns: List[str] = []
        try:
            r = subprocess.run(["resolvectl", "dns"], capture_output=True, text=True)
            for line in r.stdout.splitlines():
                parts = line.split(":")
                if len(parts) > 1:
                    servers = parts[1].strip().split()
                    for s in servers:
                        if s not in dns:
                            dns.append(s)
        except Exception:
            pass

        if not dns and os.path.isfile("/etc/resolv.conf"):
            try:
                with open("/etc/resolv.conf", "r") as f:
                    for line in f:
                        if line.startswith("nameserver"):
                            parts = line.split()
                            if len(parts) > 1 and parts[1] not in dns:
                                dns.append(parts[1])
            except Exception:
                pass
        return dns

    @staticmethod
    def set_dns_servers(dns_servers: str, iface: Optional[str] = None) -> Tuple[bool, str]:
        """
        Configures DNS servers persistently in systemd-resolved and networkd.
        Accepts space-separated IP addresses (e.g. '1.1.1.1 8.8.8.8').
        """
        servers = dns_servers.strip().split()
        if not servers:
            return False, "DNS server address cannot be empty."

        import ipaddress
        for s in servers:
            try:
                ipaddress.ip_address(s)
            except ValueError:
                return False, f"Invalid IP address format: '{s}'"

        dns_str = " ".join(servers)
        try:
            # 1. Configure systemd-resolved drop-in
            resolved_conf_dir = "/etc/systemd/resolved.conf.d"
            os.makedirs(resolved_conf_dir, exist_ok=True)
            with open(os.path.join(resolved_conf_dir, "00-custom-dns.conf"), "w") as f:
                f.write(f"[Resolve]\nDNS={dns_str}\nFallbackDNS=1.1.1.1 8.8.8.8\n")

            # 2. Update networkd interface configs if present
            net_dir = "/etc/systemd/network"
            if os.path.isdir(net_dir):
                for fn in os.listdir(net_dir):
                    if fn.endswith(".network"):
                        fp = os.path.join(net_dir, fn)
                        try:
                            with open(fp, "r") as f:
                                lines = f.readlines()
                            new_lines = []
                            has_dns = False
                            for line in lines:
                                if line.startswith("DNS="):
                                    new_lines.append(f"DNS={dns_str}\n")
                                    has_dns = True
                                else:
                                    new_lines.append(line)
                            if not has_dns:
                                out_lines = []
                                for line in new_lines:
                                    out_lines.append(line)
                                    if line.strip() == "[Network]":
                                        out_lines.append(f"DNS={dns_str}\n")
                                new_lines = out_lines
                            with open(fp, "w") as f:
                                f.writelines(new_lines)
                        except Exception:
                            pass

            # 3. Reload services
            subprocess.run(["systemctl", "restart", "systemd-networkd", "systemd-resolved"], capture_output=True)
            subprocess.run(["resolvectl", "flush-caches"], capture_output=True)

            return True, f"DNS servers successfully set to: {dns_str}"
        except Exception as e:
            return False, f"Failed to set DNS servers: {e}"

    @staticmethod
    def configure_interface(
        iface: str,
        mode: str,
        ip: str = "",
        gateway: str = "",
        dns: str = "",
    ) -> Tuple[bool, str]:
        """Configures interface using systemd-networkd (DHCP or Static)."""
        net_dir = "/etc/systemd/network"
        os.makedirs(net_dir, exist_ok=True)
        conf_file = os.path.join(net_dir, f"20-{iface}.network")

        try:
            if mode.lower() == "dhcp":
                content = (
                    f"[Match]\nName={iface}\n\n"
                    "[Network]\nDHCP=yes\nIPv6PrivacyExtensions=yes\n"
                )
                if dns:
                    content += f"DNS={dns}\n\n[DHCPv4]\nUseDNS=false\n"
            else:
                if not ip:
                    return False, "Static IP address is required (e.g., 192.168.1.50/24)."
                # Add /24 default if CIDR omitted
                if "/" not in ip:
                    ip = f"{ip}/24"
                content = (
                    f"[Match]\nName={iface}\n\n"
                    f"[Network]\nAddress={ip}\n"
                )
                if gateway:
                    content += f"Gateway={gateway}\n"
                if dns:
                    content += f"DNS={dns}\n"

            with open(conf_file, "w") as f:
                f.write(content)

            # Restart network service
            subprocess.run(["systemctl", "restart", "systemd-networkd"], capture_output=True)
            return True, f"Configuration saved to {conf_file} and systemd-networkd reloaded."
        except Exception as e:
            return False, f"Failed to configure interface {iface}: {e}"
