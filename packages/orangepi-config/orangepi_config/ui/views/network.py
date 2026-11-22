"""
Network configuration view: Ethernet & Wi-Fi settings, XR819 diagnostics, and driver recovery.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import urwid

from orangepi_config.backend.network_ctrl import NetworkController
from orangepi_config.ui.widgets import CustomButton, ModalDialog


class NetworkView(urwid.WidgetWrap):
    def __init__(
        self,
        net_ctrl: NetworkController,
        on_status_msg: Optional[Callable[[str, bool], None]] = None,
        on_modal_dialog: Optional[Callable[[urwid.Widget], None]] = None,
        on_close_modal: Optional[Callable[[], None]] = None,
    ) -> None:
        self.net_ctrl = net_ctrl
        self.on_status_msg = on_status_msg
        self.on_modal_dialog = on_modal_dialog
        self.on_close_modal = on_close_modal

        self.txt_status = urwid.Text(("status_info", "Network and XR819 diagnostics initialized."))
        self.pile_ifaces = urwid.Pile([])
        self.pile_xr819 = urwid.Pile([])
        self.pile_pia = urwid.Pile([])
        self.pile_ddns = urwid.Pile([])

        # Static IP inputs
        self.edit_iface = urwid.Edit(("card_label", "Interface (e.g., eth0, wlan0): "), "eth0")
        self.edit_ip = urwid.Edit(("card_label", "Static IP/CIDR (e.g. 192.168.1.150/24): "), "")
        self.edit_gw = urwid.Edit(("card_label", "Default Gateway (e.g. 192.168.1.1): "), "")
        self.edit_dns = urwid.Edit(("card_label", "DNS Override for Interface (optional): "), "")

        # Dedicated DNS controls
        self.edit_global_dns = urwid.Edit(("card_label", "Active DNS Servers (or 'auto'): "), "")

        layout = self._build_layout()
        fill = urwid.Filler(layout, valign="top")
        super().__init__(fill)

        self.refresh()

    def _build_card(self, title: str, content_widgets: List[urwid.Widget]) -> urwid.Widget:
        header = urwid.Text([("card_title", f" {title} ")])
        pile = urwid.Pile([header, urwid.Divider("─")] + content_widgets)
        return urwid.LineBox(pile)

    def _build_layout(self) -> urwid.Widget:
        # Card 1: Interfaces Status
        card_ifaces = self._build_card("Active Interfaces & Connectivity", [
            self.pile_ifaces,
            urwid.Divider(" "),
            CustomButton("Refresh Network State", on_press=lambda _: self.refresh()),
        ])

        # Card 2: Dedicated DNS Configuration
        btn_apply_dns = CustomButton("Apply DNS", on_press=lambda _: self._apply_custom_dns())
        btn_dns_auto = CustomButton("Auto (DHCP / Gateway)", on_press=lambda _: self._set_dns_preset("auto"))
        btn_dns_cf = CustomButton("Cloudflare (1.1.1.1)", on_press=lambda _: self._set_dns_preset("1.1.1.1 1.0.0.1"))
        btn_dns_google = CustomButton("Google (8.8.8.8)", on_press=lambda _: self._set_dns_preset("8.8.8.8 8.8.4.4"))
        btn_dns_quad9 = CustomButton("Quad9 (9.9.9.9)", on_press=lambda _: self._set_dns_preset("9.9.9.9 149.112.112.112"))
        btn_dns_adguard = CustomButton("AdGuard (94.140.14.14)", on_press=lambda _: self._set_dns_preset("94.140.14.14 94.140.15.15"))

        card_dns = self._build_card("DNS Server Configuration", [
            urwid.Text(("card_label", "Configure active upstream DNS servers (systemd-resolved & networkd):")),
            urwid.Divider(" "),
            urwid.Columns([
                (55, self.edit_global_dns),
                (16, btn_apply_dns),
            ]),
            urwid.Divider(" "),
            urwid.Text(("card_label", "Quick Presets:")),
            urwid.GridFlow([
                btn_dns_auto,
                btn_dns_cf,
                btn_dns_google,
                btn_dns_quad9,
                btn_dns_adguard,
            ], cell_width=25, h_sep=1, v_sep=1, align="left"),
        ])

        # Card 3: IP Configuration
        btn_apply_dhcp = CustomButton("Set Selected to DHCP", on_press=lambda _: self._apply_dhcp())
        btn_apply_static = CustomButton("Apply Static IP", on_press=lambda _: self._apply_static())

        card_config = self._build_card("Interface IPv4 & DHCP Configuration", [
            self.edit_iface,
            self.edit_dns,
            urwid.Divider(" "),
            btn_apply_dhcp,
            urwid.Divider("─"),
            urwid.Text(("card_label", "Static IP Mode:")),
            self.edit_ip,
            self.edit_gw,
            urwid.Divider(" "),
            btn_apply_static,
        ])

        # Card 4: XR819 Wireless Driver & Diagnostics
        btn_scan = CustomButton("Scan Wi-Fi Networks", on_press=lambda _: self._show_wifi_scan())
        btn_connect = CustomButton("Connect to Wi-Fi Network", on_press=lambda _: self._show_wifi_connect_dialog())
        btn_powersave = CustomButton("Disable Wi-Fi Sleep Bug (iw powersave off)", on_press=lambda _: self._disable_powersave())
        btn_reload = CustomButton("Reload XR819 Driver (Bus Reset)", on_press=lambda _: self._reload_driver())
        btn_unblock = CustomButton("Unblock RFKill", on_press=lambda _: self._unblock_rfkill())

        grid_actions = urwid.GridFlow([
            btn_scan,
            btn_connect,
            btn_powersave,
            btn_reload,
            btn_unblock,
        ], cell_width=36, h_sep=2, v_sep=1, align="left")

        card_xr819 = self._build_card("XR819 Wireless Hardware & Driver Diagnostics", [
            self.pile_xr819,
            urwid.Divider("─"),
            grid_actions,
        ])

        # Card 5: Private Internet Access (PIA) WireGuard VPN
        btn_pia_cfg = CustomButton("Configure & Connect PIA", on_press=lambda _: self._show_pia_dialog())
        btn_pia_stop = CustomButton("Disconnect / Stop PIA", on_press=lambda _: self._stop_pia())
        btn_pia_boot = CustomButton("Toggle Boot Autostart", on_press=lambda _: self._toggle_pia_autostart())

        card_pia = self._build_card("Private Internet Access (PIA) WireGuard VPN", [
            self.pile_pia,
            urwid.Divider("─"),
            urwid.GridFlow([
                btn_pia_cfg,
                btn_pia_stop,
                btn_pia_boot,
            ], cell_width=30, h_sep=2, v_sep=1, align="left"),
        ])

        # Card 6: Dynamic DNS (No-IP)
        btn_ddns_cfg = CustomButton("Configure No-IP DDNS", on_press=lambda _: self._show_ddns_dialog())
        btn_ddns_run = CustomButton("Update DDNS Now", on_press=lambda _: self._run_ddns_now())
        btn_ddns_boot = CustomButton("Toggle DDNS Timer", on_press=lambda _: self._toggle_ddns_autostart())

        card_ddns = self._build_card("Dynamic DNS (No-IP Updater)", [
            self.pile_ddns,
            urwid.Divider("─"),
            urwid.GridFlow([
                btn_ddns_cfg,
                btn_ddns_run,
                btn_ddns_boot,
            ], cell_width=28, h_sep=2, v_sep=1, align="left"),
        ])

        return urwid.Pile([
            urwid.AttrMap(self.txt_status, "status_info"),
            urwid.Divider(" "),
            card_ifaces,
            urwid.Divider(" "),
            card_dns,
            urwid.Divider(" "),
            card_config,
            urwid.Divider(" "),
            card_xr819,
            urwid.Divider(" "),
            card_pia,
            urwid.Divider(" "),
            card_ddns,
        ])

    def refresh(self) -> None:
        """Polls backend and refreshes network status."""
        # 1. Interfaces
        ifaces = self.net_ctrl.get_interfaces()
        rows: List[urwid.Widget] = []
        for ifc in ifaces:
            state_attr = "status_ok" if ifc["operstate"] == "up" else "status_warn"
            carrier_str = "[Plugged]" if ifc["carrier"] else "[Unplugged]" if ifc["type"] == "ethernet" else ""
            ip_str = ifc["ipv4"] if ifc["ipv4"] else "No IP assigned"
            
            row = urwid.Columns([
                (14, urwid.Text([("card_label", f"  • {ifc['name']}:")])),
                (12, urwid.Text([(state_attr, f"[{ifc['operstate'].upper()}]")])),
                (14, urwid.Text(("status_info", carrier_str))),
                (30, urwid.Text([("card_label", "IPv4: "), ("card_value", ip_str)])),
                urwid.Text([("card_label", "MAC: "), ("status_info", ifc["mac"])]),
            ])
            rows.append(row)
        
        if not rows:
            rows.append(urwid.Text(("status_warn", "  No active network interfaces detected.")))
        self.pile_ifaces.contents = [(r, ("pack", None)) for r in rows]

        # 2. XR819 diagnostics
        diag = self.net_ctrl.get_xr819_diagnostics()
        drv_text = ("status_ok", "[xradio_wlan Loaded]") if diag["driver_loaded"] else ("status_warn", "[Driver Not Loaded]")
        ifc_name = diag.get("interface_name") or "Wireless"
        ifc_text = ("status_ok", f"[{ifc_name} Present]") if diag["interface_present"] else ("status_warn", f"[{ifc_name} Missing]")
        fw_text = ("status_ok", "[Firmware: OK]") if diag["firmware_ok"] else ("status_alert", "[Firmware Missing/Incomplete]")
        rf_text = ("status_alert", "[RFKill: BLOCKED]") if diag["rfkill_blocked"] else ("status_ok", "[RFKill: Unblocked]")
        ps_text = ("status_ok", "[Powersave: OFF (Keep-Alive)]") if diag["powersave_off"] else ("status_warn", "[Powersave: ON (Sleep Prone)]")

        fw_breakdown = ", ".join(f"{k}: {'OK' if v else 'MISSING'}" for k, v in diag["firmware_files"].items())

        xr_rows = [
            urwid.Columns([
                (26, urwid.Text([("card_label", "  Driver Status: "), drv_text])),
                (24, urwid.Text([("card_label", "Interface: "), ifc_text])),
                (24, urwid.Text([("card_label", "RFKill: "), rf_text])),
                urwid.Text([("card_label", "Firmware: "), fw_text]),
            ]),
            urwid.Text([("card_label", "  Firmware Files: "), ("status_info", fw_breakdown)]),
            urwid.Text([("card_label", "  Sleep Bug Mitigation: "), ps_text]),
        ]

        if diag["dmesg_errors"]:
            xr_rows.append(urwid.Text(("card_label", "  Recent Driver Kernel Logs:")))
            for err in diag["dmesg_errors"][-3:]:
                xr_rows.append(urwid.Text(("status_warn", f"    {err}")))

        self.pile_xr819.contents = [(r, ("pack", None)) for r in xr_rows]

        # 3. Active DNS servers (always show stored/active values)
        active_dns = " ".join(self.net_ctrl.get_dns_servers())
        self.edit_global_dns.set_edit_text(active_dns if active_dns else "auto")

        # 4. PIA WireGuard VPN status
        pia = self.net_ctrl.get_pia_status()
        pia_state = ("status_ok", "[CONNECTED]") if pia["active"] else ("status_warn", "[STOPPED]")
        pia_boot = ("status_ok", "[Autostart: ON]") if pia["enabled"] else ("status_info", "[Autostart: OFF]")
        pia_cfg = ("status_ok", "[Credentials Saved]") if pia["configured"] else ("status_warn", "[Not Configured]")
        pia_scripts = ("status_ok", "[Scripts Ready]") if pia["scripts_installed"] else ("status_warn", "[Will Download on Setup]")
        pf_str = pia["forwarded_port"] if pia["forwarded_port"] else ("Pending / N/A" if pia["active"] else "-")

        self.pile_pia.contents = [
            (urwid.Columns([
                (22, urwid.Text([("card_label", "  Tunnel: "), pia_state])),
                (22, urwid.Text([("card_label", "Boot: "), pia_boot])),
                (26, urwid.Text([("card_label", "Config: "), pia_cfg])),
                urwid.Text([("card_label", "PIA: "), pia_scripts]),
            ]), ("pack", None)),
            (urwid.Text([("card_label", "  Forwarded Port: "), ("card_value", pf_str)]), ("pack", None)),
        ]

        # 5. No-IP DDNS status
        ddns = self.net_ctrl.get_ddns_status()
        ddns_tmr = ("status_ok", "[TIMER ON]") if ddns["timer_active"] else ("status_warn", "[TIMER OFF]")
        ddns_cfg = ("status_ok", "[Configured]") if ddns["configured"] else ("status_warn", "[Not Configured]")
        ddns_host = ddns["hostname"] or "-"
        ddns_ip = ddns["last_ip"] or "-"

        self.pile_ddns.contents = [
            (urwid.Columns([
                (22, urwid.Text([("card_label", "  Timer: "), ddns_tmr])),
                (22, urwid.Text([("card_label", "Config: "), ddns_cfg])),
                urwid.Text([("card_label", "Last IP: "), ("card_value", ddns_ip)]),
            ]), ("pack", None)),
            (urwid.Text([("card_label", "  Hostname: "), ("card_value", ddns_host)]), ("pack", None)),
        ]

    def _set_dns_preset(self, preset_servers: str) -> None:
        self.edit_global_dns.set_edit_text(preset_servers)
        self._apply_custom_dns()

    def _apply_custom_dns(self) -> None:
        dns_str = self.edit_global_dns.get_edit_text().strip()
        if not dns_str:
            self._set_status("DNS server string cannot be empty.", ok=False)
            return
        self._set_status(f"Applying DNS servers: {dns_str}...", ok=True)
        ok, msg = self.net_ctrl.set_dns_servers(dns_str)
        self._set_status(msg, ok=ok)
        self.refresh()

    def _apply_dhcp(self) -> None:
        iface = self.edit_iface.get_edit_text().strip()
        dns = self.edit_dns.get_edit_text().strip()
        if not iface:
            self._set_status("Please specify an interface name.", ok=False)
            return
        ok, msg = self.net_ctrl.configure_interface(iface, mode="dhcp", dns=dns)
        self._set_status(msg, ok=ok)
        self.refresh()

    def _apply_static(self) -> None:
        iface = self.edit_iface.get_edit_text().strip()
        ip = self.edit_ip.get_edit_text().strip()
        gw = self.edit_gw.get_edit_text().strip()
        dns = self.edit_dns.get_edit_text().strip()

        if not iface or not ip:
            self._set_status("Interface and Static IP address are required.", ok=False)
            return

        ok, msg = self.net_ctrl.configure_interface(iface, mode="static", ip=ip, gateway=gw, dns=dns)
        self._set_status(msg, ok=ok)
        self.refresh()

    def _disable_powersave(self) -> None:
        ok, msg = self.net_ctrl.disable_wifi_powersave()
        self._set_status(msg, ok=ok)
        self.refresh()

    def _reload_driver(self) -> None:
        self._set_status("Reloading xradio_wlan driver and resetting SDIO bus...", ok=True)
        ok, msg = self.net_ctrl.reload_xr819_driver()
        self._set_status(msg, ok=ok)
        self.refresh()

    def _unblock_rfkill(self) -> None:
        ok, msg = self.net_ctrl.unblock_rfkill()
        self._set_status(msg, ok=ok)
        self.refresh()

    def _show_wifi_scan(self) -> None:
        if not self.on_modal_dialog:
            return
        self._set_status("Scanning wireless channels...", ok=True)
        networks = self.net_ctrl.scan_wifi_networks()

        net_widgets = []
        if not networks:
            net_widgets.append(urwid.Text(("status_warn", "No Wi-Fi networks found. Is antenna attached and interface UP?")))
        else:
            for net in networks:
                txt = urwid.Text([
                    ("card_value", f"• {net['ssid']} "),
                    ("status_info", f"({net['signal']}) "),
                    ("status_ok", f"[{net['security']}]"),
                ])
                net_widgets.append(txt)

        close_btn = CustomButton("Close", on_press=lambda _: self._close_modal())
        pile = urwid.Pile([
            urwid.Text(("card_title", "Discovered Wi-Fi Networks:")),
            urwid.Divider("─"),
            urwid.BoxAdapter(urwid.ListBox(urwid.SimpleFocusListWalker(net_widgets)), height=min(12, max(4, len(net_widgets)))),
            urwid.Divider(" "),
            close_btn,
        ])
        dialog = ModalDialog(title="Wi-Fi Channel Scan", body_widget=pile, width=60, height=18)
        self.on_modal_dialog(dialog)

    def _show_wifi_connect_dialog(self) -> None:
        if not self.on_modal_dialog:
            return

        edit_ssid = urwid.Edit(("card_label", "SSID: "), "")
        edit_pass = urwid.Edit(("card_label", "Passphrase: "), "", mask="*")

        def _do_connect() -> None:
            ssid = edit_ssid.get_edit_text().strip()
            psk = edit_pass.get_edit_text().strip()
            self._close_modal()
            self._set_status(f"Connecting to '{ssid}'...", ok=True)
            ok, msg = self.net_ctrl.connect_wifi_wpa(ssid, psk)
            self._set_status(msg, ok=ok)
            self.refresh()

        btn_conn = CustomButton("Connect & Save", on_press=lambda _: _do_connect())
        btn_cancel = CustomButton("Cancel", on_press=lambda _: self._close_modal())

        wlan_label = self.net_ctrl.get_primary_wireless_interface() or "Wireless"
        pile = urwid.Pile([
            urwid.Text(("card_title", f"Configure Wi-Fi Connection ({wlan_label})")),
            urwid.Divider("─"),
            edit_ssid,
            edit_pass,
            urwid.Divider(" "),
            urwid.Columns([
                (20, btn_conn),
                (14, btn_cancel),
            ]),
        ])
        dialog = ModalDialog(title="Connect to Wi-Fi", body_widget=pile, width=54, height=12)
        self.on_modal_dialog(dialog)

    def _show_pia_dialog(self) -> None:
        if not self.on_modal_dialog:
            return

        edit_user = urwid.Edit(("card_label", "PIA Username (p#######): "), "")
        edit_pass = urwid.Edit(("card_label", "PIA Password: "), "", mask="*")
        edit_region = urwid.Edit(("card_label", "Preferred Region (blank = fastest): "), "")
        edit_dip = urwid.Edit(("card_label", "Dedicated IP Token (optional): "), "")
        chk_pf = urwid.CheckBox("Enable Port Forwarding (non-US servers)", state=True)

        def _do_pia() -> None:
            user = edit_user.get_edit_text().strip()
            pwd = edit_pass.get_edit_text().strip()
            region = edit_region.get_edit_text().strip()
            dip = edit_dip.get_edit_text().strip()
            pf = chk_pf.get_state()
            self._close_modal()
            self._set_status("Configuring PIA WireGuard VPN...", ok=True)
            ok, msg = self.net_ctrl.configure_pia_wireguard(
                user=user,
                password=pwd,
                port_forward=pf,
                dip_token=dip,
                region=region,
            )
            self._set_status(msg, ok=ok)
            self.refresh()

        btn_save = CustomButton("Save & Connect", on_press=lambda _: _do_pia())
        btn_pick = CustomButton("Pick Server...", on_press=lambda _: self._show_pia_server_picker(edit_region, chk_pf, dialog))
        btn_cancel = CustomButton("Cancel", on_press=lambda _: self._close_modal())

        pile = urwid.Pile([
            urwid.Text(("card_title", "Private Internet Access (WireGuard)")),
            urwid.Divider("─"),
            edit_user,
            edit_pass,
            urwid.Columns([
                edit_region,
                (18, btn_pick),
            ]),
            edit_dip,
            chk_pf,
            urwid.Divider(" "),
            urwid.Columns([
                (20, btn_save),
                (14, btn_cancel),
            ]),
        ])
        dialog = ModalDialog(title="Configure PIA WireGuard VPN", body_widget=pile, width=68, height=16)
        self.on_modal_dialog(dialog)

    def _show_pia_server_picker(
        self,
        edit_region: urwid.Edit,
        chk_pf: urwid.CheckBox,
        parent_dialog: ModalDialog,
    ) -> None:
        if not self.on_modal_dialog:
            return
        regions = self.net_ctrl.get_pia_regions()
        items: List[urwid.Widget] = []

        def _select(reg_id: str, pf_ok: Optional[bool]) -> None:
            edit_region.set_edit_text(reg_id)
            if pf_ok is not None:
                chk_pf.set_state(pf_ok)
            self._close_modal()
            self.on_modal_dialog(parent_dialog)

        items.append(CustomButton("Auto (Fastest Latency) [PF]", on_press=lambda _: _select("", True)))
        for r in regions:
            pf_tag = " [PF]" if r["port_forward"] else ""
            label = f"{r['name']} ({r['id']}){pf_tag}"
            items.append(
                CustomButton(
                    label,
                    on_press=lambda _, rid=r["id"], pf=r["port_forward"]: _select(rid, pf),
                )
            )

        if not regions:
            items.append(urwid.Text(("status_warn", "Could not fetch PIA region list (check internet/DNS).")))

        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(items))
        btn_back = CustomButton("Back", on_press=lambda _: _select(edit_region.get_edit_text(), None))
        pile = urwid.Pile([
            ("pack", urwid.Text(("card_title", "Select PIA WireGuard Server ([PF] = Port Forwarding)"))),
            ("pack", urwid.Divider("─")),
            ("weight", 1, listbox),
            ("pack", urwid.Divider("─")),
            ("pack", btn_back),
        ])
        picker = ModalDialog(title="PIA Server Selection", body_widget=pile, width=66, height=22)
        self._close_modal()
        self.on_modal_dialog(picker)

    def _stop_pia(self) -> None:
        ok, msg = self.net_ctrl.stop_pia_vpn()
        self._set_status(msg, ok=ok)
        self.refresh()

    def _toggle_pia_autostart(self) -> None:
        pia = self.net_ctrl.get_pia_status()
        ok, msg = self.net_ctrl.set_pia_autostart(not pia["enabled"])
        self._set_status(msg, ok=ok)
        self.refresh()

    def _show_ddns_dialog(self) -> None:
        if not self.on_modal_dialog:
            return
        cur = self.net_ctrl.get_ddns_status()
        edit_host = urwid.Edit(("card_label", "Hostname (e.g. myhost.ddns.net): "), cur["hostname"])
        edit_user = urwid.Edit(("card_label", "No-IP Username / DDNS Key: "), cur["username"])
        edit_pass = urwid.Edit(("card_label", "No-IP Password / Key Secret: "), "", mask="*")
        chk_timer = urwid.CheckBox("Enable 10-min systemd timer", state=True)

        def _do_save() -> None:
            ok, msg = self.net_ctrl.configure_noip_ddns(
                edit_host.get_edit_text(),
                edit_user.get_edit_text(),
                edit_pass.get_edit_text(),
                enable_timer=chk_timer.get_state(),
            )
            self._close_modal()
            self._set_status(msg, ok=ok)
            self.refresh()

        btn_save = CustomButton("Save & Update", on_press=lambda _: _do_save())
        btn_cancel = CustomButton("Cancel", on_press=lambda _: self._close_modal())
        pile = urwid.Pile([
            edit_host,
            edit_user,
            edit_pass,
            urwid.Divider(" "),
            chk_timer,
            urwid.Divider("─"),
            urwid.Columns([(20, btn_save), (14, btn_cancel)], dividechars=2),
        ])
        dialog = ModalDialog(title="Configure No-IP DDNS Updater", body_widget=pile, width=64, height=16)
        self.on_modal_dialog(dialog)

    def _run_ddns_now(self) -> None:
        ok, msg = self.net_ctrl.run_ddns_update()
        self._set_status(msg, ok=ok)
        self.refresh()

    def _toggle_ddns_autostart(self) -> None:
        ddns = self.net_ctrl.get_ddns_status()
        ok, msg = self.net_ctrl.set_ddns_autostart(not ddns["timer_enabled"])
        self._set_status(msg, ok=ok)
        self.refresh()

    def _close_modal(self) -> None:
        if self.on_close_modal:
            self.on_close_modal()

    def _set_status(self, msg: str, ok: bool = True) -> None:
        attr = "status_ok" if ok else "status_alert"
        self.txt_status.set_text([(attr, f"[{msg}]")])
        if self.on_status_msg:
            self.on_status_msg(msg, ok)
