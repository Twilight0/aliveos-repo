import unittest
from orangepi_config.backend.system_info import SystemInfo
from orangepi_config.backend.hardware_ctrl import HardwareController
from orangepi_config.backend.package_mgr import PackageManager
from orangepi_config.backend.network_ctrl import NetworkController


class TestBackend(unittest.TestCase):
    def setUp(self):
        self.sys_info = SystemInfo()
        self.hw_ctrl = HardwareController()
        self.pkg_mgr = PackageManager()
        self.net_ctrl = NetworkController()

    def test_system_info_basics(self):
        model = self.sys_info.get_soc_model()
        self.assertIsInstance(model, str)
        self.assertTrue(len(model) > 0)

        kernel = self.sys_info.get_kernel_version()
        self.assertIsInstance(kernel, str)

        uptime_str, secs = self.sys_info.get_uptime()
        self.assertIsInstance(uptime_str, str)
        self.assertIsInstance(secs, float)

        mem = self.sys_info.get_memory_info()
        self.assertIn("total_mb", mem)
        self.assertIn("used_percent", mem)

        cpu = self.sys_info.get_cpu_info()
        self.assertIn("core_count", cpu)
        self.assertIn("usage_percent", cpu)

        disk = self.sys_info.get_disk_info("/")
        self.assertIn("total_gb", disk)
        self.assertIn("used_percent", disk)

    def test_hardware_controller_discovery(self):
        govs = self.hw_ctrl.get_available_governors()
        self.assertIsInstance(govs, list)
        self.assertTrue(len(govs) > 0)

        cores = self.hw_ctrl.get_core_states()
        self.assertIsInstance(cores, list)

        leds = self.hw_ctrl.get_leds()
        self.assertIsInstance(leds, list)

        wifi = self.hw_ctrl.get_wifi_state()
        self.assertIn("driver_loaded", wifi)

    def test_package_manager(self):
        cats = self.pkg_mgr.get_categories()
        self.assertIn("Core CLI", cats)
        self.assertIn("Networking", cats)
        self.assertIn("Services", cats)
        self.assertIn("Development", cats)
        self.assertIn("Printing", cats)
        self.assertIn("Torrents & Downloads", cats)
        self.assertIn("Media & Audio", cats)
        self.assertIn("Storage & Backups", cats)
        self.assertIn("System Tools", cats)

        pkgs = self.pkg_mgr.get_packages_by_category("Development")
        self.assertTrue(any(p.name == "git" for p in pkgs))
        self.assertTrue(any(p.name == "python-pipx" for p in pkgs))

        torrent_pkgs = self.pkg_mgr.get_packages_by_category("Torrents & Downloads")
        self.assertTrue(any(p.name == "transmission-cli" for p in torrent_pkgs))
        self.assertTrue(any(p.name == "qbittorrent-nox" for p in torrent_pkgs))
        self.assertTrue(any(p.name == "deluge" for p in torrent_pkgs))
        self.assertTrue(any(p.name == "jackett" for p in torrent_pkgs))
        self.assertTrue(any(p.name == "aria2" for p in torrent_pkgs))

        media_pkgs = self.pkg_mgr.get_packages_by_category("Media & Audio")
        self.assertTrue(any(p.name == "minidlna" for p in media_pkgs))

        storage_pkgs = self.pkg_mgr.get_packages_by_category("Storage & Backups")
        self.assertTrue(any(p.name == "nfs-utils" for p in storage_pkgs))
        self.assertTrue(any(p.name == "vsftpd" for p in storage_pkgs))

        svc_pkgs = self.pkg_mgr.get_packages_by_category("Services")
        self.assertTrue(any(p.name == "adguardhome" for p in svc_pkgs))

        print_pkgs = self.pkg_mgr.get_packages_by_category("Printing")
        self.assertTrue(any(p.name == "cups" for p in print_pkgs))

    def test_network_controller(self):
        ifaces = self.net_ctrl.get_interfaces()
        self.assertIsInstance(ifaces, list)

        diag = self.net_ctrl.get_xr819_diagnostics()
        self.assertIn("driver_loaded", diag)
        self.assertIn("firmware_files", diag)
        self.assertIn("rfkill_blocked", diag)

    def test_web_settings_persistence(self):
        import os
        import tempfile
        from unittest.mock import patch
        from orangepi_config import config as cfg_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "orangepi-config")
            with patch.object(cfg_mod, "SYSTEM_CONFIG_PATH", cfg_path), patch.object(
                cfg_mod, "USER_CONFIG_PATH", cfg_path
            ):
                user, pw, port = cfg_mod.get_web_settings()
                self.assertEqual((user, pw, port), ("admin", "admin", 46363))

                saved = cfg_mod.set_web_settings("alive", "s3cr3t", 8080)
                self.assertEqual(saved, cfg_path)
                self.assertEqual(cfg_mod.get_web_settings(), ("alive", "s3cr3t", 8080))

                with self.assertRaises(ValueError):
                    cfg_mod.set_web_settings("bad:user", "pass", 8080)
                with self.assertRaises(ValueError):
                    cfg_mod.set_web_settings("alive", "pass", 70000)


if __name__ == "__main__":
    unittest.main()
