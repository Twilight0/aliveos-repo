"""
Package Manager and Headless Software Catalog for Arch Linux ARM.
Interacts with pacman to check status and install utilities.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, Generator, List, Optional, Tuple


@dataclass
class SoftwarePackage:
    name: str
    category: str
    description: str
    installed: bool = False


DEFAULT_PACKAGES: List[SoftwarePackage] = [
    # Core CLI & Shells
    SoftwarePackage("htop", "Core CLI", "Interactive process viewer and CPU/RAM monitor"),
    SoftwarePackage("btop", "Core CLI", "Modern resource monitor with aesthetic UI"),
    SoftwarePackage("tmux", "Core CLI", "Terminal multiplexer with persistent sessions"),
    SoftwarePackage("screen", "Core CLI", "Lightweight terminal screen manager"),
    SoftwarePackage("neovim", "Core CLI", "Vim-fork focused on extensibility and speed"),
    SoftwarePackage("nano", "Core CLI", "Simple, user-friendly command-line text editor"),
    SoftwarePackage("tree", "Core CLI", "Directory structure recursive visualizer"),
    SoftwarePackage("jq", "Core CLI", "Lightweight and flexible command-line JSON processor"),
    SoftwarePackage("fastfetch", "Core CLI", "Neofetch-like tool for showing system information"),
    SoftwarePackage("ncdu", "Core CLI", "Disk usage analyzer with ncurses interface"),
    SoftwarePackage("rsync", "Core CLI", "Fast and versatile file-copying and backup tool"),
    SoftwarePackage("zsh", "Core CLI", "Advanced programmable command shell"),

    # Development & Python
    SoftwarePackage("git", "Development", "Fast, distributed version control system"),
    SoftwarePackage("python-pipx", "Development", "Install and run Python CLI apps in isolated virtual environments"),
    SoftwarePackage("python-pip", "Development", "The PyPA recommended tool for installing Python packages"),
    SoftwarePackage("strace", "Development", "Diagnostic, debugging and system call tracer"),

    # Networking & Remote Access
    SoftwarePackage("wireguard-tools", "Networking", "Next-gen fast and secure VPN tunnel"),
    SoftwarePackage("iperf3", "Networking", "Bandwidth and network throughput testing tool"),
    SoftwarePackage("ethtool", "Networking", "Utility for querying and controlling network devices"),
    SoftwarePackage("tcpdump", "Networking", "Command-line packet analyzer"),
    SoftwarePackage("nmap", "Networking", "Network exploration tool and security / port scanner"),
    SoftwarePackage("bind-tools", "Networking", "DNS query tools (dig, host, nslookup)"),
    SoftwarePackage("curl", "Networking", "Command-line tool for transferring data with URLs"),
    SoftwarePackage("wget", "Networking", "Network utility to retrieve files from the Web"),
    SoftwarePackage("socat", "Networking", "Multipurpose bidirectional relay tool"),
    SoftwarePackage("iftop", "Networking", "Real-time console bandwidth monitor"),

    # Wireless & Wi-Fi Management
    SoftwarePackage("wpa_supplicant", "Wireless", "WPA/WPA2/WPA3 wireless client daemon (required for wlan0 WiFi)"),
    SoftwarePackage("iwd", "Wireless", "Intel Wireless Daemon - lightweight standalone Wi-Fi agent"),
    SoftwarePackage("wireless_tools", "Wireless", "Legacy Linux Wireless Extensions tools (iwconfig, iwlist)"),
    SoftwarePackage("iw", "Wireless", "Modern nl80211 based CLI utility for wireless devices"),

    # Printing & Imaging
    SoftwarePackage("cups", "Printing", "Open-source print server standard for Unix/Linux"),
    SoftwarePackage("cups-filters", "Printing", "OpenPrinting CUPS filters and backends"),
    SoftwarePackage("hplip", "Printing", "HP Linux Imaging and Printing driver and management suite"),

    # Hardware & Low-Level Bus
    SoftwarePackage("i2c-tools", "Hardware", "Heterogeneous I2C tools for SBC hardware hacking"),
    SoftwarePackage("lm_sensors", "Hardware", "Hardware health monitoring for temperatures & voltages"),
    SoftwarePackage("usbutils", "Hardware", "USB device inspection utilities (lsusb)"),
    SoftwarePackage("pciutils", "Hardware", "PCI bus inspection utilities (lspci)"),

    # Headless Server & IoT
    SoftwarePackage("adguardhome", "Services", "Network-wide ads & tracking blocking DNS server"),
    SoftwarePackage("dnsmasq", "Services", "Lightweight DHCP and caching DNS server"),
    SoftwarePackage("unbound", "Services", "Validating, recursive, caching DNS resolver"),
    SoftwarePackage("avahi", "Services", "mDNS/DNS-SD (ZeroConf, access via .local hostname)"),
    SoftwarePackage("samba", "Services", "Windows-compatible SMB network file sharing"),
    SoftwarePackage("chrony", "Services", "Versatile Network Time Protocol (NTP) daemon"),
    SoftwarePackage("fail2ban", "Services", "Ban hosts that cause multiple authentication errors"),
    SoftwarePackage("mosquitto", "Services", "Lightweight MQTT broker for IoT home automation"),
    SoftwarePackage("caddy", "Services", "Modern, memory-efficient web server with automatic HTTPS"),
    SoftwarePackage("nginx", "Services", "High-performance HTTP server and reverse proxy"),
    SoftwarePackage("lighttpd", "Services", "Memory-efficient web server optimized for embedded boards"),
    SoftwarePackage("tailscale", "Services", "Zero-config mesh VPN based on WireGuard"),
    SoftwarePackage("rclone", "Services", "Sync files and directories to and from cloud storage"),
    SoftwarePackage("syncthing", "Services", "Continuous peer-to-peer file synchronization"),

    # Torrents & Downloads (DietPi-inspired)
    SoftwarePackage("transmission-cli", "Torrents & Downloads", "Fast BitTorrent client with lightweight Web UI (port 9091)"),
    SoftwarePackage("qbittorrent-nox", "Torrents & Downloads", "Feature-rich BitTorrent client with Web UI (port 8080)"),
    SoftwarePackage("deluge", "Torrents & Downloads", "BitTorrent client/daemon with Web UI (port 8112)"),
    SoftwarePackage("jackett", "Torrents & Downloads", "Torrent indexer proxy API server (Web UI port 9117, standalone binary)"),
    SoftwarePackage("aria2", "Torrents & Downloads", "High-speed multi-protocol download manager (HTTP/FTP/BitTorrent/Metalink)"),
    SoftwarePackage("rtorrent", "Torrents & Downloads", "Ncurses BitTorrent client with ultra-low memory footprint"),
    SoftwarePackage("nzbget", "Torrents & Downloads", "Lightweight and efficient Usenet downloader with Web UI (port 6789)"),
    SoftwarePackage("btfs", "Torrents & Downloads", "BitTorrent filesystem based on FUSE (stream torrents as mounts)"),
    SoftwarePackage("yt-dlp", "Torrents & Downloads", "CLI audio/video downloader from YouTube and hundreds of streaming sites"),

    # Media & Audio Streaming
    SoftwarePackage("minidlna", "Media & Audio", "Lightweight DLNA/UPnP-AV media server (ReadyMedia)"),
    SoftwarePackage("mpd", "Media & Audio", "Music Player Daemon for network audio streaming and playback"),
    SoftwarePackage("shairport-sync", "Media & Audio", "AirPlay audio player with multi-room sync"),

    # File Sharing, Storage & Backups
    SoftwarePackage("nfs-utils", "Storage & Backups", "Network File System (NFSv4) server and client utilities"),
    SoftwarePackage("vsftpd", "Storage & Backups", "Very secure, fast, and lightweight FTP daemon"),
    SoftwarePackage("restic", "Storage & Backups", "Fast, secure, and encrypted backup program"),
    SoftwarePackage("borg", "Storage & Backups", "Deduplicating backup archiver with compression and encryption"),

    # System & Web Tools
    SoftwarePackage("vnstat", "System Tools", "Console and background network traffic monitor and logger"),
    SoftwarePackage("darkstat", "System Tools", "Lightweight packet sniffer and web-based traffic analyzer"),
    SoftwarePackage("goaccess", "System Tools", "Real-time web log analyzer and interactive console viewer"),
    SoftwarePackage("cronie", "System Tools", "Standard crond daemon for scheduled background tasks"),
    SoftwarePackage("certbot", "System Tools", "Automatic Let's Encrypt TLS/SSL certificate manager"),
    SoftwarePackage("sqlite", "System Tools", "Self-contained serverless SQL database engine"),
]


class PackageManager:
    def __init__(self) -> None:
        self._packages: List[SoftwarePackage] = list(DEFAULT_PACKAGES)

    def refresh_installed_status(self) -> None:
        """Queries local pacman database and custom paths to update installed state for all packages."""
        installed_set: set[str] = set()
        if shutil.which("pacman"):
            try:
                # Query all installed packages once
                out = subprocess.check_output(
                    ["pacman", "-Q"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                installed_set = {line.split()[0] for line in out.splitlines() if line.strip()}
            except Exception:
                pass

        for pkg in self._packages:
            if pkg.name == "jackett":
                # Check for standalone binary in /opt/Jackett/jackett or in PATH
                pkg.installed = (shutil.which("jackett") is not None) or shutil.os.path.exists("/opt/Jackett/jackett")
            else:
                if installed_set:
                    pkg.installed = pkg.name in installed_set
                elif shutil.which("pacman"):
                    res = subprocess.run(
                        ["pacman", "-Q", pkg.name],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    pkg.installed = (res.returncode == 0)

    def get_categories(self) -> List[str]:
        """Returns sorted list of unique package categories."""
        cats = sorted(list({p.category for p in self._packages}))
        return cats

    def get_packages_by_category(self, category: Optional[str] = None) -> List[SoftwarePackage]:
        """Returns packages filtered by category, or all packages if category is None."""
        if category:
            return [p for p in self._packages if p.category == category]
        return self._packages

    @staticmethod
    def install_packages(package_names: List[str]) -> Generator[str, None, int]:
        """
        Runs pacman -S --needed --noconfirm for specified packages,
        yielding console output line by line.
        """
        if not package_names:
            yield "No packages selected for installation.\n"
            return 0

        cmd = ["pacman", "-S", "--needed", "--noconfirm"] + package_names
        yield f"Executing: {' '.join(cmd)}\n\n"

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        if proc.stdout:
            for line in proc.stdout:
                yield line

        proc.wait()
        rc = proc.returncode
        if rc == 0:
            yield "\nInstallation completed successfully!\n"
        else:
            yield f"\nInstallation exited with code {rc}.\n"
        return rc

    @staticmethod
    def update_databases() -> Generator[str, None, int]:
        """Runs pacman -Sy to synchronize package databases."""
        cmd = ["pacman", "-Sy"]
        yield f"Executing: {' '.join(cmd)}\n\n"
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if proc.stdout:
            for line in proc.stdout:
                yield line
        proc.wait()
        return proc.returncode

    @staticmethod
    def clean_cache() -> Generator[str, None, int]:
        """Runs pacman -Sc --noconfirm to clean cached tarballs."""
        cmd = ["pacman", "-Sc", "--noconfirm"]
        yield f"Executing: {' '.join(cmd)}\n\n"
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if proc.stdout:
            for line in proc.stdout:
                yield line
        proc.wait()
        return proc.returncode
