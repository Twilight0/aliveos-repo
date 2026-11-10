"""
System maintenance, package upgrades, cache cleanup, and power controls.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Callable, List, Optional
import urwid

from orangepi_config.ui.widgets import CustomButton


class SystemView(urwid.WidgetWrap):
    def __init__(
        self,
        on_run_command: Optional[Callable[[str, List[str]], None]] = None,
        on_confirm_dialog: Optional[Callable[[str, str, Callable[[], None]], None]] = None,
    ) -> None:
        self.on_run_command = on_run_command
        self.on_confirm_dialog = on_confirm_dialog

        self.txt_status = urwid.Text(("status_info", "Select a maintenance task or system control."))

        layout = self._build_layout()
        fill = urwid.Filler(layout, valign="top")
        super().__init__(fill)

    def _build_card(self, title: str, content_widgets: List[urwid.Widget]) -> urwid.Widget:
        header = [("card_title", f" {title} ")]
        pile = urwid.Pile([urwid.Text(header)] + content_widgets)
        return urwid.LineBox(pile)

    def _build_layout(self) -> urwid.Pile:
        # Card 1: Pacman Maintenance
        card_pacman = self._build_card("Package Database & Updates", [
            urwid.Text(("card_label", "Keep Arch Linux ARM repositories and installed software up to date:")),
            urwid.Divider(" "),
            urwid.GridFlow([
                CustomButton("Sync Databases (pacman -Sy)", on_press=lambda _: self._run_sync()),
                CustomButton("Full Upgrade (pacman -Syu)", on_press=lambda _: self._run_upgrade()),
                CustomButton("Clean Cache (pacman -Sc)", on_press=lambda _: self._run_clean_cache()),
            ], cell_width=32, h_sep=2, v_sep=1, align="left"),
        ])

        # Card 2: System Configuration
        self.edit_hostname = urwid.Edit(("card_label", "New Hostname: "), "")
        card_config = self._build_card("System Hostname", [
            urwid.Columns([
                (40, self.edit_hostname),
                (22, CustomButton("Apply Hostname", on_press=lambda _: self._apply_hostname())),
            ]),
        ])

        # Card 3: Power Management
        card_power = self._build_card("Power & Reboot", [
            urwid.Text(("card_label", "Safely reboot or shutdown the Orange Pi Zero:")),
            urwid.Divider(" "),
            urwid.GridFlow([
                CustomButton("Reboot Board", on_press=lambda _: self._prompt_reboot()),
                CustomButton("Power Off Board", on_press=lambda _: self._prompt_poweroff()),
            ], cell_width=22, h_sep=2, v_sep=1, align="left"),
        ])

        card_status = self._build_card("Maintenance Status", [self.txt_status])

        return urwid.Pile([
            card_status,
            card_pacman,
            card_config,
            card_power,
        ])

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
                "Confirm Shutdown",
                "Are you sure you want to safely power off the Orange Pi Zero now?",
                lambda: subprocess.run(["poweroff"]),
            )
