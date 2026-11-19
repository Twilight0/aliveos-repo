# Hardware Quirks & Failsafes for Orange Pi Zero (Allwinner H2+)

This document records the technical hardware quirks, memory constraints, and kernel/U-Boot bugs discovered during development and the permanent failsafes implemented to resolve them.

---

## 1. The 256MB RAM / U-Boot Initramfs Allocation Failure

### The Issue:
- The Orange Pi Zero (H2+) base model has only **256 MB total DDR3 RAM** (physical memory mapped at `0x40000000`–`0x50000000`).
- During system updates or kernel package hooks, Arch Linux ARM runs `mkinitcpio`, creating an initramfs image (`/boot/initramfs-linux.img`). When generic distribution firmware packages (`linux-firmware-intel`, `linux-firmware-amd`, etc.) were pulled in, the image grew to 131.8 MB.
- In U-Boot's default memory map for Sunxi boards:
  - `kernel_addr_r`: `0x42000000`
  - `fdt_addr_r`: `0x43000000`
  - `ramdisk_addr_r`: `0x43300000`
- When U-Boot attempted to verify and relocate the initramfs, it failed fatally with:
  ```
  ERROR: Failed to allocate 0x7dba47e bytes below 0x4a000000.
  ramdisk - allocation error
  ```
  Even with a standard 14 MB initramfs, ARM `zImage` kernel self-decompression combined with U-Boot memory allocations caused unpredictable hangs during boot.

### The Solution:
1. **Direct Kernel Booting (No Initramfs):**
   Arch Linux ARM's Sunxi kernel has built-in MMC (`sunxi-mmc`) and ext4 drivers compiled directly into `zImage`. An initramfs is completely unnecessary for booting root on SD card.
2. **Permanent U-Boot Script ([`/boot/boot.cmd`](file:///boot/boot.cmd)):**
   ```bash
   part uuid ${devtype} ${devnum}:${bootpart} uuid
   setenv bootargs console=ttyS0,115200 root=PARTUUID=${uuid} rw rootwait cpufreq.default_governor=performance fsck.mode=force fsck.repair=yes panic=10
   setenv verbosity "1"

   if load ${devtype} ${devnum}:${bootpart} ${kernel_addr_r} /boot/zImage; then
       if load ${devtype} ${devnum}:${bootpart} ${fdt_addr_r} /boot/dtbs/${fdtfile}; then
           fdt addr ${fdt_addr_r}
           fdt resize
           setexpr fdtovaddr ${fdt_addr_r} + F000
           load ${devtype} ${devnum}:${bootpart} ${fdtovaddr} /boot/dtbs/overlay/sun8i-h3-analog-codec.dtbo && fdt apply ${fdtovaddr}
           bootz ${kernel_addr_r} - ${fdt_addr_r};
       fi;
   fi
   ```
   Compiled with `mkimage -C none -A arm -T script -d boot.cmd boot.scr`.
3. **Disabling mkinitcpio Presets:**
   In `/etc/mkinitcpio.d/linux-armv7.preset`, set:
   ```bash
   PRESETS=()
   ```
   This prevents `pacman` kernel updates from auto-generating an initramfs ever again.

---

## 2. Discrete 2-State Voltage Regulator & CPU Governor Brownouts

### The Issue:
- Unlike H3 boards (Orange Pi PC / One) that use an I2C-controlled `SY8106A` PMIC capable of fine-grained dynamic voltage scaling (0.90V to 1.40V), the Orange Pi Zero uses a low-cost discrete GPIO-switched regulator (`vdd-cpux`).
- It only supports **two physical voltage states**:
  - **1.10V** (Low state, used for 648 MHz / 816 MHz)
  - **1.30V** (High state, used for 1008 MHz)
- **The Brownout Quirk:**
  On board revisions v1.4 and v1.5, or when powered via typical micro-USB cables with minor voltage drop, dropping to the 1.10V rail under governors like `powersave` or `conservative` causes the CPU voltage to sag below operating tolerance. This triggers an **immediate hard lockup / processor brownout**.

### The Solution:
1. **Boot Baseline Locked at 1.30V:**
   Added `cpufreq.default_governor=performance` to kernel `bootargs` so the board always boots on the stable 1.30V rail.
2. **Startup Service ([`cpufreq-governor.service`](file:///etc/systemd/system/cpufreq-governor.service)):**
   Guarantees that once userspace initializes, the system remains on `performance` by default.
3. **Software Failsafe in `orangepi-config`:**
   [`hardware_ctrl.py`](file:///home/twilight/Projects/orangepi-config/orangepi_config/backend/hardware_ctrl.py) detects the Orange Pi Zero model and blocks `powersave` / `conservative` from dropping voltage into the brownout zone. Dynamic scaling governors like `schedutil` or `ondemand` remain fully available.

---

## 3. Filesystem Unclean Shutdown Recovery

### The Issue:
- When a brownout or power pull occurs on an active ext4 partition, uncommitted journal transactions and orphaned inodes prevent standard read-only mounting, dropping the system into an emergency rescue shell.

### The Solution:
- Added `fsck.mode=force fsck.repair=yes panic=10` to `bootargs`.
- On any abnormal reboot, the kernel automatically checks and repairs ext4 consistency on root, ensuring headless boards recover unattended.

---

## 4. Xunlong XR819 SDIO Wi-Fi Driver Quirks

### The Issue:
- The on-board Wi-Fi chip is the **Allwinner XR819** connected over SDIO (`mmc1`).
- The driver (`xradio_wlan`) was never merged into the mainline Linux kernel tree.
- When power saving is enabled (`power_save=on`), the chip frequently enters an unrecoverable sleep state over SDIO, dropping Wi-Fi connectivity permanently until power cycle.

### The Solution:
- In `orangepi-config`, the Network tab provides a **"Disable Wi-Fi Sleep Bug"** button which runs `iw dev wlan0 set power_save off`.
- The tool also provides a **"Reload XR819 Driver (Bus Reset)"** option (`modprobe -r xradio_wlan && modprobe xradio_wlan`) to revive a frozen chip without rebooting.
