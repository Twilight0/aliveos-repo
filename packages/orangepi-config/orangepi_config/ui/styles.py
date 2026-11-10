"""
Palette and Color Schemes for orangepi-config Urwid TUI.
Optimized for 256-color and 16-color ANSI serial / SSH terminals.
"""

from typing import List, Tuple

# Format: (name, foreground, background, mono, foreground_high, background_high)
PALETTE: List[Tuple[str, str, str]] = [
    # General UI
    ("normal", "light gray", "black"),
    ("bold", "white,bold", "black"),
    ("header", "white,bold", "dark blue"),
    ("header_accent", "light cyan,bold", "dark blue"),
    ("footer", "light gray", "dark gray"),
    ("footer_key", "yellow,bold", "dark gray"),
    
    # Navigation Tabs
    ("tab_inactive", "light gray", "dark blue"),
    ("tab_active", "white,bold", "light blue"),
    ("tab_active_border", "yellow,bold", "light blue"),

    # Cards & Sections
    ("card_title", "light cyan,bold", "black"),
    ("card_border", "dark blue", "black"),
    ("card_label", "light gray", "black"),
    ("card_value", "white,bold", "black"),

    # Status Badges
    ("status_ok", "light green,bold", "black"),
    ("status_warn", "yellow,bold", "black"),
    ("status_alert", "light red,bold", "black"),
    ("status_info", "light cyan", "black"),

    # Meters & Progress
    ("meter_bar_ok", "black", "light green"),
    ("meter_bar_warn", "black", "yellow"),
    ("meter_bar_alert", "black", "light red"),
    ("meter_bar_empty", "dark gray", "dark gray"),

    # Interactive Elements
    ("button", "white,bold", "dark blue"),
    ("button_focus", "black,bold", "light cyan"),
    ("selectable", "light gray", "black"),
    ("selectable_focus", "white,bold", "dark blue"),
    ("checkbox", "light gray", "black"),
    ("checkbox_focus", "white,bold", "dark cyan"),
    
    # Dialogs & Overlays
    ("dialog_bg", "light gray", "dark blue"),
    ("dialog_title", "white,bold", "dark blue"),
    ("dialog_content", "white", "black"),
    ("log_output", "light green", "black"),
]
