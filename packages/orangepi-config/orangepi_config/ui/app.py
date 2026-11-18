"""
Main Application Frame and Event Loop Controller for orangepi-config.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
from typing import Any, Callable, List, Optional
import urwid

from orangepi_config import __version__
from orangepi_config.backend.hardware_ctrl import HardwareController
from orangepi_config.backend.network_ctrl import NetworkController
from orangepi_config.backend.package_mgr import PackageManager
from orangepi_config.backend.system_info import SystemInfo
from orangepi_config.config import emit_terminal_title, get_window_title
from orangepi_config.ui.styles import PALETTE
from orangepi_config.ui.views.dashboard import DashboardView
from orangepi_config.ui.views.hardware import HardwareView
from orangepi_config.ui.views.network import NetworkView
from orangepi_config.ui.views.packages import PackagesView
from orangepi_config.ui.views.system import SystemView
from orangepi_config.ui.views.terminal import TerminalView
from orangepi_config.ui.widgets import CustomButton, ModalDialog, TabButton


class OrangePiConfigApp:
    def __init__(self, window_title: Optional[str] = None) -> None:
        self.window_title = window_title or get_window_title()

        # Backends
        self.sys_info = SystemInfo()
        self.hw_ctrl = HardwareController()
        self.net_ctrl = NetworkController()
        self.pkg_mgr = PackageManager()

        # Views
        self.view_dashboard = DashboardView(self.sys_info)
        self.view_hardware = HardwareView(self.hw_ctrl)
        self.view_network = NetworkView(
            self.net_ctrl,
            on_modal_dialog=self.open_modal,
            on_close_modal=self.close_modal,
        )
        self.view_packages = PackagesView(self.pkg_mgr, on_install_request=self.show_install_dialog)
        self.view_system = SystemView(
            on_run_command=self.show_command_dialog,
            on_confirm_dialog=self.show_confirm_dialog,
            on_title_change=self.set_window_title,
            on_modal_dialog=self.open_modal,
            on_close_modal=self.close_modal,
        )
        self.view_terminal = TerminalView(
            on_launch_terminal=self.launch_terminal,
            on_run_command=self.show_command_dialog,
            get_loop=lambda: self.loop,
        )

        self.views = [
            ("Status", self.view_dashboard),
            ("Hardware", self.view_hardware),
            ("Network", self.view_network),
            ("Software", self.view_packages),
            ("System", self.view_system),
            ("Terminal", self.view_terminal),
        ]
        self.current_tab_idx = 0

        # Build top header & tab navigation
        self.header_widget = self._build_header()
        self.footer_widget = self._build_footer()

        # Body container
        self.body_container = urwid.WidgetPlaceholder(self.views[0][1])

        # Base Frame
        self.frame = urwid.Frame(
            body=self.body_container,
            header=self.header_widget,
            footer=self.footer_widget,
        )

        # Overlay holder for popups / modals
        self.root_widget = urwid.WidgetPlaceholder(self.frame)

        # Urwid MainLoop
        self.loop = urwid.MainLoop(
            self.root_widget,
            palette=PALETTE,
            unhandled_input=self._handle_input,
        )

        # Dashboard refresh timer
        self._refresh_alarm: Optional[Any] = None
        self._schedule_refresh()

    def _build_header(self) -> urwid.Pile:
        self.header_title_text = urwid.Text([
            ("header_accent", " orangepi-config "),
            ("header", f"v{__version__} | {self.window_title}"),
        ], align="center")
        header_bar = urwid.AttrMap(self.header_title_text, "header")

        # Tab navigation buttons
        self.tab_buttons: List[urwid.Button] = []
        tab_cols = []
        for idx, (name, _) in enumerate(self.views):
            label = f"[F{idx + 1}] {name}"
            btn = TabButton(label, on_press=self._on_tab_click, user_data=idx)
            self.tab_buttons.append(btn)
            styled_btn = urwid.AttrMap(btn, "tab_inactive", focus_map="tab_active")
            tab_cols.append(styled_btn)

        tabs_row = urwid.Columns(tab_cols)
        divider = urwid.Divider("─")

        return urwid.Pile([
            header_bar,
            tabs_row,
            divider,
        ])

    def set_window_title(self, new_title: str) -> None:
        self.window_title = new_title
        self.header_title_text.set_text([
            ("header_accent", " orangepi-config "),
            ("header", f"v{__version__} | {self.window_title}"),
        ])
        emit_terminal_title(self.window_title)

    def _build_footer(self) -> urwid.Widget:
        key_hints = [
            ("footer_key", " [F1-F6]"), ("footer", " Switch Tab | "),
            ("footer_key", "[↑/↓/Tab]"), ("footer", " Navigate | "),
            ("footer_key", "[Space/Enter]"), ("footer", " Select | "),
            ("footer_key", "[Q]"), ("footer", " Quit"),
        ]
        return urwid.AttrMap(urwid.Text(key_hints, align="center"), "footer")

    def _update_tabs(self) -> None:
        for idx, btn in enumerate(self.tab_buttons):
            is_active = (idx == self.current_tab_idx)
            attr = "tab_active" if is_active else "tab_inactive"
            btn_parent = self.header_widget.contents[1][0].contents[idx][0]
            btn_parent.set_attr_map({None: attr})

        # Switch body view
        active_view = self.views[self.current_tab_idx][1]
        self.body_container.original_widget = active_view
        if hasattr(active_view, "refresh"):
            active_view.refresh()

    def _on_tab_click(self, btn: Any, idx: int) -> None:
        self.switch_tab(idx)

    def switch_tab(self, idx: int) -> None:
        if 0 <= idx < len(self.views):
            self.current_tab_idx = idx
            self._update_tabs()
            emit_terminal_title(self.window_title)

    def _schedule_refresh(self) -> None:
        # Refresh dashboard every 2.0s if visible and keep terminal/ttyd window title synced
        if self.current_tab_idx == 0:
            self.view_dashboard.refresh()
        emit_terminal_title(self.window_title)
        self._refresh_alarm = self.loop.set_alarm_in(2.0, self._timer_tick)

    def _timer_tick(self, loop: Any, user_data: Any) -> None:
        self._schedule_refresh()

    def _handle_input(self, key: str) -> None:
        if key in ("q", "Q"):
            raise urwid.ExitMainLoop()
        elif key in ("f1", "F1"):
            self.switch_tab(0)
        elif key in ("f2", "F2"):
            self.switch_tab(1)
        elif key in ("f3", "F3"):
            self.switch_tab(2)
        elif key in ("f4", "F4"):
            self.switch_tab(3)
        elif key in ("f5", "F5"):
            self.switch_tab(4)
        elif key in ("f6", "F6"):
            self.switch_tab(5)
        elif key == "tab" and self.current_tab_idx != 3:  # Don't override tab in Software tab
            next_tab = (self.current_tab_idx + 1) % len(self.views)
            self.switch_tab(next_tab)

    def launch_terminal(self, username: str) -> None:
        """Interactive terminal launcher with security restrictions."""
        # Security policy: do not allow login to user accounts or root from the terminal tab
        self.show_confirm_dialog(
            "Access Prohibited",
            "Security Policy: Direct login to root or user accounts is disabled from the terminal tab.\n\nPlease connect securely via SSH for interactive shell access.",
            lambda: None,
        )

    # ---------------- Modal Dialogs ----------------

    def show_confirm_dialog(self, title: str, prompt: str, on_confirm: Callable[[], None]) -> None:
        """Displays a confirmation dialog with Yes / Cancel."""
        body = urwid.Filler(urwid.Text(prompt, align="center"))
        
        def _yes(_: Any) -> None:
            self.close_modal()
            on_confirm()

        def _cancel(_: Any) -> None:
            self.close_modal()

        dialog = ModalDialog(
            title=title,
            body_widget=body,
            buttons=[("Confirm", _yes), ("Cancel", _cancel)],
            width=50,
            height=10,
        )
        self.open_modal(dialog)

    def _resolve_installer_script(self, script_name: str) -> str:
        """Resolve installed or local-tree helper script path."""
        installed_path = f"/usr/share/orangepi-config/scripts/{script_name}"
        if os.path.exists(installed_path):
            return installed_path
        local_script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts", script_name)
        return local_script if os.path.exists(local_script) else installed_path

    def show_install_dialog(self, packages: List[str]) -> None:
        """Launches installation modal for selected packages (pacman or custom standalone)."""
        standalone_scripts = {
            "jackett": "install-jackett.sh",
            "9router-go": "install-9router-go.sh",
        }
        pacman_pkgs = [p for p in packages if p not in standalone_scripts]
        standalone_pkgs = [p for p in packages if p in standalone_scripts]

        steps = []
        if pacman_pkgs:
            steps.append(f"pacman -S --needed --noconfirm {' '.join(pacman_pkgs)}")
        for pkg in standalone_pkgs:
            script_path = self._resolve_installer_script(standalone_scripts[pkg])
            steps.append(f"bash {script_path}")

        if len(standalone_pkgs) == 1 and not pacman_pkgs:
            script_path = self._resolve_installer_script(standalone_scripts[standalone_pkgs[0]])
            self.show_command_dialog(f"Installing {standalone_pkgs[0]}", ["/bin/bash", script_path])
            return

        if standalone_pkgs:
            self.show_command_dialog("Installing Selected Software", ["/bin/bash", "-c", " && ".join(steps)])
            return

        cmd = ["pacman", "-S", "--needed", "--noconfirm"] + pacman_pkgs
        self.show_command_dialog("Installing Software", cmd)

    def show_command_dialog(self, title: str, cmd: List[str]) -> None:
        """Executes a command asynchronously and streams stdout into a live terminal modal."""
        # Security validation: disallow privilege escalation or user switching
        for part in cmd:
            for word in str(part).split():
                if word.lower() in {"su", "sudo", "login", "passwd", "useradd", "usermod", "userdel", "chsh"}:
                    self.show_confirm_dialog(
                        "Security Policy Violation",
                        f"Execution of '{word}' is prohibited. Direct escalation or login to root and user accounts is disabled from this interface.",
                        lambda: None,
                    )
                    return

        log_walker = urwid.SimpleFocusListWalker([])
        log_box = urwid.ListBox(log_walker)
        box_styled = urwid.AttrMap(log_box, "dialog_content")

        btn_close = CustomButton("Close", on_press=lambda _: self.close_modal())
        btn_close_holder = urwid.WidgetPlaceholder(urwid.Text(("card_label", "Executing command, please wait..."), align="center"))

        content = urwid.Pile([
            box_styled,
            ("pack", urwid.Divider("─")),
            ("pack", btn_close_holder),
        ])
        
        modal = ModalDialog(
            title=title,
            body_widget=content,
            buttons=[],
            width=70,
            height=20,
        )
        self.open_modal(modal)

        def _worker() -> None:
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                if proc.stdout:
                    for line in proc.stdout:
                        clean_line = line.rstrip()
                        self.loop.set_alarm_in(0, lambda *_, l=clean_line: log_walker.append(urwid.Text(("log_output", l))))
                        self.loop.set_alarm_in(0, lambda *_: log_box.set_focus(len(log_walker) - 1))
                proc.wait()
                rc = proc.returncode
                status_line = f"\n[Process finished with exit code {rc}]"
                attr = "status_ok" if rc == 0 else "status_alert"
                self.loop.set_alarm_in(0, lambda *_, a=attr, s=status_line: log_walker.append(urwid.Text((a, s))))
                self.loop.set_alarm_in(0, lambda *_: log_box.set_focus(len(log_walker) - 1))
            except Exception as e:
                err_msg = str(e)
                self.loop.set_alarm_in(0, lambda *_, err=err_msg: log_walker.append(urwid.Text(("status_alert", f"\nFailed: {err}"))))
            
            # Show Close button and refresh packages view
            def _done(*_: Any) -> None:
                btn_close_holder.original_widget = btn_close
                if hasattr(self.view_packages, "refresh"):
                    self.view_packages.refresh()
            self.loop.set_alarm_in(0, _done)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def open_modal(self, modal_widget: ModalDialog) -> None:
        """Pushes modal overlay onto root container."""
        overlay = urwid.Overlay(
            modal_widget,
            self.frame,
            align="center",
            width=modal_widget.width,
            valign="middle",
            height=modal_widget.height,
        )
        self.root_widget.original_widget = overlay

    def close_modal(self) -> None:
        """Removes modal overlay."""
        self.root_widget.original_widget = self.frame

    def run(self) -> None:
        """Starts Urwid main loop."""
        self.loop.set_alarm_in(0.05, lambda *_: emit_terminal_title(self.window_title))
        self.loop.run()
