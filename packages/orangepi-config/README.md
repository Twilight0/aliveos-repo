# orangepi-config

**orangepi-config** is a lightweight, responsive Terminal User Interface (TUI) designed for **Orange Pi Zero (Allwinner H2+/H3)** and similar low-memory single-board computers (SBCs) running **Arch Linux ARM**.

Built using [`urwid`](https://urwid.org/), it is engineered to consume minimal RAM (running comfortably in under 20MB resident memory) while providing full hardware monitoring, system diagnostics, board feature toggles, network configuration, and package management over serial consoles, SSH sessions, and web browsers.

![Terminal TUI Preview](https://raw.githubusercontent.com/Twilight0/orangepi-config/main/docs/preview.png)

---

## Features

### 📊 Live Diagnostics & System Health (F1)
- Real-time CPU frequency, per-core stats, and SoC temperature monitoring (`/sys/class/thermal`).
- Memory & Swap breakdown (designed specifically for 256MB / 512MB RAM constraints).
- Storage utilization on root and attached storage.
- System load averages, uptime, and active network interfaces (`eth0`, `wlan0`).
- Auto-refreshing dashboard with configurable polling.

### ⚙️ Board Features & Hardware Controls (F2)
- **CPU Governor:** Easily switch governors on the fly (`schedutil`, `performance`, `ondemand`).
- **Persistent Governor:** Governor choices are automatically saved to `/etc/default/cpufreq` and persisted across reboots via `cpufreq-governor.service`.
- **Failsafe Voltage Protection:** Prevents 1.10V discrete regulator brownouts on Orange Pi Zero H2+.
- **CPU Cores:** Hotplug / toggle CPU cores (CPU1–3) for ultra low-power scenarios.
- **On-board LEDs:** Control triggers (`heartbeat`, `cpu0`, `mmc0`, `none`, `default-on`) and brightness for red status and green power LEDs.

### 🌐 Network & Wireless Management (F3)
- **Interface Inspection:** Real-time carrier detection, MAC addresses, IPv4, gateway, and DNS for `eth0` and `wlan0`.
- **IP Configuration:** One-click toggle between **DHCP** and **Static IP** via `systemd-networkd`.
- **XR819 Hardware Recovery & Diagnostics:**
  - Firmware presence check (`boot_xr819.bin`, `fw_xr819.bin`, `sdd_xr819.bin` in `/lib/firmware/xr819`).
  - **Disable WiFi Sleep Bug:** Fixes Xunlong XR819 SDIO sleep timeouts and connection drops (`iw dev wlan0 set power_save off`).
  - **SDIO Driver Reload:** Unloads and reloads `xradio_wlan` to revive frozen wireless hardware without rebooting.
  - **RFKill Status & Unblock:** Quick one-click unblock for wireless radios.
- **Wi-Fi Scanner & Connect:** Live wireless network channel scanner and interactive WPA2/WPA3 passphrase setup.

### 📦 Headless & Server Package Installer (F4)
- **Intuitive Category Navigation:**
  - Press `Tab` to switch focus between category bar and package list.
  - Press `c` or `]` to cycle to next category; `[` for previous category.
  - Press number keys `1`–`8` to jump directly to any category.
  - Press `Space` to select/unselect packages for batch installation.
- Curated package catalog for Orange Pi Zero servers:
  - **Core CLI:** `htop`, `btop`, `tmux`, `screen`, `neovim`, `nano`, `tree`, `jq`, `fastfetch`, `ncdu`, `rsync`, `zsh`.
  - **Development:** `git`, `python-pipx`, `python-pip`, `strace`.
  - **Networking:** `wireguard-tools`, `iperf3`, `ethtool`, `tcpdump`, `nmap`, `bind-tools`, `curl`, `wget`, `socat`, `iftop`.
  - **Wireless:** `wpa_supplicant`, `iwd`, `wireless_tools`, `iw`.
  - **Printing:** `cups`, `cups-filters`, `hplip`.
  - **Hardware I/O:** `i2c-tools`, `lm_sensors`, `usbutils`, `pciutils`.
  - **Services & IoT:** `adguardhome`, `dnsmasq`, `avahi` (mDNS), `samba`, `chrony` (NTP), `fail2ban`, `mosquitto` (MQTT), `caddy`, `nginx`, `lighttpd`, `tailscale`, `rclone`, `syncthing`.
- Live package status check (`[Installed]` vs `[Available]`).
- Interactive batch selection and one-click pacman installation modal.

### 🛠️ System Maintenance (F5)
- Package database synchronization (`pacman -Sy`) and full upgrades.
- Pacman cache cleaning to save precious SD card space.
- Hostname management.
- Clean system reboot and poweroff.

### 💻 Interactive Terminal Access (F6)
- **Direct Shell Drop-in:** Spawn native interactive shells directly in the TUI, SSH session, serial console, or web browser.
- **Root or Regular User:**
  - Launch superuser root shell (`/bin/bash -l` / `sudo -i`).
  - Launch regular user shell (`su - alarm` or any non-root account).
  - Launch standard `/bin/login` system prompt.
  - Switch to any custom username on the system.
- **Single Command Runner:** Execute commands (`ip addr`, `lsblk`, `dmesg`, custom scripts) with real-time streaming output logs without leaving the app.
- **Seamless Return:** Simply type `exit` or press `Ctrl+D` to return instantly to `orangepi-config`.

---

## Remote Access via Browser (Port 46363)

`orangepi-config` includes a systemd service running `ttyd` to provide instant web-based TUI access:
- **Local:** `http://<device-ip>:46363`
- **Default Login:** `admin` / `admin`
- Full mouse, function key, and terminal resize support in under 1MB RAM footprint.
- **Custom Credentials:** Set `TTYD_CREDENTIALS="admin:your_new_password"` in `/etc/default/orangepi-config` to override.
- **Security Policy:** Direct shell escalation to root or user accounts from the terminal tab is disabled to ensure system integrity. For interactive shell access, connect securely via SSH.

---

## Keyboard Shortcuts & Navigation

| Key | Action |
| :--- | :--- |
| **`F1` – `F6`** | Switch between tabs (Status, Hardware, Network, Software, System, Terminal) |
| **`Tab`** | Switch focus between controls (in Software tab: toggle Category bar / Package list) |
| **`c` / `]` / `[`** | Cycle forward / backward through software categories |
| **`1` – `8`** | Jump directly to category (1: All, 2: Core, 3: Dev, 4: Net, 5: Print, 6: HW, 7: Svc, 8: WiFi) |
| **`Space`** | Toggle package checkbox or button |
| **`Enter`** | Activate focused button / submit modal |
| **`q` / `Q`** | Quit application |

---

## Installation (Arch Linux / Arch Linux ARM)

### Standard Pacman Package Build:
```bash
git clone https://github.com/Twilight0/orangepi-config.git
cd orangepi-config
makepkg -si
```

### Install Pre-built Package:
```bash
sudo pacman -U orangepi-config-0.1.0-1-any.pkg.tar.zst
```

---

## Project Documentation & Guides

- [Creating a Lean Base OS Image](file:///home/twilight/Projects/orangepi-config/docs/BASE_IMAGE_GUIDE.md)
- [Hardware Quirks & Board Failsafes](file:///home/twilight/Projects/orangepi-config/docs/HARDWARE_QUIRKS_AND_FAILSAFES.md)
- [Remote Web Access Configuration](file:///home/twilight/Projects/orangepi-config/docs/REMOTE_ACCESS_TTYD.md)

---

## License
MIT License © 2026 Twilight0.
