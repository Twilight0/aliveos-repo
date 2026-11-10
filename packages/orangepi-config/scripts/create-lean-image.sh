#!/usr/bin/env bash
# ==============================================================================
# create-lean-image.sh
# Automates sanitizing, shrinking, dumping, and compressing a redistributable
# minimal Arch Linux ARM base image from an Orange Pi Zero SD card.
# ==============================================================================

set -euo pipefail

SD_DEV="${1:-/dev/mmcblk0}"
OUTPUT_DIR="${2:-/home/twilight/Projects}"
IMAGE_NAME="orangepi-zero-archlinux-base"
RAW_IMG="$OUTPUT_DIR/$IMAGE_NAME.img"
XZ_IMG="$OUTPUT_DIR/$IMAGE_NAME.img.xz"
MOUNT_POINT="/mnt/opizero"

if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run as root (sudo ./create-lean-image.sh [device] [output_dir])"
    exit 1
fi

if [ ! -b "$SD_DEV" ]; then
    echo "Error: Device '$SD_DEV' is not a block device."
    exit 1
fi

PART_DEV="${SD_DEV}p1"
if [ ! -b "$PART_DEV" ]; then
    PART_DEV="${SD_DEV}1"
fi

if [ ! -b "$PART_DEV" ]; then
    echo "Error: Partition '$PART_DEV' not found."
    exit 1
fi

echo "================================================================="
echo "Orange Pi Zero Base Image Builder"
echo "Target Device: $SD_DEV ($PART_DEV)"
echo "Output Image:  $XZ_IMG"
echo "================================================================="

# 1. Unmount if currently mounted
umount "$PART_DEV" 2>/dev/null || true

# 2. Filesystem check
echo "[1/6] Checking filesystem integrity..."
e2fsck -fy "$PART_DEV" || true

# 3. Mount and sanitize
echo "[2/6] Mounting and sanitizing filesystem..."
mkdir -p "$MOUNT_POINT"
mount "$PART_DEV" "$MOUNT_POINT"

# Remove pacman cache, logs, histories, temporary files
rm -rf "$MOUNT_POINT/var/cache/pacman/pkg/*"
find "$MOUNT_POINT/var/log" -type f -exec truncate -s 0 {} +
rm -rf "$MOUNT_POINT/var/log/journal/*"
rm -rf "$MOUNT_POINT/tmp/*" "$MOUNT_POINT/var/tmp/*"
rm -f "$MOUNT_POINT/root/.bash_history" "$MOUNT_POINT/home/alarm/.bash_history"
rm -f "$MOUNT_POINT/etc/ssh/ssh_host_*"

# Install first-boot partition auto-expand service
cat << 'EOF' > "$MOUNT_POINT/etc/systemd/system/auto-expand-root.service"
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
EOF

cat << 'EOF' > "$MOUNT_POINT/usr/local/sbin/auto-expand-root.sh"
#!/bin/bash
set -e
PART_DEV=$(findmnt / -o SOURCE -n)
DISK_DEV=$(lsblk -no PKNAME "$PART_DEV")
parted -s "/dev/$DISK_DEV" resizepart 1 100%
resize2fs "$PART_DEV"
systemctl disable auto-expand-root.service
rm -f /etc/systemd/system/auto-expand-root.service /usr/local/sbin/auto-expand-root.sh
EOF
chmod +x "$MOUNT_POINT/usr/local/sbin/auto-expand-root.sh"
mkdir -p "$MOUNT_POINT/etc/systemd/system/basic.target.wants"
ln -sf /etc/systemd/system/auto-expand-root.service "$MOUNT_POINT/etc/systemd/system/basic.target.wants/auto-expand-root.service"

sync
umount "$MOUNT_POINT"

# 4. Shrink ext4 filesystem to minimum
echo "[3/6] Shrinking ext4 filesystem to minimum possible size..."
e2fsck -fy "$PART_DEV"
resize2fs -M "$PART_DEV"

# Determine filesystem size in MB
BLOCK_COUNT=$(dumpe2fs -h "$PART_DEV" 2>/dev/null | grep "Block count:" | awk '{print $3}')
BLOCK_SIZE=$(dumpe2fs -h "$PART_DEV" 2>/dev/null | grep "Block size:" | awk '{print $3}')
FS_SIZE_BYTES=$(( BLOCK_COUNT * BLOCK_SIZE ))
FS_SIZE_MB=$(( FS_SIZE_BYTES / (1024 * 1024) ))
TARGET_PART_MB=$(( FS_SIZE_MB + 150 )) # 150MB safety margin

echo "Filesystem size: ${FS_SIZE_MB}MB. Setting partition end to: ${TARGET_PART_MB}MB..."
parted -s "$SD_DEV" resizepart 1 "${TARGET_PART_MB}MB"

# 5. Dump raw image with dd
DUMP_COUNT_MB=$(( TARGET_PART_MB + 10 ))
echo "[4/6] Dumping ${DUMP_COUNT_MB}MB raw image (MBR + U-Boot SPL + Rootfs)..."
mkdir -p "$OUTPUT_DIR"
rm -f "$RAW_IMG"
dd if="$SD_DEV" of="$RAW_IMG" bs=1M count="$DUMP_COUNT_MB" status=progress conv=fsync

# 6. Compress with xz
echo "[5/6] Compressing image with multi-threaded xz -9 (this may take 2-4 minutes)..."
rm -f "$XZ_IMG"
xz -T0 -9 -v "$RAW_IMG"

echo "[6/6] Complete!"
echo "Generated lean distributable image:"
ls -lh "$XZ_IMG"
echo "Sha256 checksum:"
sha256sum "$XZ_IMG"
