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
    SoftwarePackage("htop", "Remote Access & Shells", "Interactive process viewer and CPU/RAM monitor"),
    SoftwarePackage("btop", "Monitoring & Stats", "Modern resource monitor with aesthetic UI"),
    SoftwarePackage("glances", "Monitoring & Stats", "Cross-platform curses and web-based system monitoring tool"),
    SoftwarePackage("netdata", "Monitoring & Stats", "Real-time performance and health monitoring web dashboard (port 19999)"),
    SoftwarePackage("prometheus", "Monitoring & Stats", "Cloud-native metrics collector and monitoring system"),
    SoftwarePackage("goaccess", "Monitoring & Stats", "Real-time web log analyzer and interactive console viewer"),
    SoftwarePackage("vnstat", "Monitoring & Stats", "Background network traffic monitor and bandwidth logger"),
    SoftwarePackage("darkstat", "Monitoring & Stats", "Lightweight packet sniffer and web-based traffic analyzer (port 667)"),
    SoftwarePackage("monit", "Monitoring & Stats", "Lightweight process, file, directory, and device supervisor daemon"),
    SoftwarePackage("sysstat", "Monitoring & Stats", "Performance monitoring tools for Linux (sar, iostat, mpstat)"),
    SoftwarePackage("iftop", "Monitoring & Stats", "Real-time console bandwidth monitor by network connection"),
    SoftwarePackage("iotop", "Monitoring & Stats", "Python-based I/O monitor displaying disk activity per process"),
    SoftwarePackage("nethogs", "Monitoring & Stats", "Small 'net top' tool grouping bandwidth by process"),

    # Remote Access & Shells
    SoftwarePackage("openssh", "Remote Access & Shells", "Secure Shell (SSH) protocol server and client"),
    SoftwarePackage("ttyd", "Remote Access & Shells", "Share terminal over the web with WebSocket support (port 46363)"),
    SoftwarePackage("tmux", "Remote Access & Shells", "Terminal multiplexer with persistent sessions and split panes"),
    SoftwarePackage("screen", "Remote Access & Shells", "Lightweight terminal screen manager"),
    SoftwarePackage("mosh", "Remote Access & Shells", "Mobile Shell that supports roaming and intermittent connectivity"),
    SoftwarePackage("neovim", "Remote Access & Shells", "Vim-fork focused on extensibility and speed"),
    SoftwarePackage("nano", "Remote Access & Shells", "Simple, user-friendly command-line text editor"),
    SoftwarePackage("zsh", "Remote Access & Shells", "Advanced programmable command shell"),
    SoftwarePackage("fish", "Remote Access & Shells", "Smart and user-friendly interactive command line shell"),
    SoftwarePackage("bash-completion", "Remote Access & Shells", "Programmable completion functions for Bash"),

    # File Servers & Cloud
    SoftwarePackage("samba", "File Servers & Cloud", "Windows-compatible SMB network file sharing"),
    SoftwarePackage("nfs-utils", "File Servers & Cloud", "Network File System (NFSv4) server and client utilities"),
    SoftwarePackage("vsftpd", "File Servers & Cloud", "Lightweight, secure, and fast FTP daemon"),
    SoftwarePackage("syncthing", "File Servers & Cloud", "Continuous peer-to-peer file synchronization"),
    SoftwarePackage("nextcloud", "File Servers & Cloud", "Self-hosted productivity and private cloud storage platform"),
    SoftwarePackage("rclone", "File Servers & Cloud", "Sync files and directories to and from cloud storage"),
    SoftwarePackage("rsync", "File Servers & Cloud", "Fast and versatile file-copying and backup tool"),

    # Web Servers & Stacks
    SoftwarePackage("caddy", "Web Servers & Stacks", "Modern, memory-efficient web server with automatic HTTPS"),
    SoftwarePackage("nginx", "Web Servers & Stacks", "High-performance HTTP server and reverse proxy"),
    SoftwarePackage("apache", "Web Servers & Stacks", "Powerful, feature-rich HTTP web server"),
    SoftwarePackage("lighttpd", "Web Servers & Stacks", "Memory-efficient web server optimized for embedded boards"),
    SoftwarePackage("php", "Web Servers & Stacks", "Popular general-purpose scripting language for web servers"),
    SoftwarePackage("php-fpm", "Web Servers & Stacks", "FastCGI Process Manager for PHP (for Nginx/Caddy/Lighttpd)"),
    SoftwarePackage("php-sqlite", "Web Servers & Stacks", "SQLite database driver extension for PHP"),
    SoftwarePackage("certbot", "Web Servers & Stacks", "Automatic Let's Encrypt TLS/SSL certificate manager"),
    SoftwarePackage("certbot-nginx", "Web Servers & Stacks", "Nginx plugin for Certbot TLS automation"),

    # Databases & In-Memory
    SoftwarePackage("sqlite", "Databases & In-Memory", "Self-contained serverless SQL database engine"),
    SoftwarePackage("mariadb", "Databases & In-Memory", "Fast, robust community fork of MySQL relational database"),
    SoftwarePackage("postgresql", "Databases & In-Memory", "Advanced, enterprise-grade object-relational SQL database"),
    SoftwarePackage("valkey", "Databases & In-Memory", "High-performance in-memory key-value data store (Redis fork)"),
    SoftwarePackage("memcached", "Databases & In-Memory", "High-performance distributed memory object caching system"),
    SoftwarePackage("influxdb", "Databases & In-Memory", "Scalable time-series database for metrics and IoT sensor logging"),

    # Torrents & Downloads (DietPi-inspired)
    SoftwarePackage("transmission-cli", "Torrents & Downloads", "Fast BitTorrent client with lightweight Web UI (port 9091)"),
    SoftwarePackage("qbittorrent-nox", "Torrents & Downloads", "Feature-rich BitTorrent client with Web UI (port 8080)"),
    SoftwarePackage("deluge", "Torrents & Downloads", "BitTorrent client/daemon with Web UI (port 8112)"),
    SoftwarePackage("rtorrent", "Torrents & Downloads", "Ncurses BitTorrent client with ultra-low memory footprint"),
    SoftwarePackage("aria2", "Torrents & Downloads", "High-speed multi-protocol download manager (HTTP/FTP/BitTorrent/Metalink)"),
    SoftwarePackage("nzbget", "Torrents & Downloads", "Lightweight and efficient Usenet downloader with Web UI (port 6789)"),
    SoftwarePackage("amule", "Torrents & Downloads", "All-platform eMule P2P file-sharing client (headless ed2k)"),
    SoftwarePackage("yt-dlp", "Torrents & Downloads", "CLI audio/video downloader from YouTube and streaming sites"),
    SoftwarePackage("jackett", "Torrents & Downloads", "Torrent indexer proxy API server (Web UI port 9117, standalone binary)"),

    # Media & Audio Streaming
    SoftwarePackage("minidlna", "Media & Audio", "Lightweight DLNA/UPnP-AV media server (ReadyMedia)"),
    SoftwarePackage("gerbera", "Media & Audio", "Highly configurable UPnP media server with Web UI"),
    SoftwarePackage("mpd", "Media & Audio", "Music Player Daemon for network audio streaming and playback"),
    SoftwarePackage("mpc", "Media & Audio", "Minimalist command-line client for Music Player Daemon (MPD)"),
    SoftwarePackage("ncmpcpp", "Media & Audio", "Ncurses music player client for MPD with visualizer"),
    SoftwarePackage("shairport-sync", "Media & Audio", "AirPlay audio player with multi-room synchronization"),
    SoftwarePackage("umurmur", "Media & Audio", "Ultra-lightweight embedded Mumble voice chat server (<5MB RAM)"),
    SoftwarePackage("mumble-server", "Media & Audio", "Official full-featured Mumble voice chat server daemon (Murmur)"),
    SoftwarePackage("alsa-utils", "Media & Audio", "Advanced Linux Sound Architecture CLI utilities (alsamixer, aplay)"),
    SoftwarePackage("flac", "Media & Audio", "Free Lossless Audio Codec encoder/decoder tools"),

    # DNS, Security & VPN
    SoftwarePackage("adguardhome", "DNS, Security & VPN", "Network-wide ads & tracking blocking DNS server (Web UI port 3000)"),
    SoftwarePackage("unbound", "DNS, Security & VPN", "Validating, recursive, caching DNS resolver with DNSSEC"),
    SoftwarePackage("dnsmasq", "DNS, Security & VPN", "Lightweight DHCP and caching DNS server"),
    SoftwarePackage("bind", "DNS, Security & VPN", "BIND DNS server and query utilities (dig, host, nslookup)"),
    SoftwarePackage("wireguard-tools", "DNS, Security & VPN", "Next-gen fast, modern and secure VPN tunnel"),
    SoftwarePackage("tailscale", "DNS, Security & VPN", "Zero-config mesh VPN based on WireGuard"),
    SoftwarePackage("cloudflared", "DNS, Security & VPN", "Cloudflare Zero Trust tunnel and DNS-over-HTTPS client"),
    SoftwarePackage("openvpn", "DNS, Security & VPN", "Robust and highly configurable SSL/TLS VPN solution"),
    SoftwarePackage("tor", "DNS, Security & VPN", "Anonymizing overlay network client and SOCKS5 proxy"),
    SoftwarePackage("privoxy", "DNS, Security & VPN", "Privacy enhancing web proxy with advanced filtering capabilities"),
    SoftwarePackage("fail2ban", "DNS, Security & VPN", "Ban hosts that cause multiple authentication errors"),
    SoftwarePackage("ufw", "DNS, Security & VPN", "Program for managing a netfilter firewall (Uncomplicated Firewall)"),

    # Home & Git Servers
    SoftwarePackage("mosquitto", "Home & Git Servers", "Lightweight MQTT message broker for IoT and home automation"),
    SoftwarePackage("vaultwarden", "Home & Git Servers", "Lightweight Bitwarden-compatible password manager in Rust"),
    SoftwarePackage("gitea", "Home & Git Servers", "Painless, lightweight self-hosted Git service in Go (Web UI port 3000)"),
    SoftwarePackage("forgejo", "Home & Git Servers", "Community-governed lightweight Git forge fork of Gitea"),

    # Printing & Scanning
    SoftwarePackage("cups", "Printing & Scanning", "Open-source print server standard for Unix/Linux (port 631)"),
    SoftwarePackage("cups-filters", "Printing & Scanning", "OpenPrinting CUPS filters and backends"),
    SoftwarePackage("cups-pdf", "Printing & Scanning", "Virtual PDF printer backend for CUPS"),
    SoftwarePackage("sane", "Printing & Scanning", "Scanner Access Now Easy - backend for scanners and All-in-Ones"),
    SoftwarePackage("sane-airscan", "Printing & Scanning", "SANE backend for AirScan (eSCL) and WSD driverless scanners"),
    SoftwarePackage("hplip", "Printing & Scanning", "HP Linux Imaging and Printing driver and management suite"),

    # Storage & Backups
    SoftwarePackage("restic", "Storage & Backups", "Fast, secure, and encrypted backup program"),
    SoftwarePackage("borg", "Storage & Backups", "Deduplicating backup archiver with compression and encryption"),
    SoftwarePackage("duplicity", "Storage & Backups", "Encrypted bandwidth-efficient backup using librsync"),
    SoftwarePackage("smartmontools", "Storage & Backups", "Control and monitor S.M.A.R.T. storage drive health"),
    SoftwarePackage("hdparm", "Storage & Backups", "Tune hard drive performance and spindown parameters"),
    SoftwarePackage("btrfs-progs", "Storage & Backups", "Utilities for managing Btrfs filesystems"),
    SoftwarePackage("dosfstools", "Storage & Backups", "FAT/FAT32 filesystem creation and checking utilities"),
    SoftwarePackage("e2fsprogs", "Storage & Backups", "Ext2/3/4 filesystem management utilities"),
    SoftwarePackage("exfatprogs", "Storage & Backups", "Userspace utilities for exFAT filesystems"),
    SoftwarePackage("ntfs-3g", "Storage & Backups", "Read/write NTFS driver for external Windows hard drives"),
    SoftwarePackage("f2fs-tools", "Storage & Backups", "Flash-Friendly File System (F2FS) tools for SD cards and SSDs"),
    SoftwarePackage("parted", "Storage & Backups", "Disk partition manipulation program"),

    # Development & CLI Utilities
    SoftwarePackage("git", "Development & CLI", "Fast, distributed version control system"),
    SoftwarePackage("git-lfs", "Development & CLI", "Git extension for versioning large files"),
    SoftwarePackage("python", "Development & CLI", "Powerful general-purpose programming language"),
    SoftwarePackage("python-pip", "Development & CLI", "The PyPA recommended tool for installing Python packages"),
    SoftwarePackage("python-pipx", "Development & CLI", "Install and run Python CLI apps in isolated virtual environments"),
    SoftwarePackage("gcc", "Development & CLI", "The GNU Compiler Collection (C/C++ compiler)"),
    SoftwarePackage("make", "Development & CLI", "GNU utility for directed compilation of code"),
    SoftwarePackage("cmake", "Development & CLI", "Cross-platform open-source build system generator"),
    SoftwarePackage("strace", "Development & CLI", "Diagnostic, debugging and system call tracer"),
    SoftwarePackage("lsof", "Development & CLI", "Lists open files and listening network sockets"),
    SoftwarePackage("jq", "Development & CLI", "Lightweight and flexible command-line JSON processor"),
    SoftwarePackage("tree", "Development & CLI", "Directory structure recursive visualizer"),
    SoftwarePackage("ncdu", "Development & CLI", "Disk usage analyzer with ncurses interface"),
    SoftwarePackage("fastfetch", "Development & CLI", "Neofetch-like tool for showing system information"),
    SoftwarePackage("inxi", "Development & CLI", "Full-featured system and hardware information CLI tool"),
    SoftwarePackage("bat", "Development & CLI", "Cat clone with syntax highlighting and Git integration"),
    SoftwarePackage("fzf", "Development & CLI", "General-purpose command-line fuzzy finder"),
    SoftwarePackage("ripgrep", "Development & CLI", "Extremely fast line-oriented search tool (rg)"),
    SoftwarePackage("fd", "Development & CLI", "Simple, fast, and user-friendly alternative to 'find'"),
    SoftwarePackage("speedtest-cli", "Development & CLI", "Command line interface for testing internet bandwidth"),

    # Hardware & Wireless
    SoftwarePackage("wpa_supplicant", "Hardware & Wireless", "WPA/WPA2/WPA3 wireless client daemon (required for wlan0 WiFi)"),
    SoftwarePackage("iwd", "Hardware & Wireless", "Intel Wireless Daemon - lightweight standalone Wi-Fi agent"),
    SoftwarePackage("wireless_tools", "Hardware & Wireless", "Legacy Linux Wireless Extensions tools (iwconfig, iwlist)"),
    SoftwarePackage("iw", "Hardware & Wireless", "Modern nl80211 based CLI utility for wireless devices"),
    SoftwarePackage("i2c-tools", "Hardware & Wireless", "Heterogeneous I2C tools for SBC hardware hacking"),
    SoftwarePackage("lm_sensors", "Hardware & Wireless", "Hardware health monitoring for temperatures & voltages"),
    SoftwarePackage("usbutils", "Hardware & Wireless", "USB device inspection utilities (lsusb)"),
    SoftwarePackage("pciutils", "Hardware & Wireless", "PCI bus inspection utilities (lspci)"),
    SoftwarePackage("ethtool", "Hardware & Wireless", "Utility for querying and controlling network devices"),
    SoftwarePackage("cronie", "Hardware & Wireless", "Standard crond daemon for scheduled background tasks"),
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
        and delegates standalone utilities (like Jackett) to their installers,
        yielding console output line by line.
        """
        if not package_names:
            yield "No packages selected for installation.\n"
            return 0

        install_jackett = "jackett" in package_names
        pacman_pkgs = [p for p in package_names if p != "jackett"]

        rc = 0
        if pacman_pkgs:
            cmd = ["pacman", "-S", "--needed", "--noconfirm"] + pacman_pkgs
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

        if install_jackett and rc == 0:
            yield "\nInstalling Jackett via standalone ARM32 installer...\n"
            jackett_cmd = ["/usr/bin/orangepi-install-jackett"]
            if not shutil.which("orangepi-install-jackett") and shutil.os.path.exists("/usr/share/orangepi-config/scripts/install-jackett.sh"):
                jackett_cmd = ["/usr/share/orangepi-config/scripts/install-jackett.sh"]

            yield f"Executing: {' '.join(jackett_cmd)}\n\n"
            proc = subprocess.Popen(
                jackett_cmd,
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
