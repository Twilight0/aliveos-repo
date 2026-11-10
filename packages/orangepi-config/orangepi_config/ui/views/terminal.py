"""
Terminal access view for orangepi-config.
Provides system diagnostics and terminal environment information.
Direct shell login to root or user accounts is disabled for security.
"""

from __future__ import annotations

import os
import pwd
import shlex
import sys
from typing import Any, Callable, List, Optional
import urwid

from orangepi_config.ui.widgets import CustomButton

BLOCKED_COMMANDS = {
    "bash", "sh", "zsh", "dash", "ash", "csh", "tcsh", "ksh",
    "su", "sudo", "login", "passwd", "useradd", "usermod", "userdel", "chsh",
}


def get_active_tty() -> str:
    """Returns the current TTY device or description."""
    try:
        return os.ttyname(sys.stdin.fileno())
    except Exception:
        term = os.environ.get("TERM", "unknown")
        return f"PTY ({term})"


class TerminalView(urwid.WidgetWrap):
    def __init__(
        self,
        on_launch_terminal: Optional[Callable[[str], None]] = None,
        on_run_command: Optional[Callable[[str, List[str]], None]] = None,
    ) -> None:
        self.on_launch_terminal = on_launch_terminal
        self.on_run_command = on_run_command

        self.txt_status = urwid.Text(("status_info", "Select a system diagnostics shortcut or view environment details."))

        layout = self._build_layout()
        fill = urwid.Filler(layout, valign="top")
        super().__init__(fill)

    def _build_card(self, title: str, content_widgets: List[urwid.Widget]) -> urwid.Widget:
        header = [("card_title", f" {title} ")]
        pile = urwid.Pile([urwid.Text(header)] + content_widgets)
        return urwid.LineBox(pile)

    def _build_layout(self) -> urwid.Pile:
        # Card 1: Security Policy Notice
        card_security = self._build_card("Terminal Access & Security Policy", [
            urwid.Text(("status_warn", "⚠ Direct login to root and system user accounts is disabled from this terminal interface.")),
            urwid.Divider(" "),
            urwid.Text(("card_label", "Security Notice:")),
            urwid.Text(("normal", "When orangepi-config is accessed via web TUI (ttyd) with default credentials (admin/admin), shell login to root or user accounts is disallowed to ensure system integrity.")),
            urwid.Divider(" "),
            urwid.Text(("card_label", "SSH Access for Interactive Shells:")),
            urwid.Text(("normal", "To access a full interactive shell session, please connect securely over SSH using your system account credentials:")),
            urwid.Text(("card_value", "  $ ssh <username>@<device-ip>")),
        ])

        # Card 2: Quick Diagnostics Runner (Safe single-shot execution)
        self.edit_quick_cmd = urwid.Edit(("card_label", "Diagnostics Command: "), "")
        presets = [
            ("ip addr", lambda _: self._run_preset(["ip", "addr"])),
            ("free -m", lambda _: self._run_preset(["free", "-m"])),
            ("lsblk -f", lambda _: self._run_preset(["lsblk", "-f"])),
            ("dmesg | tail", lambda _: self._run_preset(["sh", "-c", "dmesg | tail -n 25"])),
            ("uptime & load", lambda _: self._run_preset(["uptime"])),
        ]
        preset_buttons = [CustomButton(label, on_press=fn) for label, fn in presets]

        card_cmd_runner = self._build_card("System Diagnostics Shortcuts (Live Output)", [
            urwid.Text(("card_label", "Run non-interactive diagnostic commands and view streaming output:")),
            urwid.GridFlow(preset_buttons, cell_width=20, h_sep=2, v_sep=1, align="left"),
            urwid.Divider("─"),
            urwid.Columns([
                (48, self.edit_quick_cmd),
                (20, CustomButton("Run Command", on_press=lambda _: self._run_custom_command())),
            ]),
        ])

        # Card 3: Terminal Session Info
        euid = os.geteuid()
        curr_user = "root" if euid == 0 else pwd.getpwuid(euid).pw_name
        shell_path = os.environ.get("SHELL", "/bin/bash")
        tty_dev = get_active_tty()
        term_type = os.environ.get("TERM", "xterm-256color")

        info_rows = [
            urwid.Columns([
                (24, urwid.Text(("card_label", "Service User:"))),
                (urwid.WEIGHT, 1, urwid.Text(("card_value", f"{curr_user} (UID: {euid})"))),
                (20, urwid.Text(("card_label", "Active TTY:"))),
                (urwid.WEIGHT, 1, urwid.Text(("card_value", tty_dev))),
            ]),
            urwid.Columns([
                (24, urwid.Text(("card_label", "Default Shell:"))),
                (urwid.WEIGHT, 1, urwid.Text(("card_value", shell_path))),
                (20, urwid.Text(("card_label", "Terminal ($TERM):"))),
                (urwid.WEIGHT, 1, urwid.Text(("card_value", term_type))),
            ]),
        ]
        card_info = self._build_card("Terminal Environment", info_rows)

        card_status = self._build_card("Status", [self.txt_status])

        return urwid.Pile([
            card_status,
            card_security,
            card_cmd_runner,
            card_info,
        ])

    def _run_preset(self, cmd: List[str]) -> None:
        if self.on_run_command:
            title = f"Quick Run: {' '.join(cmd)}"
            self.on_run_command(title, cmd)

    def _run_custom_command(self) -> None:
        cmd_str = self.edit_quick_cmd.get_edit_text().strip()
        if not cmd_str:
            self.txt_status.set_text(("status_alert", "Please enter a diagnostic command to execute."))
            return

        try:
            tokens = shlex.split(cmd_str)
        except Exception:
            tokens = cmd_str.split()

        # Security check: disallow interactive shell drops or user account switching
        for token in tokens:
            base_cmd = os.path.basename(token).lower()
            if base_cmd in BLOCKED_COMMANDS:
                self.txt_status.set_text(
                    ("status_alert", f"Security Policy: Command '{base_cmd}' is prohibited. Shell login to root/user accounts is disabled. Use SSH instead.")
                )
                return

        if self.on_run_command:
            self.on_run_command(f"Run: {cmd_str}", ["sh", "-c", cmd_str])
