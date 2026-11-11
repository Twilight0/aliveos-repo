"""
System maintenance, package upgrades, cache cleanup, power controls,
and external storage management (mount, unmount, format).
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Callable, Dict, List, Optional
import urwid

from orangepi_config.backend.storage_ctrl import StorageController
from orangepi_config.config import DEFAULT_WINDOW_TITLE, get_window_title, set_window_title
from orangepi_config.ui.widgets import CustomButton, ModalDialog


class SystemView(urwid.WidgetWrap):
    def __init__(
        self,
        on_run_command: Optional[Callable[[str, List[str]], None]] = None,
        on_confirm_dialog: Optional[Callable[[str, str, Callable[[], None]], None]] = None,
        on_title_change: Optional[Callable[[str], None]] = None,
        on_modal_dialog: Optional[Callable[[urwid.Widget], None]] = None,
        on_close_modal: Optional[Callable[[], None]] = None,
    ) -> None:
        self.on_run_command = on_run_command
        self.on_confirm_dialog = on_confirm_dialog
        self.on_title_change = on_title_change
        self.on_modal_dialog = on_modal_dialog
        self.on_close_modal = on_close_modal

        self.storage_ctrl = StorageController()
        self.txt_status = urwid.Text(("status_info", "Select a maintenance task, power control, or manage external storage."))
        self.pile_storage = urwid.Pile([])

        # System Hostname
        self.edit_hostname = urwid.Edit(("card_label", "New Hostname: "), "")

        # Window & Web Tab Title Customization
        self.edit_window_title = urwid.Edit(("card_label", "Window Title: "), get_window_title())

        layout = self._build_layout()
        fill = urwid.Filler(layout, valign="top")
        super().__init__(fill)

        self._refresh_storage()

    def _build_card(self, title: str, content_widgets: List[urwid.Widget]) -> urwid.Widget:
        header = [("card_title", f" {title} ")]
        pile = urwid.Pile([urwid.Text(header)] + content_widgets)
        return urwid.LineBox(pile)

    def _build_layout(self) -> urwid.Pile:
        card_status = self._build_card("Maintenance & Storage Status", [self.txt_status])

        # Card 1: External Storage & USB Drives
        btn_mount = CustomButton("Mount External Drive", on_press=lambda _: self._show_mount_dialog())
        btn_unmount = CustomButton("Unmount Drive", on_press=lambda _: self._show_unmount_dialog())
        btn_format = CustomButton("Format Drive", on_press=lambda _: self._show_format_dialog())
        btn_refresh_storage = CustomButton("Refresh Storage", on_press=lambda _: self._refresh_storage())

        card_storage = self._build_card("External Storage & USB Drives", [
            urwid.Text(("card_label", "Connected Disks & Partitions (Default Mount Base: /mnt):")),
            urwid.Divider(" "),
            self.pile_storage,
            urwid.Divider("─"),
            urwid.GridFlow([
                btn_mount,
                btn_unmount,
                btn_format,
                btn_refresh_storage,
            ], cell_width=25, h_sep=2, v_sep=1, align="left"),
        ])

        # Card 2: Pacman Maintenance
        card_pacman = self._build_card("Package Database & Updates", [
            urwid.Text(("card_label", "Keep Arch Linux ARM repositories and installed software up to date:")),
            urwid.Divider(" "),
            urwid.GridFlow([
                CustomButton("Sync Databases (pacman -Sy)", on_press=lambda _: self._run_sync()),
                CustomButton("Full Upgrade (pacman -Syu)", on_press=lambda _: self._run_upgrade()),
                CustomButton("Clean Cache (pacman -Sc)", on_press=lambda _: self._run_clean_cache()),
            ], cell_width=32, h_sep=2, v_sep=1, align="left"),
        ])

        # Card 3: System Hostname
        card_config = self._build_card("System Hostname", [
            urwid.Columns([
                (40, self.edit_hostname),
                (22, CustomButton("Apply Hostname", on_press=lambda _: self._apply_hostname())),
            ]),
        ])

        # Card 4: Window & Web Tab Title Customization
        card_title = self._build_card("Window & Web Tab Title", [
            urwid.Text(("card_label", "Customize browser tab (ttyd) and terminal window title:")),
            urwid.Divider(" "),
            urwid.Columns([
                (44, self.edit_window_title),
                (18, CustomButton("Apply Title", on_press=lambda _: self._apply_window_title())),
                (2, urwid.Text("")),
                (19, CustomButton("Reset Default", on_press=lambda _: self._reset_window_title())),
            ]),
        ])

        # Card 5: Power Management
        card_power = self._build_card("Power & Reboot", [
            urwid.Text(("card_label", "Safely reboot or shutdown the Orange Pi Zero:")),
            urwid.Divider(" "),
            urwid.GridFlow([
                CustomButton("Reboot Board", on_press=lambda _: self._prompt_reboot()),
                CustomButton("Power Off Board", on_press=lambda _: self._prompt_poweroff()),
            ], cell_width=22, h_sep=2, v_sep=1, align="left"),
        ])

        return urwid.Pile([
            card_status,
            urwid.Divider(" "),
            card_storage,
            urwid.Divider(" "),
            card_pacman,
            urwid.Divider(" "),
            card_config,
            urwid.Divider(" "),
            card_title,
            urwid.Divider(" "),
            card_power,
        ])

    def _refresh_storage(self) -> None:
        """Queries storage controller and updates connected devices list."""
        devs = self.storage_ctrl.get_storage_devices()
        rows: List[urwid.Widget] = []

        if not devs:
            rows.append(urwid.Text(("status_warn", "  No block devices detected.")))
        else:
            for d in devs:
                badge = ("status_ok", f"[Mounted: {d['mountpoint']}]") if d["is_mounted"] else ("status_info", "[Unmounted]")
                if d["is_root"]:
                    badge = ("header_accent", "[System Root /]")
                elif d["name"].startswith("zram"):
                    badge = ("status_ok", "[ZRAM Swap]")

                lbl = d["label"] if d["label"] else "-"
                row = urwid.Columns([
                    (18, urwid.Text(("card_value", f"• {d['name']} ({d['path']})"))),
                    (12, urwid.Text(("status_info", d["size_human"]))),
                    (10, urwid.Text(("card_label", d["fstype"]))),
                    (20, urwid.Text(("card_label", f"Label: {lbl[:12]}"))),
                    urwid.Text([badge]),
                ])
                rows.append(row)

        self.pile_storage.contents = [(r, ("pack", None)) for r in rows]

    def _show_mount_dialog(self) -> None:
        """Opens modal dialog to select device and mount point."""
        if not self.on_modal_dialog:
            return

        ext_devs = self.storage_ctrl.get_external_partitions()
        unmounted = [d for d in ext_devs if not d["is_mounted"]]

        if not unmounted:
            if not ext_devs:
                msg = "No external drives or USB sticks found. Connect one and click 'Refresh Storage'."
            else:
                msg = "All connected external drives are already mounted!"
            self._set_status(msg, ok=False)
            return

        default_dev = unmounted[0]
        edit_dev = urwid.Edit(("card_label", "Device Node (e.g. /dev/sda1): "), default_dev["path"])
        edit_mp = urwid.Edit(("card_label", "Mount Point: "), default_dev["default_mountpoint"])

        def _do_mount():
            target_dev = edit_dev.get_edit_text().strip()
            target_mp = edit_mp.get_edit_text().strip()
            if not target_dev or not target_mp:
                self._set_status("Device and Mount Point cannot be empty.", ok=False)
                return
            self._close_modal()
            self._set_status(f"Mounting {target_dev} at {target_mp}...", ok=True)
            ok, res_msg = self.storage_ctrl.mount_device(target_dev, target_mp)
            self._set_status(res_msg, ok=ok)
            self._refresh_storage()

        btn_mount_action = CustomButton("Mount", on_press=lambda _: _do_mount())
        btn_cancel = CustomButton("Cancel", on_press=lambda _: self._close_modal())

        pile = urwid.Pile([
            urwid.Text(("card_title", "Mount External Storage")),
            urwid.Divider("─"),
            urwid.Text(("card_label", "Default mount point uses partition label if available (Base: /mnt):")),
            urwid.Divider(" "),
            edit_dev,
            edit_mp,
            urwid.Divider(" "),
            urwid.Columns([
                (14, btn_mount_action),
                (14, btn_cancel),
            ]),
        ])
        dialog = ModalDialog(title="Mount Drive", body_widget=pile, width=64, height=13)
        self.on_modal_dialog(dialog)

    def _show_unmount_dialog(self) -> None:
        """Opens modal dialog to select and unmount an external partition."""
        if not self.on_modal_dialog:
            return

        mounted = [d for d in self.storage_ctrl.get_external_partitions() if d["is_mounted"]]
        if not mounted:
            self._set_status("No mounted external storage devices found.", ok=False)
            return

        default_dev = mounted[0]
        edit_target = urwid.Edit(("card_label", "Device or Mount Point: "), default_dev["mountpoint"] or default_dev["path"])

        def _do_unmount():
            target = edit_target.get_edit_text().strip()
            if not target:
                return
            self._close_modal()
            self._set_status(f"Unmounting {target}...", ok=True)
            ok, res_msg = self.storage_ctrl.unmount_device(target)
            self._set_status(res_msg, ok=ok)
            self._refresh_storage()

        btn_unmount_action = CustomButton("Unmount", on_press=lambda _: _do_unmount())
        btn_cancel = CustomButton("Cancel", on_press=lambda _: self._close_modal())

        pile = urwid.Pile([
            urwid.Text(("card_title", "Unmount External Storage")),
            urwid.Divider("─"),
            edit_target,
            urwid.Divider(" "),
            urwid.Columns([
                (14, btn_unmount_action),
                (14, btn_cancel),
            ]),
        ])
        dialog = ModalDialog(title="Unmount Drive", body_widget=pile, width=60, height=10)
        self.on_modal_dialog(dialog)

    def _show_format_dialog(self) -> None:
        """Opens modal dialog with filesystem type, volume label, and safety confirmation."""
        if not self.on_modal_dialog:
            return

        ext_devs = self.storage_ctrl.get_external_partitions()
        if not ext_devs:
            self._set_status("No external USB or disk drives found to format.", ok=False)
            return

        default_dev = ext_devs[0]["path"]
        edit_dev = urwid.Edit(("card_label", "Device to Format: "), default_dev)
        edit_fs = urwid.Edit(("card_label", "Filesystem (ext4, vfat, exfat, ntfs, btrfs): "), "ext4")
        edit_lbl = urwid.Edit(("card_label", "Volume Label (optional): "), "USB_STORAGE")

        def _do_format():
            target_dev = edit_dev.get_edit_text().strip()
            target_fs = edit_fs.get_edit_text().strip().lower()
            target_lbl = edit_lbl.get_edit_text().strip()

            if not target_dev:
                self._set_status("Device path cannot be empty.", ok=False)
                return

            self._close_modal()
            self._set_status(f"Formatting {target_dev} as {target_fs}...", ok=True)
            ok, res_msg = self.storage_ctrl.format_device(target_dev, fstype=target_fs, label=target_lbl)
            self._set_status(res_msg, ok=ok)
            self._refresh_storage()

        btn_format_action = CustomButton("Format & Erase", on_press=lambda _: _do_format())
        btn_cancel = CustomButton("Cancel", on_press=lambda _: self._close_modal())

        pile = urwid.Pile([
            urwid.Text(("card_title", "Format External Storage")),
            urwid.Divider("─"),
            urwid.Text(("status_alert", "WARNING: ALL DATA ON THE TARGET DEVICE WILL BE PERMANENTLY ERASED!")),
            urwid.Divider(" "),
            edit_dev,
            edit_fs,
            edit_lbl,
            urwid.Divider(" "),
            urwid.Columns([
                (20, btn_format_action),
                (14, btn_cancel),
            ]),
        ])
        dialog = ModalDialog(title="Format Drive", body_widget=pile, width=66, height=15)
        self.on_modal_dialog(dialog)

    def _close_modal(self) -> None:
        if self.on_close_modal:
            self.on_close_modal()

    def _set_status(self, msg: str, ok: bool = True) -> None:
        attr = "status_ok" if ok else "status_alert"
        self.txt_status.set_text([(attr, f"[{msg}]")])

    def _run_sync(self) -> None:
        if self.on_run_command:
            self.on_run_command("Sync Databases", ["pacman", "-Sy"])

    def _run_upgrade(self) -> None:
        if self.on_run_command:
            self.on_run_command("System Upgrade", ["pacman", "-Syu", "--noconfirm"])

    def _run_clean_cache(self) -> None:
        if self.on_run_command:
            self.on_run_command("Clean Package Cache", ["pacman", "-Sc", "--noconfirm"])

    def _apply_hostname(self) -> None:
        new_host = self.edit_hostname.get_edit_text().strip()
        if not new_host:
            self.txt_status.set_text(("status_alert", "Error: Hostname cannot be empty."))
            return
        try:
            res = subprocess.run(["hostnamectl", "set-hostname", new_host], capture_output=True, text=True)
            if res.returncode == 0:
                self.txt_status.set_text(("status_ok", f"Hostname successfully changed to '{new_host}'."))
                self.edit_hostname.set_edit_text("")
            else:
                self.txt_status.set_text(("status_alert", f"Failed: {res.stderr.strip()}"))
        except Exception as e:
            self.txt_status.set_text(("status_alert", f"Error: {e}"))

    def _apply_window_title(self) -> None:
        new_title = self.edit_window_title.get_edit_text().strip()
        if not new_title:
            self.txt_status.set_text(("status_alert", "Error: Window title cannot be empty."))
            return
        try:
            saved_path = set_window_title(new_title)
            if self.on_title_change:
                self.on_title_change(new_title)
            self.txt_status.set_text(("status_ok", f"Window title set to '{new_title}' (saved to {saved_path})."))
        except Exception as e:
            self.txt_status.set_text(("status_alert", f"Failed to save window title: {e}"))

    def _reset_window_title(self) -> None:
        self.edit_window_title.set_edit_text(DEFAULT_WINDOW_TITLE)
        try:
            saved_path = set_window_title(DEFAULT_WINDOW_TITLE)
            if self.on_title_change:
                self.on_title_change(DEFAULT_WINDOW_TITLE)
            self.txt_status.set_text(("status_ok", f"Window title reset to default (saved to {saved_path})."))
        except Exception as e:
            self.txt_status.set_text(("status_alert", f"Failed to reset window title: {e}"))

    def _prompt_reboot(self) -> None:
        if self.on_confirm_dialog:
            self.on_confirm_dialog(
                "Confirm Reboot",
                "Are you sure you want to reboot the Orange Pi Zero now?",
                lambda: subprocess.run(["reboot"]),
            )

    def _prompt_poweroff(self) -> None:
        if self.on_confirm_dialog:
            self.on_confirm_dialog(
                "Confirm Power Off",
                "Are you sure you want to shut down and power off the Orange Pi Zero now?",
                lambda: subprocess.run(["poweroff"]),
            )
