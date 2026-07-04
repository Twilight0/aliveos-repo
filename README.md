# AliveOS Pacman Repository

This repository compiles and hosts custom stable versions of Arch User Repository (AUR) and local packages for the **AliveOS** distribution.

It is automatically compiled and updated via **GitHub Actions** and hosted using **GitHub Pages**.

## Packages Included

1.  **`aliveos-assets`** - Custom icon themes and graphic assets for AliveOS.
2.  **`aliveos-settings`** - Core configuration and styling packages for AliveOS.
3.  **`graphite-gtk-theme-git`** - Graphite GTK theme (includes the black compact variant).
4.  **`tela-icon-theme`** - Tela flat icon theme.
5.  **`xlibre-xserver-legacyabi`** - XLibre X11 display server drop-in replacement with legacy ABI support.
6.  **`nvidia-390xx-utils`** - Patched legacy NVIDIA 390.xx drivers compatible with modern kernels and Xlibre.
7.  **`nvidia-340xx-utils`** - Patched legacy NVIDIA 340.xx drivers compatible with modern kernels and Xlibre.

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

