# AliveOS Pacman Repository

This repository compiles and hosts custom stable versions of Arch User Repository (AUR) and local packages for the **AliveOS** distribution.

It is automatically compiled and updated via **GitHub Actions** and hosted using **GitHub Pages**.

## Packages Included

1. **`aliveos-assets`** - Custom icon themes and graphic assets for AliveOS.
2. **`blender-3.6-lts`** - Full-featured 3D creation suite (official 3.6 LTS release).
3. **`blender-4.5-lts`** - Full-featured 3D creation suite (official 4.5 LTS release).
4. **`cinnamon-aliveos`** - Cinnamon desktop environment for AliveOS with Zenity GTK3 dialogs and custom enhancements.
5. **`dell-xps-brightness-dkms`** - DKMS source package for Dell XPS L702X EC hardware brightness driver.
6. **`dell-xps-brightness-xanmod-lts-x64v2`** - **Prebuilt** binary Dell XPS L702X EC hardware brightness driver for `linux-xanmod-lts-linux-bin-x64v2`.
7. **`graphite-gtk-theme-git`** - Graphite GTK theme (includes the black compact variant).
8. **`grub-silent`** - Suppressed boot output version of GRUB.
9. **`httptoolkit`** - HTTP(S) interception, debugging, and mock proxy desktop application.
10. **`linux-xanmod-lts-linux-bin-x64v2`** & **`linux-xanmod-lts-linux-headers-bin-x64v2`** - Prebuilt LTS Linux kernel and headers with XanMod performance patches (x86-64-v2 baseline).
11. **`mcp-kodi`** - MCP server that lets an AI assistant control Kodi over its JSON-RPC API (22 tools: transport, volume, library search, queue, history, audio/subtitle switching, notifications).
12. **`mesa-aliveos`** - Patched Mesa (`26.3.1`) with Nouveau Fermi/VP4 VA-API teardown and synchronization fixes, VL compositor YUV420p chroma fix, raised RA spill retry limit, and GLSL 4.60 on `nvc0` (pulled prebuilt from [`Twilight0/mesa-aliveos`](https://github.com/Twilight0/mesa-aliveos) releases).
13. **`muse-code-bin`** - Terminal-based AI coding agent powered by Meta's Muse Spark with opt-in AVX2 legacy CPU emulation fallback and interactive session manager.
14. **`nerd-dictation`** - Voice typing/dictation system using Vosk.
15. **`nouveau-fermi-reclock-dkms`** / **`nouveau-dkms`** - DKMS source package for out-of-tree Nouveau driver.
16. **`nouveau-xanmod-lts-x64v2`** - **Prebuilt** binary Nouveau kernel module with Fermi core, shader, and DDR3 memory reclocking and native 120Hz eDP support for `linux-xanmod-lts-linux-bin-x64v2`.
17. **`nvidia-390xx-utils`**, **`nvidia-390xx-dkms`**, **`nvidia-390xx-settings`** - Patched legacy NVIDIA 390.xx userspace drivers, DKMS module sources, and utilities.
18. **`nvidia-390xx-xanmod-lts-x64v2`** - **Prebuilt** binary NVIDIA 390.xx kernel modules (`nvidia.ko`, `nvidia-modeset.ko`, `nvidia-drm.ko`, `nvidia-uvm.ko`) for `linux-xanmod-lts-linux-bin-x64v2`.
19. **`piper-voices-common`** - Common files (voice index, Speech Dispatcher module config, `piper-dispatcher`) for the Piper neural TTS voices.
20. **`piper-voices-el-gr`** - Greek (el_GR) neural voices for Piper: `joy-medium`, `rapunzelina-medium` and `rapunzelina-low`.
21. **`polkit-aliveos`** - Transparent Polkit authentication agent for AliveOS with explicit caller disclosure, UAC screen dimming, and Zenity-GTK3 styling.
22. **`respite`** - GTK3 media player (fork of Parole, Xfce deps removed).
23. **`skript`** - Lightweight GTK3 markdown editor/viewer.
24. **`tela-icon-theme`** - Tela flat icon theme.
25. **`valuate`** - Lightweight calculator application for AliveOS.
26. **`xconnect`** - KDE Connect protocol implementation in Vala/C with GTK3/XApp GUI.
27. **`xdg-desktop-portal-aliveos`** - Portal backend with native multi-view file chooser dialog for AliveOS.
28. **`orangepi-config`** - Urwid TUI configuration and diagnostics utility for Orange Pi Zero (Allwinner H2+/H3).
29. **`xradio-dkms-git`** - DKMS source driver for the Allwinner XRadio XR819 wireless chip.
30. **`xradio-linux-armv7`** - Prebuilt binary XRadio XR819 wireless module (`xradio_wlan.ko`) for official Arch Linux ARM `linux-armv7`.
31. **`radio-tui`** - Lightweight curses internet radio player with SomaFM and Radio Browser feeds, favorites, recently played stations, YouTube playback, filtering and live volume control.

---

## How to Add this Repository to Arch/AliveOS

Add the following to the bottom of your `/etc/pacman.conf`:

```ini
[aliveos-repo]
SigLevel = Optional TrustAll
Server = https://github.com/Twilight0/aliveos-repo/releases/download/latest
```

Then synchronize your package database and update:

```bash
sudo pacman -Syu
```

---

## Build Actions Pipeline

The repository build pipeline runs on a scheduled weekly cron inside a privileged Arch Linux runner container:
1.  Downloads packages from AUR.
2.  Renames specified packages (e.g. `*-git` to stable names) and updates provides/conflicts parameters using `clean_pkgbuild.py`.
3.  Compiles the packages via `makepkg` (optimized with parallel multi-core compilation).
4.  Assembles the repository file database (`aliveos-repo.db`) via `repo-add`.
5.  Deploys the static files (`x86_64/*.pkg.tar.zst` and index databases) to the `gh-pages` branch, making them instantly downloadable.

