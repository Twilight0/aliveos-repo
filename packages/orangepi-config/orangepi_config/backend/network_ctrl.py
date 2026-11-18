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
        """Returns list of active or configured DNS servers."""
        # Prefer explicit custom override if configured
        custom_conf = "/etc/systemd/resolved.conf.d/00-custom-dns.conf"
        if os.path.isfile(custom_conf):
            try:
                with open(custom_conf, "r") as f:
                    for line in f:
                        if line.strip().startswith("DNS="):
                            vals = line.strip().split("=", 1)[1].split()
                            if vals:
                                return vals
            except Exception:
                pass

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
        Pass 'auto', 'dhcp', or 'gateway' to restore DHCP/gateway DNS.
        """
        raw = dns_servers.strip()
        if not raw:
            return False, "DNS server address cannot be empty (use 'auto' for DHCP/Gateway)."

        resolved_conf = "/etc/systemd/resolved.conf.d/00-custom-dns.conf"
        net_dir = "/etc/systemd/network"

        if raw.lower() in {"auto", "dhcp", "gateway"}:
            try:
                if os.path.exists(resolved_conf):
                    os.remove(resolved_conf)
                if os.path.isdir(net_dir):
                    for fn in os.listdir(net_dir):
                        if fn.endswith(".network"):
                            fp = os.path.join(net_dir, fn)
                            with open(fp, "r") as f:
                                lines = f.readlines()
                            new_lines = []
                            for line in lines:
                                if line.startswith("DNS="):
                                    continue
                                if line.strip() == "UseDNS=no":
                                    new_lines.append("UseDNS=yes\n")
                                else:
                                    new_lines.append(line)
                            with open(fp, "w") as f:
                                f.writelines(new_lines)
                subprocess.run(["systemctl", "restart", "systemd-networkd", "systemd-resolved"], capture_output=True)
                subprocess.run(["resolvectl", "flush-caches"], capture_output=True)
                return True, "DNS restored to automatic (DHCP / Gateway)."
            except Exception as e:
                return False, f"Failed to restore automatic DNS: {e}"

        servers = raw.split()
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
            with open(resolved_conf, "w") as f:
                f.write(f"[Resolve]\nDNS={dns_str}\n")

            # 2. Update networkd interface configs if present
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
                                elif line.strip() == "UseDNS=yes":
                                    new_lines.append("UseDNS=no\n")
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

    @staticmethod
    def get_pia_status() -> Dict[str, Any]:
        """Returns current Private Internet Access WireGuard VPN status and forwarded port."""
        active = False
        enabled = False
        forwarded_port = ""
        configured = os.path.exists("/etc/pia/pia.env")
        scripts_installed = os.path.exists("/opt/pia-manual-connections/run_setup.sh")

        try:
            r_act = subprocess.run(["systemctl", "is-active", "pia-vpn.service"], capture_output=True, text=True)
            active = r_act.stdout.strip() == "active"
            r_ena = subprocess.run(["systemctl", "is-enabled", "pia-vpn.service"], capture_output=True, text=True)
            enabled = r_ena.stdout.strip() == "enabled"
            if active:
                r_log = subprocess.run(
                    ["journalctl", "-u", "pia-vpn.service", "-n", "50", "--no-pager"],
                    capture_output=True,
                    text=True,
                )
                for line in reversed(r_log.stdout.splitlines()):
                    m = re.search(r"Forwarded port\s+(\d+)", line)
                    if m:
                        forwarded_port = m.group(1)
                        break
        except Exception:
            pass

        return {
            "active": active,
            "enabled": enabled,
            "configured": configured,
            "scripts_installed": scripts_installed,
            "forwarded_port": forwarded_port,
        }

    @staticmethod
    def configure_pia_wireguard(
        user: str,
        password: str,
        port_forward: bool = True,
        dip_token: str = "",
        region: str = "",
    ) -> Tuple[bool, str]:
        """Configures PIA WireGuard credentials and starts pia-vpn.service."""
        user = user.strip()
        password = password.strip()
        dip_token = dip_token.strip()
        region = region.strip()

        if not user or not re.match(r"^[pP]\d{7}$", user):
            return False, "Invalid PIA username (expected format: p1234567)."
        if len(password) < 8:
            return False, "PIA password must be at least 8 characters."

        try:
            # Ensure dependencies and PIA scripts exist
            missing = [pkg for pkg, bin_name in [("wireguard-tools", "wg"), ("jq", "jq")] if not shutil.which(bin_name)]
            if missing:
                subprocess.run(["pacman", "-S", "--needed", "--noconfirm"] + missing, check=True)

            if not os.path.exists("/opt/pia-manual-connections/run_setup.sh"):
                os.makedirs("/opt/pia-manual-connections", exist_ok=True)
                subprocess.run(
                    [
                        "/bin/bash",
                        "-c",
                        "curl -fsSL https://github.com/pia-foss/manual-connections/archive/refs/heads/master.tar.gz "
                        "| tar -xz --strip-components=1 -C /opt/pia-manual-connections",
                    ],
                    check=True,
                )

            os.makedirs("/etc/pia", mode=0o700, exist_ok=True)
            os.chmod("/etc/pia", 0o700)

            env_lines = [
                f"PIA_USER={user}",
                f"PIA_PASS={password}",
                f"DIP_TOKEN={dip_token if dip_token else 'no'}",
                f"PIA_PF={'false' if dip_token else ('true' if port_forward else 'false')}",
                "DISABLE_IPV6=yes",
                "VPN_PROTOCOL=wireguard",
                "PIA_DNS=false",
            ]
            if not dip_token:
                if region:
                    env_lines.append("AUTOCONNECT=false")
                    env_lines.append(f"PREFERRED_REGION={region}")
                else:
                    env_lines.append("AUTOCONNECT=true")
                    env_lines.append("MAX_LATENCY=0.25")

            with open("/etc/pia/pia.env", "w") as f:
                f.write("\n".join(env_lines) + "\n")
            os.chmod("/etc/pia/pia.env", 0o600)

            runner_path = "/usr/local/bin/pia-vpn"
            with open(runner_path, "w") as f:
                f.write(
                    "#!/usr/bin/env bash\n"
                    "set -a\n"
                    "source /etc/pia/pia.env\n"
                    "set +a\n"
                    "cd /opt/pia-manual-connections || exit 1\n"
                    "exec ./run_setup.sh\n"
                )
            os.chmod(runner_path, 0o755)

            unit_path = "/etc/systemd/system/pia-vpn.service"
            with open(unit_path, "w") as f:
                f.write(
                    "[Unit]\n"
                    "Description=Private Internet Access WireGuard VPN (manual-connections)\n"
                    "After=network.target\n\n"
                    "[Service]\n"
                    "Type=simple\n"
                    "ExecStart=/usr/local/bin/pia-vpn\n"
                    "ExecStopPost=/bin/sh -c \"wg-quick down pia 2>/dev/null || true\"\n"
                    "Restart=on-failure\n"
                    "RestartSec=10\n\n"
                    "[Install]\n"
                    "WantedBy=multi-user.target\n"
                )

            subprocess.run(["systemctl", "daemon-reload"], capture_output=True)
            subprocess.run(["systemctl", "restart", "pia-vpn.service"], check=True)
            return True, "PIA WireGuard configured and pia-vpn.service started. Refresh in ~20s for tunnel & port."
        except Exception as e:
            return False, f"Failed to configure PIA WireGuard: {e}"

    @staticmethod
    def stop_pia_vpn() -> Tuple[bool, str]:
        """Stops pia-vpn.service and tears down the WireGuard interface."""
        try:
            subprocess.run(["systemctl", "stop", "pia-vpn.service"], capture_output=True)
            subprocess.run(["wg-quick", "down", "pia"], capture_output=True)
            return True, "PIA WireGuard VPN stopped."
        except Exception as e:
            return False, f"Failed to stop PIA VPN: {e}"

    @staticmethod
    def set_pia_autostart(enabled: bool) -> Tuple[bool, str]:
        """Enables or disables pia-vpn.service at boot."""
        action = "enable" if enabled else "disable"
        try:
            res = subprocess.run(["systemctl", action, "pia-vpn.service"], capture_output=True, text=True)
            if res.returncode == 0:
                return True, f"PIA VPN autostart {action}d."
            return False, res.stderr.strip() or f"Failed to {action} pia-vpn.service."
        except Exception as e:
            return False, f"Failed to {action} pia-vpn.service: {e}"

    @staticmethod
    def get_pia_regions() -> List[Dict[str, Any]]:
        """Fetches available PIA WireGuard regions from PIA's official server list."""
        import json
        import urllib.request

        try:
            req = urllib.request.Request(
                "https://serverlist.piaservers.net/vpninfo/servers/v6",
                headers={"User-Agent": "orangepi-config"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw = resp.read().decode("utf-8", errors="replace").splitlines()[0]
                data = json.loads(raw)
                regions = []
                for r in data.get("regions", []):
                    if r.get("servers", {}).get("wg"):
                        regions.append({
                            "id": r.get("id", ""),
                            "name": r.get("name", ""),
                            "port_forward": bool(r.get("port_forward", False)),
                        })
                return sorted(regions, key=lambda x: x["name"])
        except Exception:
            return []
