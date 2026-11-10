"""
Reusable UI widgets and layout components for orangepi-config.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple
import urwid


class MeterBar(urwid.WidgetWrap):
    """A compact, visual text-based meter bar (e.g., [██████░░░░░░] 60%)."""

    def __init__(self, percent: float, width: int = 16, label_suffix: str = "%") -> None:
        self.width = width
        self.label_suffix = label_suffix
        self.text_widget = urwid.Text("")
        super().__init__(self.text_widget)
        self.set_percent(percent)

    def set_percent(self, percent: float) -> None:
        clamped = max(0.0, min(100.0, percent))
        filled_len = int(round(clamped / 100.0 * self.width))
        empty_len = self.width - filled_len

        # Color coding: Green (<70%), Yellow (70-85%), Red (>85%)
        color_attr = "status_ok"
        if clamped > 85.0:
            color_attr = "status_alert"
        elif clamped > 70.0:
            color_attr = "status_warn"

        bar = "█" * filled_len + "░" * empty_len
        txt = [
            ("card_border", "["),
            (color_attr, bar),
            ("card_border", "] "),
            (color_attr, f"{clamped:5.1f}{self.label_suffix}"),
        ]
        self.text_widget.set_text(txt)


class TabButton(urwid.Button):
    """Button for tab headers without enclosing '< >' symbols."""

    def __init__(self, label: str, on_press: Optional[Callable[[Any, Any], None]] = None, user_data: Any = None) -> None:
        super().__init__("", on_press=on_press, user_data=user_data)
        self._w = urwid.SelectableIcon(label, 0)
        self._label = label

    def set_label(self, label: str) -> None:
        self._label = label
        self._w.set_text(label)


class CustomButton(urwid.WidgetWrap):
    """Styled button with prominent focus borders [ Action ]."""

    def __init__(self, label: str, on_press: Optional[Callable[[Any], None]] = None, user_data: Any = None) -> None:
        self.label = label
        self.on_press = on_press
        self.user_data = user_data
        self.btn = urwid.Button(f" {label} ", on_press=self._clicked)
        styled = urwid.AttrMap(self.btn, "button", focus_map="button_focus")
        super().__init__(styled)

    def _clicked(self, button: Any) -> None:
        if self.on_press:
            self.on_press(self.user_data)


class ModalDialog(urwid.WidgetWrap):
    """Modal overlay dialog for command outputs, prompts, and confirmations."""

    def __init__(
        self,
        title: str = "",
        body_widget: Optional[urwid.Widget] = None,
        buttons: Optional[List[Tuple[str, Callable[[Any], None]]]] = None,
        width: int = 65,
        height: int = 18,
    ) -> None:
        self.title = title
        if body_widget is None:
            body_widget = urwid.Text("")

        content_elements: List[Any] = [
            ("pack", urwid.AttrMap(urwid.Text(f" {title} ", align="center"), "dialog_title")),
            ("pack", urwid.Divider("─")),
        ]

        if "box" in body_widget.sizing():
            content_elements.append(body_widget)
        else:
            content_elements.append(("pack", body_widget))

        # Build button row if buttons provided
        if buttons:
            btn_widgets = []
            for label, cb in buttons:
                btn_widgets.append(CustomButton(label, on_press=lambda b, fn=cb: fn(b)))
            button_grid = urwid.GridFlow(btn_widgets, cell_width=16, h_sep=2, v_sep=1, align="center")
            content_elements.extend([
                ("pack", urwid.Divider("─")),
                ("pack", button_grid),
            ])

        content = urwid.Pile(content_elements)
        boxed = urwid.LineBox(content)
        styled_box = urwid.AttrMap(boxed, "dialog_bg")
        super().__init__(styled_box)
        self.width = width
        self.height = height
