# AliveOS Pacman Repository

This repository compiles and hosts custom stable versions of Arch User Repository (AUR) and local packages for the **AliveOS** distribution.

It is automatically compiled and updated via **GitHub Actions** and hosted using **GitHub Pages**.

## Packages Included

1.  **`aliveos-assets`** - Custom icon themes and graphic assets for AliveOS.
2.  **`cinnamon-aliveos`** - Cinnamon desktop environment for AliveOS (without Nemo, with Dory integration and custom enhancements).
3.  **`dell-xps-brightness-cachyos-lts-v2`** - **Prebuilt** binary Dell XPS L702X EC hardware brightness driver for `linux-cachyos-lts-v2`.
4.  **`dell-xps-brightness-dkms`** - DKMS source package for Dell XPS L702X EC hardware brightness driver.
5.  **`dory`** - Nemo-based standalone file chooser portal helper.
6.  **`dory-extensions`** - Standard set of file manager extensions for Dory:
    *   `dory-audio-tab`, `dory-compare`, `dory-dropbox`, `dory-emblems`, `dory-fileroller`, `dory-image-converter`, `dory-media-columns`, `dory-pastebin`, `dory-preview`, `dory-python`, `dory-repairer`, `dory-seahorse`, `dory-share`, `dory-terminal`
7.  **`graphite-gtk-theme-git`** - Graphite GTK theme (includes the black compact variant).
8.  **`grub-silent-ldfix`** - Suppressed boot output version of GRUB with linker bugfix.
9.  **`httptoolkit`** - HTTP(S) interception, debugging, and mock proxy desktop application.
10. **Legacy Clutter Stack** - Compiled from the AUR to satisfy dependencies for `dory-preview` (`cogl`, `clutter`, `clutter-gtk`, `clutter-gst`).
11. **`linux-cachyos-lts-v2`** - Performance-optimized LTS Linux kernel (x86-64-v2 baseline) with BORE scheduler and CPU optimizations.
12. **`nerd-dictation`** - Voice typing/dictation system using Vosk.
13. **`nouveau-fermi-reclock-cachyos-lts-v2`** - **Prebuilt** binary Nouveau kernel module with Fermi GPU dynamic reclocking and native 120Hz eDP support for `linux-cachyos-lts-v2`.
14. **`nouveau-fermi-reclock-dkms`** - DKMS source package for out-of-tree Nouveau driver.
15. **`nvidia-390xx-cachyos-lts-v2`** - **Prebuilt** binary NVIDIA 390.xx kernel modules (`nvidia.ko`, `nvidia-modeset.ko`, `nvidia-drm.ko`, `nvidia-uvm.ko`) for `linux-cachyos-lts-v2`.
16. **`nvidia-390xx-utils`**, **`nvidia-390xx-dkms`**, **`nvidia-390xx-settings`** - Patched legacy NVIDIA 390.xx userspace drivers, DKMS module sources, and utilities.
17. **`respite`** - GTK3 media player (fork of Parole, Xfce deps removed).
18. **`skript`** - Lightweight GTK3 markdown editor/viewer.
19. **`tela-icon-theme`** - Tela flat icon theme.
20. **`valuate`** - Lightweight calculator application for AliveOS.
21. **`xconnect`** - KDE Connect protocol implementation in Vala/C with GTK3/XApp GUI.
22. **`xdg-desktop-portal-xapp-filepicker`** - Portal backend using XApp file dialogs.
23. **`xlibre-xserver`** & **`xlibre-xserver-legacyabi`** - XLibre drop-in replacement for X11 display server (along with legacy ABI support for older drivers).

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

