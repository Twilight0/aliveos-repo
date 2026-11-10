"""
Command-line entry point for orangepi-config.
"""

from __future__ import annotations

import argparse
import os
import sys

from orangepi_config import __version__
from orangepi_config.ui.app import OrangePiConfigApp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="orangepi-config",
        description="Lightweight Urwid TUI Configuration and Diagnostics Utility for Orange Pi Zero (Allwinner H2+/H3) on Arch Linux ARM.",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args()


def main() -> None:
    parse_args()

    # Warn if not running with root privileges
    if os.geteuid() != 0:
        sys.stderr.write(
            "\033[33m[WARNING] Running without root privileges.\033[0m\n"
            "Hardware toggles (CPU governor, LED triggers) and package installations require root.\n"
            "For full functionality, consider running with: sudo orangepi-config\n\n"
        )

    try:
        app = OrangePiConfigApp()
        app.run()
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        sys.stderr.write(f"\n[Error] {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
