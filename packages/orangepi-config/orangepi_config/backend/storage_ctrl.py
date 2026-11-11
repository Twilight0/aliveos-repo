"""
Storage Controller for Orange Pi Zero.
Provides block device detection, external drive mounting/unmounting,
and safe disk formatting with volume labeling for external USB storage.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple


def _format_size(size_bytes: int) -> str:
    """Formats bytes into human readable binary/decimal units."""
    if size_bytes <= 0:
        return "0 B"
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PiB"


def _sanitize_label(label: str) -> str:
    """Sanitizes a label for use as a directory name under /mnt."""
    sanitized = re.sub(r"[^\w\-.]", "_", label).strip("_")
    return sanitized if sanitized else "storage"


class StorageController:
    @staticmethod
    def get_storage_devices() -> List[Dict[str, Any]]:
        """
        Discovers all block devices, filtering and categorizing
        system disks (e.g. mmcblk0) vs external USB/SATA drives.
        """
        devices: List[Dict[str, Any]] = []
        if not shutil.which("lsblk"):
            return devices

        try:
            cmd = [
                "lsblk",
                "-J",
                "-b",
                "-o",
                "NAME,PATH,FSTYPE,FSVER,LABEL,UUID,FSAVAIL,FSUSE%,MOUNTPOINTS,SIZE,MODEL,TRAN,RM,HOTPLUG,TYPE",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                return devices

            data = json.loads(res.stdout)
            raw_devices = data.get("blockdevices", [])

            def parse_device_tree(node: Dict[str, Any], parent_model: str = ""):
                path = node.get("path", "")
                name = node.get("name", "")
                size_b = int(node.get("size") or 0)
                fstype = node.get("fstype") or ""
                label = (node.get("label") or "").strip()
                uuid = node.get("uuid") or ""
                model = (node.get("model") or parent_model or "").strip()
                node_type = node.get("type", "")

                mounts = node.get("mountpoints") or []
                # Filter out None values in mountpoints
                mountpoints = [m for m in mounts if m]
                primary_mount = mountpoints[0] if mountpoints else None

                is_root = any(m in ("/", "/boot") for m in mountpoints)
                is_system = name.startswith("mmcblk0") or name.startswith("zram") or is_root
                is_partition = (node_type == "part") or bool(re.search(r"[0-9]+$", name))

                # Determine default mount point
                default_mp = ""
                if label:
                    default_mp = f"/mnt/{_sanitize_label(label)}"
                else:
                    default_mp = f"/mnt/{name}"

                dev_info = {
                    "name": name,
                    "path": path,
                    "size_bytes": size_b,
                    "size_human": _format_size(size_b),
                    "fstype": fstype or "raw/unknown",
                    "label": label,
                    "uuid": uuid,
                    "model": model,
                    "type": node_type,
                    "is_partition": is_partition,
                    "mountpoint": primary_mount,
                    "is_mounted": bool(primary_mount),
                    "default_mountpoint": default_mp,
                    "is_system": is_system,
                    "is_root": is_root,
                    "has_children": bool(node.get("children")),
                }
                devices.append(dev_info)

                for child in node.get("children", []):
                    parse_device_tree(child, parent_model=model)

            for d in raw_devices:
                parse_device_tree(d)

        except Exception:
            pass

        return devices

    @staticmethod
    def get_external_partitions() -> List[Dict[str, Any]]:
        """Returns list of mountable/formattable external non-system partitions or drives."""
        all_devs = StorageController.get_storage_devices()
        external = []
        for d in all_devs:
            # We allow formatting/mounting external drives (sda, sdb, etc.)
            # Exclude mmcblk0, zram, and root/boot partitions
            if not d["is_system"] and not d["is_root"]:
                # If disk has partitions, users usually mount/format partitions,
                # but if unpartitioned raw disk (like raw FAT stick), allow whole disk
                if not d["has_children"] or d["is_partition"]:
                    external.append(d)
        return external

    @staticmethod
    def mount_device(device_path: str, mountpoint: Optional[str] = None) -> Tuple[bool, str]:
        """Mounts a block device to specified or default (/mnt/{label|name}) mount point."""
        if not device_path or not os.path.exists(device_path):
            return False, f"Device '{device_path}' does not exist."

        # Safety check: do not touch root partition
        if device_path.startswith("/dev/mmcblk0p1"):
            return False, "Cannot mount root system device."

        if not mountpoint:
            # Find label or device name to determine default mountpoint
            for d in StorageController.get_storage_devices():
                if d["path"] == device_path:
                    mountpoint = d["default_mountpoint"]
                    break
            if not mountpoint:
                devname = os.path.basename(device_path)
                mountpoint = f"/mnt/{devname}"

        mountpoint = os.path.abspath(mountpoint)
        try:
            os.makedirs(mountpoint, exist_ok=True)
            res = subprocess.run(["mount", device_path, mountpoint], capture_output=True, text=True)
            if res.returncode == 0:
                return True, f"Successfully mounted '{device_path}' at '{mountpoint}'."
            
            # If standard mount failed, check if ntfs-3g can handle it
            if "ntfs" in res.stderr.lower() and shutil.which("ntfs-3g"):
                res2 = subprocess.run(["ntfs-3g", device_path, mountpoint], capture_output=True, text=True)
                if res2.returncode == 0:
                    return True, f"Successfully mounted NTFS '{device_path}' at '{mountpoint}'."

            return False, f"Mount failed: {res.stderr.strip()}"
        except Exception as e:
            return False, f"Error mounting device: {e}"

    @staticmethod
    def unmount_device(device_path: str) -> Tuple[bool, str]:
        """Safely unmounts a block device or mountpoint."""
        if not device_path:
            return False, "Device path cannot be empty."

        # Safety check: prevent unmounting root or system mounts
        for d in StorageController.get_storage_devices():
            if (d["path"] == device_path or d["mountpoint"] == device_path) and d["is_root"]:
                return False, "Refusing to unmount system root partition (/)."

        try:
            res = subprocess.run(["umount", device_path], capture_output=True, text=True)
            if res.returncode == 0:
                return True, f"Successfully unmounted '{device_path}'."
            return False, f"Unmount failed: {res.stderr.strip()}"
        except Exception as e:
            return False, f"Error unmounting device: {e}"

    @staticmethod
    def format_device(device_path: str, fstype: str = "ext4", label: str = "") -> Tuple[bool, str]:
        """
        Formats a device with given filesystem and optional volume label.
        Supported filesystems: ext4, vfat, exfat, ntfs, btrfs.
        """
        if not device_path or not os.path.exists(device_path):
            return False, f"Device '{device_path}' does not exist."

        # STRICT SAFETY GUARD: Never format root or eMMC/SD system card
        if any(device_path.startswith(p) for p in ["/dev/mmcblk0", "/dev/zram"]):
            return False, "CRITICAL ERROR: Cannot format system boot disk or swap memory!"

        for d in StorageController.get_storage_devices():
            if d["path"] == device_path and d["is_root"]:
                return False, "CRITICAL ERROR: Cannot format active root partition (/)."

        # Unmount first if mounted
        StorageController.unmount_device(device_path)

        fstype_clean = fstype.lower().strip()
        label_clean = label.strip()

        cmd = []
        if fstype_clean in ("ext4", "ext3", "ext2"):
            if not shutil.which(f"mkfs.{fstype_clean}"):
                return False, f"mkfs.{fstype_clean} not found. Please install 'e2fsprogs'."
            cmd = [f"mkfs.{fstype_clean}", "-F"]
            if label_clean:
                cmd += ["-L", label_clean]
            cmd.append(device_path)

        elif fstype_clean in ("vfat", "fat32", "fat"):
            if not shutil.which("mkfs.vfat"):
                return False, "mkfs.vfat not found. Please install 'dosfstools'."
            cmd = ["mkfs.vfat", "-F", "32"]
            if label_clean:
                # FAT32 volume labels are max 11 characters
                cmd += ["-n", label_clean[:11].upper()]
            cmd.append(device_path)

        elif fstype_clean == "exfat":
            if not shutil.which("mkfs.exfat"):
                return False, "mkfs.exfat not found. Please install 'exfatprogs'."
            cmd = ["mkfs.exfat"]
            if label_clean:
                cmd += ["-n", label_clean[:15]]
            cmd.append(device_path)

        elif fstype_clean == "ntfs":
            if not shutil.which("mkfs.ntfs"):
                return False, "mkfs.ntfs not found. Please install 'ntfs-3g'."
            cmd = ["mkfs.ntfs", "-f"]
            if label_clean:
                cmd += ["-L", label_clean]
            cmd.append(device_path)

        elif fstype_clean == "btrfs":
            if not shutil.which("mkfs.btrfs"):
                return False, "mkfs.btrfs not found. Please install 'btrfs-progs'."
            cmd = ["mkfs.btrfs", "-f"]
            if label_clean:
                cmd += ["-L", label_clean]
            cmd.append(device_path)

        else:
            return False, f"Unsupported filesystem type: '{fstype}'."

        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                lbl_msg = f" with label '{label_clean}'" if label_clean else ""
                return True, f"Successfully formatted '{device_path}' as {fstype_clean}{lbl_msg}."
            return False, f"Formatting failed: {res.stderr.strip() or res.stdout.strip()}"
        except Exception as e:
            return False, f"Error formatting device: {e}"
