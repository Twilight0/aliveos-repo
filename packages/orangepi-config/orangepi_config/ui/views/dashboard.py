"""
Dashboard view: Real-time diagnostics, CPU stats, thermals, memory, and disk usage.
"""

from __future__ import annotations

from typing import Any, List
import urwid

from orangepi_config.backend.system_info import SystemInfo
from orangepi_config.ui.widgets import MeterBar


class DashboardView(urwid.WidgetWrap):
    def __init__(self, sys_info: SystemInfo) -> None:
        self.sys_info = sys_info

        # Dynamic text widgets
        self.txt_model = urwid.Text("")
        self.txt_kernel = urwid.Text("")
        self.txt_uptime = urwid.Text("")
        self.txt_load = urwid.Text("")
        self.txt_temp = urwid.Text("")
        
        self.meter_cpu = MeterBar(0.0, width=20)
        self.txt_gov = urwid.Text("")
        self.pile_cores = urwid.Pile([])

        self.meter_mem = MeterBar(0.0, width=20)
        self.txt_mem_details = urwid.Text("")
        self.meter_swap = MeterBar(0.0, width=20)
        self.txt_swap_details = urwid.Text("")

        self.meter_disk = MeterBar(0.0, width=20)
        self.txt_disk_details = urwid.Text("")

        self.pile_net = urwid.Pile([])

        # Build UI layout
        body_pile = self._build_layout()
        fill = urwid.Filler(body_pile, valign="top")
        super().__init__(fill)

        # Initial refresh
        self.refresh()

    def _build_card(self, title: str, content_widgets: List[urwid.Widget]) -> urwid.Widget:
        """Wraps widgets in a bordered card with a cyan header."""
        header = [("card_title", f" {title} ")]
        pile = urwid.Pile([urwid.Text(header)] + content_widgets)
        return urwid.LineBox(pile)

    def _build_layout(self) -> urwid.Pile:
        # Section 1: System Overview Card
        sys_grid = urwid.GridFlow([
            self._label_val("Model:", self.txt_model),
            self._label_val("Kernel:", self.txt_kernel),
            self._label_val("Uptime:", self.txt_uptime),
            self._label_val("Load Avg:", self.txt_load),
            self._label_val("SoC Temp:", self.txt_temp),
        ], cell_width=32, h_sep=2, v_sep=1, align="left")
        card_sys = self._build_card("System Overview", [sys_grid])

        # Section 2: CPU & Thermals Card
        cpu_widgets = [
            urwid.Columns([
                (14, urwid.Text(("card_label", "Overall CPU:"))),
                (32, self.meter_cpu),
                self.txt_gov,
            ]),
            urwid.Divider(" "),
            self.pile_cores,
        ]
        card_cpu = self._build_card("CPU Diagnostics & Thermals", cpu_widgets)

        # Section 3: Memory & Storage Card
        mem_widgets = [
            urwid.Columns([
                (14, urwid.Text(("card_label", "RAM Usage:"))),
                (32, self.meter_mem),
                self.txt_mem_details,
            ]),
            urwid.Columns([
                (14, urwid.Text(("card_label", "Swap Usage:"))),
                (32, self.meter_swap),
                self.txt_swap_details,
            ]),
            urwid.Divider("─"),
            urwid.Columns([
                (14, urwid.Text(("card_label", "Root Disk (/):"))),
                (32, self.meter_disk),
                self.txt_disk_details,
            ]),
        ]
        card_mem = self._build_card("Memory & Storage Utilization", mem_widgets)

        # Section 4: Network Interfaces Card
        card_net = self._build_card("Active Network Interfaces", [self.pile_net])

        return urwid.Pile([
            card_sys,
            card_cpu,
            card_mem,
            card_net,
        ])

    def _label_val(self, label: str, val_widget: urwid.Widget) -> urwid.Columns:
        return urwid.Columns([
            (11, urwid.Text(("card_label", label))),
            val_widget,
        ])

    def refresh(self) -> None:
        """Polls backend and updates all telemetry labels."""
        # Overview
        model = self.sys_info.get_soc_model()
        kernel = self.sys_info.get_kernel_version()
        uptime_str, _ = self.sys_info.get_uptime()
        load = self.sys_info.get_load_average()
        temp = self.sys_info.get_temperature()

        self.txt_model.set_text(("card_value", model))
        self.txt_kernel.set_text(("card_value", kernel))
        self.txt_uptime.set_text(("card_value", uptime_str))
        self.txt_load.set_text(("card_value", f"{load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"))

        if temp is not None:
            temp_attr = "status_ok" if temp < 65.0 else ("status_warn" if temp < 78.0 else "status_alert")
            self.txt_temp.set_text([(temp_attr, f"{temp:.1f} °C")])
        else:
            self.txt_temp.set_text(("status_info", "N/A"))

        # CPU info
        cpu_data = self.sys_info.get_cpu_info()
        self.meter_cpu.set_percent(cpu_data["usage_percent"])
        self.txt_gov.set_text([("card_label", " Governor: "), ("status_info", cpu_data["governor"])])

        core_widgets = []
        for core in cpu_data["cores"]:
            cid = core["id"]
            if core["online"]:
                freq_mhz = core["freq_mhz"]
                c_txt = [
                    ("card_label", f"  Core {cid}: "),
                    ("status_ok", "[ONLINE] "),
                    ("card_value", f"{freq_mhz:4d} MHz"),
                ]
            else:
                c_txt = [
                    ("card_label", f"  Core {cid}: "),
                    ("status_alert", "[OFFLINE]"),
                ]
            core_widgets.append(urwid.Text(c_txt))
        
        # Display cores in a 2-column or 4-column layout
        if core_widgets:
            core_columns = urwid.Columns(core_widgets)
            self.pile_cores.contents = [(core_columns, ("pack", None))]

        # Memory info
        mem = self.sys_info.get_memory_info()
        self.meter_mem.set_percent(mem["used_percent"])
        self.txt_mem_details.set_text([
            ("card_value", f"{mem['used_mb']} MB / {mem['total_mb']} MB "),
            ("card_label", f"(Free: {mem['free_mb']}MB, Avail: {mem['available_mb']}MB)"),
        ])

        self.meter_swap.set_percent(mem["swap_used_percent"])
        self.txt_swap_details.set_text([
            ("card_value", f"{mem['swap_used_mb']} MB / {mem['swap_total_mb']} MB "),
            ("card_label", f"(Free: {mem['swap_free_mb']}MB)"),
        ])

        # Disk info
        disk = self.sys_info.get_disk_info("/")
        self.meter_disk.set_percent(disk["used_percent"])
        self.txt_disk_details.set_text([
            ("card_value", f"{disk['used_gb']:.1f} GB / {disk['total_gb']:.1f} GB "),
            ("card_label", f"(Free: {disk['free_gb']:.1f} GB)"),
        ])

        # Network info
        net_list = self.sys_info.get_network_interfaces()
        net_rows = []
        for iface in net_list:
            state_attr = "status_ok" if iface["state"] == "up" else "status_warn"
            net_rows.append(urwid.Columns([
                (16, urwid.Text([("card_label", "  • "), ("card_value", iface["name"])])),
                (14, urwid.Text([(state_attr, f"[{iface['state'].upper()}]")])),
                urwid.Text([("card_label", "IPv4: "), ("status_info", iface["ip"])]),
            ]))
        if not net_rows:
            net_rows.append(urwid.Text(("status_info", "  No external network interfaces detected.")))
        self.pile_net.contents = [(r, ("pack", None)) for r in net_rows]
