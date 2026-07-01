# AliveOS Pacman Repository

This repository compiles and hosts custom stable versions of Arch User Repository (AUR) and local packages for the **AliveOS** distribution.

It is automatically compiled and updated via **GitHub Actions** and hosted using **GitHub Pages**.

## Packages Included

1.  **`aliveos-icon-theme`** - Custom neon dark square icon theme for AliveOS.
2.  **`aliveos-cinnamon-spices`** - Custom Cinnamon applets and extensions (resizable panels, clipboard, updates, places).
3.  **`cinnamon-no-nemo`** - Cinnamon desktop environment repackaged without Nemo dependency (utilizes Dory).
4.  **`dory`** - Nemo-based standalone file chooser portal helper.
5.  **`dory-extensions`** - Standard set of file manager extensions for Dory:
    *   `dory-audio-tab`
    *   `dory-compare`
    *   `dory-dropbox`
    *   `dory-emblems`
    *   `dory-fileroller`
    *   `dory-image-converter`
    *   `dory-media-columns`
    *   `dory-pastebin`
    *   `dory-preview`
    *   `dory-python`
    *   `dory-repairer`
    *   `dory-seahorse`
    *   `dory-share`
    *   `dory-terminal`
6.  **`grub-silent-ldfix`** - Suppressed boot output version of GRUB with linker bugfix.
7.  **`xdg-desktop-portal-xapp-filepicker`** - Portal backend using XApp file dialogs.
8.  **`viewmd`** - Lightweight GTK-based markdown viewer.
9.  **`httptoolkit-bin`** - Binary release of HTTP Toolkit debugging client.
10. **`nerd-dictation`** - Voice typing/dictation system using Vosk.
11. **`xlibre-xserver`** & **Drivers** - XLibre replacement for X11 display server along with modern input and display drivers.
12. **Legacy Clutter Stack** - Compiled from the AUR to satisfy dependencies for `dory-preview`:
    *   `cogl` - Object oriented GL/GLES abstraction utility layer.
    *   `clutter` - Toolkit for creating dynamic user interfaces.
    *   `clutter-gtk` - Clutter integration with GTK+.
    *   `clutter-gst` - GStreamer bindings for Clutter.

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

