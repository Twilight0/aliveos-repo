# Guide: Creating a Lean Redistributable Base Image for Orange Pi Zero

This guide details the complete process for creating, sanitizing, shrinking, and compressing a minimal **Arch Linux ARM** base image for the **Orange Pi Zero (Allwinner H2+)** from an SD card.

---

## 1. Overview & Image Goals

- **Target Board:** Orange Pi Zero (Allwinner H2+, 256MB / 512MB RAM).
- **Base OS:** Arch Linux ARM (Sunxi mainline kernel 6.x/7.x).
- **Raw SD Card Size:** ~15–16 GB.
- **Actual Content Size:** ~1.5–1.8 GB.
- **Compressed Output:** **`~400–600 MB`** (`.img.xz`).
- **Compatibility:** Can be burned to any SD card $\ge$ 2 GB using BalenaEtcher, Raspberry Pi Imager, or `dd`.

---

## 2. Included Fixes & Out-of-the-Box Features

1. **U-Boot Direct Boot (No Bloated Initramfs):**
   - Configured `/boot/boot.cmd` and compiled `/boot/boot.scr` with `bootz ${kernel_addr_r} - ${fdt_addr_r}`.
   - Prevents fatal U-Boot memory allocation errors (`ramdisk - allocation error`) on 256MB boards.
   - `/etc/mkinitcpio.d/linux-armv7.preset` set to `PRESETS=()` to prevent auto-regeneration.
2. **Voltage Brownout Protection:**
   - Kernel boot argument `cpufreq.default_governor=performance` pins initial voltage to 1.30V.
   - `cpufreq-governor.service` startup service prevents unstable 1.10V discrete regulator brownouts.
3. **Automatic Filesystem Recovery:**
   - Kernel command line includes `fsck.mode=force fsck.repair=yes panic=10` to automatically recover from unclean power cuts without halting boot.
4. **Pre-installed orangepi-config:**
   - Full TUI configuration and diagnostics utility pre-installed in `/usr/local/bin/orangepi-config`.
5. **Remote Web TUI Access:**
   - `ttyd` service configured on port `46363` (`orangepi-config-web.service`).

---

## 3. Preparation & System Sanitization (Before Dumping)

Before dumping the SD card, remove machine-specific files, caches, and histories so the image is clean and secure for other users:

### Step 3.1: Mount Partition
```bash
sudo mkdir -p /mnt/opizero
sudo mount /dev/mmcblk0p1 /mnt/opizero
```

### Step 3.2: Clean Package Cache & Logs
```bash
# Clean pacman cache
sudo rm -rf /mnt/opizero/var/cache/pacman/pkg/*

# Truncate log files
sudo find /mnt/opizero/var/log -type f -exec truncate -s 0 {} +
sudo rm -rf /mnt/opizero/var/log/journal/*

# Remove temporary files
sudo rm -rf /mnt/opizero/tmp/* /mnt/opizero/var/tmp/*
sudo rm -f /mnt/opizero/root/.bash_history /mnt/opizero/home/alarm/.bash_history
```

### Step 3.3: Remove SSH Host Keys (First-Boot Regeneration)
To prevent all users from sharing identical SSH keys:
```bash
sudo rm -f /mnt/opizero/etc/ssh/ssh_host_*
```

### Step 3.4: Install First-Boot Auto-Expand Service
To allow the 2GB image to automatically expand to fill whatever SD card size the user flashes it onto:

Create `/mnt/opizero/etc/systemd/system/rpi-resizerootfs.service`:
```ini
[Unit]
Description=Auto-expand root filesystem on first boot
After=local-fs.target
DefaultDependencies=no

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/auto-expand-root.sh
RemainAfterExit=yes

[Install]
WantedBy=basic.target
```

Create `/mnt/opizero/usr/local/sbin/auto-expand-root.sh`:
```bash
#!/bin/bash
set -e
# Grow partition 1 to 100% of the disk
PART_DEV=$(findmnt / -o SOURCE -n)
DISK_DEV=$(lsblk -no PKNAME "$PART_DEV")
parted -s "/dev/$DISK_DEV" resizepart 1 100%
resize2fs "$PART_DEV"

# Disable this service after success
systemctl disable rpi-resizerootfs.service
rm -f /etc/systemd/system/rpi-resizerootfs.service /usr/local/sbin/auto-expand-root.sh
```
```bash
sudo chmod +x /mnt/opizero/usr/local/sbin/auto-expand-root.sh
sudo ln -sf /etc/systemd/system/rpi-resizerootfs.service /mnt/opizero/etc/systemd/system/basic.target.wants/rpi-resizerootfs.service
```

### Step 3.5: Unmount SD Card
```bash
sudo umount /mnt/opizero
```

---

## 4. Shrinking the Filesystem & Partition

### Step 4.1: Filesystem Check & Minimum Resize
```bash
# Check filesystem
sudo fsck.ext4 -fy /dev/mmcblk0p1

# Shrink ext4 filesystem to minimal possible size
sudo resize2fs -M /dev/mmcblk0p1
```
Note the number of blocks reported by `resize2fs` (e.g., `450000 (4k) blocks` = `1800 MB`).

### Step 4.2: Shrink Partition 1 with Parted
Calculate a safe buffer above the filesystem (e.g., filesystem size + 150MB margin):
```bash
# If filesystem is ~1800MB, set partition end to 2000MB
sudo parted /dev/mmcblk0 resizepart 1 2048MB
```

---

## 5. Dumping the Raw Image

The Allwinner bootloader requires:
- Sector 0: MBR partition table.
- Offset 8 KB: `u-boot-sunxi-with-spl.bin` (U-Boot SPL).
- Offset 1024 KB (Sector 2048): Partition 1 start.

Dump only the used portion of the disk (e.g., 2050 MB):
```bash
sudo dd if=/dev/mmcblk0 of=orangepi-zero-archlinux-base.img bs=1M count=2050 status=progress conv=fsync
```

---

## 6. High-Ratio Compression

Compress the raw `.img` file with multi-threaded `xz`:
```bash
xz -T0 -9 -v orangepi-zero-archlinux-base.img
```
This produces `orangepi-zero-archlinux-base.img.xz` (~450 MB).

---

## 7. Flashing Instructions for End Users

Users can flash the `.img.xz` directly using:
- **Graphical Tool:** [BalenaEtcher](https://etcher.balena.io/) or [Raspberry Pi Imager](https://www.raspberrypi.com/software/) (supports `.xz` directly without manual decompression).
- **Command Line:**
  ```bash
  xzcat orangepi-zero-archlinux-base.img.xz | sudo dd of=/dev/sdX bs=4M status=progress conv=fsync
  ```

### Default Credentials for Users:
- **Root Login:** `root` / `GoToDev2026!!!!`
- **Default User:** `alarm` / `alarm`
- **Web TUI Access:** `http://<board-ip>:46363` (User: `admin` / Password: `GoToDev2026!!!!`)
