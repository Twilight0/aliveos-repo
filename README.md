# AliveOS Pacman Repository

This repository compiles and hosts custom stable versions of Arch User Repository (AUR) and local packages for the **AliveOS** distribution.

It is automatically compiled and updated via **GitHub Actions** and hosted using **GitHub Pages**.

## Packages Included

1.  **`aliveos-assets`** - Custom icon themes and graphic assets for AliveOS.
2.  **`cinnamon-aliveos`** - Cinnamon desktop environment for AliveOS with Zenity GTK3 dialogs and custom enhancements.
3.  **`dell-xps-brightness-cachyos-lts-v2`** - **Prebuilt** binary Dell XPS L702X EC hardware brightness driver for `linux-cachyos-lts-v2`.
4.  **`dell-xps-brightness-dkms`** - DKMS source package for Dell XPS L702X EC hardware brightness driver.
5.  **`graphite-gtk-theme-git`** - Graphite GTK theme (includes the black compact variant).
6.  **`grub-silent-ldfix`** - Suppressed boot output version of GRUB with linker bugfix.
7.  **`httptoolkit`** - HTTP(S) interception, debugging, and mock proxy desktop application.
8.  **`linux-cachyos-lts-v2`** - Performance-optimized LTS Linux kernel (x86-64-v2 baseline) with BORE scheduler and CPU optimizations.
9.  **`muse-code`** - Terminal-based AI coding agent powered by Meta's Muse Spark with AVX2 legacy CPU emulation fallback and interactive session manager.
10. **`nerd-dictation`** - Voice typing/dictation system using Vosk.
11. **`nouveau-fermi-reclock-cachyos-lts-v2`** - **Prebuilt** binary Nouveau kernel module with Fermi GPU dynamic reclocking and native 120Hz eDP support for `linux-cachyos-lts-v2`.
12. **`nouveau-fermi-reclock-dkms`** - DKMS source package for out-of-tree Nouveau driver.
13. **`nvidia-390xx-cachyos-lts-v2`** - **Prebuilt** binary NVIDIA 390.xx kernel modules (`nvidia.ko`, `nvidia-modeset.ko`, `nvidia-drm.ko`, `nvidia-uvm.ko`) for `linux-cachyos-lts-v2`.
14. **`nvidia-390xx-utils`**, **`nvidia-390xx-dkms`**, **`nvidia-390xx-settings`** - Patched legacy NVIDIA 390.xx userspace drivers, DKMS module sources, and utilities.
15. **`polkit-aliveos`** - Transparent Polkit authentication agent for AliveOS with explicit caller disclosure, UAC screen dimming, and Zenity-GTK3 styling.
16. **`respite`** - GTK3 media player (fork of Parole, Xfce deps removed).
17. **`skript`** - Lightweight GTK3 markdown editor/viewer.
18. **`tela-icon-theme`** - Tela flat icon theme.
19. **`valuate`** - Lightweight calculator application for AliveOS.
20. **`xconnect`** - KDE Connect protocol implementation in Vala/C with GTK3/XApp GUI.
21. **`xdg-desktop-portal-aliveos`** - Portal backend with native multi-view file chooser dialog for AliveOS.
22. **`xlibre-xserver`** & **`xlibre-xserver-legacyabi`** - XLibre drop-in replacement for X11 display server (along with legacy ABI support for older drivers).

---

## How to Add this Repository to Arch/AliveOS

Add the following to the bottom of your `/etc/pacman.conf`:

```ini
[aliveos-repo]
SigLevel = Optional TrustAll
Server = https://Twilight0.github.io/aliveos-repo/x86_64
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

