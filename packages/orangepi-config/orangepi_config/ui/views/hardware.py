"""
Hardware configuration view: CPU governors, core hotplugging, LED triggers, and WiFi.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional
import urwid

from orangepi_config.backend.hardware_ctrl import HardwareController
from orangepi_config.ui.widgets import CustomButton


class HardwareView(urwid.WidgetWrap):
    def __init__(self, hw_ctrl: HardwareController, on_status_msg: Optional[Callable[[str, bool], None]] = None) -> None:
        self.hw_ctrl = hw_ctrl
        self.on_status_msg = on_status_msg

        self.txt_status = urwid.Text(("status_info", "Select an option below to configure hardware features."))
        
        self.pile_govs = urwid.GridFlow([], cell_width=16, h_sep=2, v_sep=1, align="left")
        self.pile_cores = urwid.Pile([])
        self.pile_leds = urwid.Pile([])
        self.pile_wifi = urwid.Pile([])

        layout = self._build_layout()
        fill = urwid.Filler(layout, valign="top")
        super().__init__(fill)

        self.refresh()

    def _build_card(self, title: str, content_widgets: List[urwid.Widget]) -> urwid.Widget:
        header = [("card_title", f" {title} ")]
        pile = urwid.Pile([urwid.Text(header)] + content_widgets)
        return urwid.LineBox(pile)

    def _build_layout(self) -> urwid.Pile:
        card_gov = self._build_card("CPU Scaling Governor", [
            urwid.Text(("card_label", "Set frequency scaling policy across all active CPU cores:")),
            urwid.Divider(" "),
            self.pile_govs,
        ])

        card_cores = self._build_card("CPU Core Hotplug (Low Power Mode)", [
            urwid.Text(("card_label", "Disable unused cores to reduce heat and power consumption (Core 0 remains active):")),
            urwid.Divider(" "),
            self.pile_cores,
        ])

        card_leds = self._build_card("On-board LED Controls", [
            urwid.Text(("card_label", "Configure LED trigger modes (heartbeat, disk activity, cpu) or manual state:")),
            urwid.Divider(" "),
            self.pile_leds,
        ])

        card_wifi = self._build_card("Wireless (XR819 / wlan0)", [
            self.pile_wifi,
        ])

        card_status = self._build_card("Hardware Control Status", [self.txt_status])

        return urwid.Pile([
            card_status,
            card_gov,
            card_cores,
            card_leds,
            card_wifi,
        ])

    def refresh(self) -> None:
        """Reloads current hardware states into controls."""
        # 1. Governors
        avail_govs = self.hw_ctrl.get_available_governors()
        cur_gov = self.hw_ctrl.get_current_governor()
        gov_buttons = []
        for g in avail_govs:
            prefix = "● " if g == cur_gov else "○ "
            btn = CustomButton(f"{prefix}{g}", on_press=self._on_set_gov, user_data=g)
            gov_buttons.append(btn)
        self.pile_govs.contents = [(b, self.pile_govs.options()) for b in gov_buttons]

        # 2. Cores
        core_states = self.hw_ctrl.get_core_states()
        core_rows = []
        for c in core_states:
            cid = c["core"]
            online = c["online"]
            can_toggle = c["can_toggle"]

            status_text = ("status_ok", "[ONLINE] ") if online else ("status_alert", "[OFFLINE]")
            action_btn = None
            if can_toggle:
                btn_label = "Disable" if online else "Enable"
                action_btn = CustomButton(btn_label, on_press=self._on_toggle_core, user_data=(cid, not online))
            else:
                action_btn = urwid.Text(("card_label", "(Primary Boot Core)"))

            core_rows.append(urwid.Columns([
                (14, urwid.Text([("card_label", f"  CPU Core {cid}:")])),
                (14, urwid.Text([status_text])),
                (20, action_btn),
            ]))
        self.pile_cores.contents = [(r, ("pack", None)) for r in core_rows]

        # 3. LEDs
        led_list = self.hw_ctrl.get_leds()
        led_rows = []
        for led in led_list:
            sys_name = led["sysfs_name"]
            friendly = led["name"]
            cur_trig = led["current_trigger"]
            
            # Popular triggers to offer
            top_triggers = ["heartbeat", "cpu0", "mmc0", "default-on", "none"]
            trig_buttons = []
            for t in top_triggers:
                prefix = "●" if t == cur_trig else "○"
                trig_buttons.append(CustomButton(f"{prefix}{t}", on_press=self._on_set_led_trigger, user_data=(sys_name, t)))
            
            grid_trigs = urwid.GridFlow(trig_buttons, cell_width=14, h_sep=1, v_sep=1, align="left")
            led_rows.append(urwid.Pile([
                urwid.Text([("card_label", f"  • {friendly} "), ("status_info", f"[Trigger: {cur_trig}]")]),
                grid_trigs,
                urwid.Divider(" "),
            ]))
        self.pile_leds.contents = [(r, ("pack", None)) for r in led_rows]

        # 4. WiFi
        wifi = self.hw_ctrl.get_wifi_state()
        wifi_widgets = []
        if wifi["interface_present"]:
            state_text = ("status_ok", "[UP]") if wifi["is_up"] else ("status_warn", "[DOWN]")
            toggle_label = "Bring Interface DOWN" if wifi["is_up"] else "Bring Interface UP"
            toggle_btn = CustomButton(toggle_label, on_press=self._on_toggle_wifi, user_data=not wifi["is_up"])
            wifi_widgets.append(urwid.Columns([
                (20, urwid.Text([("card_label", "  wlan0 Interface: "), state_text])),
                (26, toggle_btn),
            ]))
        else:
            driver_str = "Driver loaded" if wifi["driver_loaded"] else "Driver not loaded"
            wifi_widgets.append(urwid.Text(("status_warn", f"  wlan0 interface not present ({driver_str}).")))
        self.pile_wifi.contents = [(w, ("pack", None)) for w in wifi_widgets]

    def _on_set_gov(self, gov: str) -> None:
        ok, msg = self.hw_ctrl.set_governor(gov)
        attr = "status_ok" if ok else "status_alert"
        self.txt_status.set_text([(attr, msg)])
        self.refresh()

    def _on_toggle_core(self, data: tuple[int, bool]) -> None:
        cid, new_state = data
        ok, msg = self.hw_ctrl.set_core_online(cid, new_state)
        attr = "status_ok" if ok else "status_alert"
        self.txt_status.set_text([(attr, msg)])
        self.refresh()

    def _on_set_led_trigger(self, data: tuple[str, str]) -> None:
        led_name, trigger = data
        ok, msg = self.hw_ctrl.set_led_trigger(led_name, trigger)
        attr = "status_ok" if ok else "status_alert"
        self.txt_status.set_text([(attr, msg)])
        self.refresh()

    def _on_toggle_wifi(self, target_state: bool) -> None:
        ok, msg = self.hw_ctrl.toggle_wifi(target_state)
        attr = "status_ok" if ok else "status_alert"
        self.txt_status.set_text([(attr, msg)])
        self.refresh()
