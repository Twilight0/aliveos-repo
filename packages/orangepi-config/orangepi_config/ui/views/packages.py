"""
Software Package Installer View: Curated headless utilities and services for Orange Pi Zero.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import urwid

from orangepi_config.backend.package_mgr import PackageManager, SoftwarePackage
from orangepi_config.ui.widgets import CustomButton


class PackageRow(urwid.WidgetWrap):
    """Row representing a single software package with checkbox, badge, and description."""

    def __init__(self, package: SoftwarePackage, on_toggle: Optional[Callable[[SoftwarePackage, bool], None]] = None) -> None:
        self.package = package
        self.on_toggle = on_toggle

        # Checkbox is checked if user selected it for installation
        self.checkbox = urwid.CheckBox(package.name, state=False, on_state_change=self._changed)
        styled_cb = urwid.AttrMap(self.checkbox, "checkbox", focus_map="checkbox_focus")

        badge = ("status_ok", "[Installed]") if package.installed else ("status_info", "[Available]")
        self.txt_badge = urwid.Text([badge])
        self.txt_desc = urwid.Text(("card_label", package.description))

        cols = urwid.Columns([
            (24, styled_cb),
            (14, self.txt_badge),
            self.txt_desc,
        ])
        super().__init__(cols)

    def _changed(self, cb: urwid.CheckBox, new_state: bool) -> None:
        if self.on_toggle:
            self.on_toggle(self.package, new_state)

    def set_selected(self, state: bool) -> None:
        self.checkbox.set_state(state, do_callback=False)


class PackagesView(urwid.WidgetWrap):
    def __init__(self, pkg_mgr: PackageManager, on_install_request: Optional[Callable[[List[str]], None]] = None) -> None:
        self.pkg_mgr = pkg_mgr
        self.on_install_request = on_install_request
        self.current_category: Optional[str] = None
        self.selected_pkgs: set[str] = set()

        self.pile_categories = urwid.GridFlow([], cell_width=26, h_sep=1, v_sep=1, align="left")
        self.list_walker = urwid.SimpleFocusListWalker([])
        self.list_box = urwid.ListBox(self.list_walker)
        self.txt_summary = urwid.Text(("card_label", "Selected: 0 packages"))

        self._frame = self._build_layout()
        super().__init__(self._frame)

        self.refresh()

    def _build_layout(self) -> urwid.Frame:
        # Header actions
        btn_all_uninstalled = CustomButton("Select Uninstalled", on_press=lambda _: self._select_uninstalled())
        btn_clear = CustomButton("Clear Selection", on_press=lambda _: self._clear_selection())
        btn_install = CustomButton("Install Selected", on_press=lambda _: self._trigger_install())

        action_bar = urwid.Columns([
            (22, btn_all_uninstalled),
            (18, btn_clear),
            self.txt_summary,
            (20, btn_install),
        ])

        nav_hint = urwid.Text([
            ("header_accent", " Categories "),
            ("card_label", "[Tab: Switch Header/List | c / ]: Next Cat | [: Prev Cat | 1-9: Jump]"),
        ])

        top_controls = urwid.Pile([
            urwid.LineBox(urwid.Pile([
                nav_hint,
                urwid.Divider(" "),
                self.pile_categories,
            ])),
            urwid.Divider(" "),
            action_bar,
            urwid.Divider("─"),
        ])

        frame = urwid.Frame(
            body=self.list_box,
            header=top_controls,
            focus_part="body",
        )
        return frame

    def refresh(self) -> None:
        """Refreshes installed state from pacman and updates list."""
        self.pkg_mgr.refresh_installed_status()

        # Update category buttons
        cats = ["All"] + self.pkg_mgr.get_categories()
        cat_btns = []
        for idx, cat in enumerate(cats):
            is_active = (cat == "All" and self.current_category is None) or (cat == self.current_category)
            prefix = "● " if is_active else "○ "
            cat_name = None if cat == "All" else cat
            label = f"{prefix}[{idx + 1}] {cat}"
            btn = CustomButton(label, on_press=self._filter_category, user_data=cat_name)
            cat_btns.append(btn)
        self.pile_categories.contents = [(b, self.pile_categories.options()) for b in cat_btns]

        # Populate package list
        packages = self.pkg_mgr.get_packages_by_category(self.current_category)
        rows: List[urwid.Widget] = []
        for pkg in packages:
            row = PackageRow(pkg, on_toggle=self._on_package_toggled)
            row.set_selected(pkg.name in self.selected_pkgs)
            rows.append(row)

        self.list_walker[:] = rows
        self._update_summary()

    def _filter_category(self, category: Optional[str]) -> None:
        self.current_category = category
        self.refresh()

    def _cycle_category(self, forward: bool = True) -> None:
        cats = [None] + self.pkg_mgr.get_categories()
        try:
            curr_idx = cats.index(self.current_category)
        except ValueError:
            curr_idx = 0
        if forward:
            next_idx = (curr_idx + 1) % len(cats)
        else:
            next_idx = (curr_idx - 1) % len(cats)
        self._filter_category(cats[next_idx])

    def keypress(self, size: Tuple[int, int], key: str) -> Optional[str]:
        # Handle Tab to toggle focus between category/actions header and package list body
        if key in ("tab", "shift tab"):
            if self._frame.focus_position == "body":
                self._frame.focus_position = "header"
            else:
                self._frame.focus_position = "body"
            return None

        # Quick cycle category hotkeys: 'c', 'C', ']', '['
        if key in ("c", "C", "]"):
            self._cycle_category(forward=True)
            return None
        if key == "[":
            self._cycle_category(forward=False)
            return None

        # Number keys 1-9 to jump directly to category
        cats = [None] + self.pkg_mgr.get_categories()
        if key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(cats):
                self._filter_category(cats[idx])
                return None

        return super().keypress(size, key)

    def _on_package_toggled(self, pkg: SoftwarePackage, state: bool) -> None:
        if state:
            self.selected_pkgs.add(pkg.name)
        else:
            self.selected_pkgs.discard(pkg.name)
        self._update_summary()

    def _select_uninstalled(self) -> None:
        packages = self.pkg_mgr.get_packages_by_category(self.current_category)
        for p in packages:
            if not p.installed:
                self.selected_pkgs.add(p.name)
        self.refresh()

    def _clear_selection(self) -> None:
        self.selected_pkgs.clear()
        self.refresh()

    def _update_summary(self) -> None:
        count = len(self.selected_pkgs)
        if count == 0:
            self.txt_summary.set_text(("card_label", "Selected: 0 packages"))
        else:
            names = ", ".join(sorted(self.selected_pkgs))
            self.txt_summary.set_text([
                ("card_label", f"Selected ({count}): "),
                ("status_warn", names[:40] + ("..." if len(names) > 40 else "")),
            ])

    def _trigger_install(self) -> None:
        if not self.selected_pkgs:
            return
        if self.on_install_request:
            self.on_install_request(sorted(list(self.selected_pkgs)))
