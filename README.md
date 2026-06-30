# AliveOS Pacman Repository

This repository compiles and hosts custom stable versions of Arch User Repository (AUR) packages for the **AliveOS** distribution.

It is automatically compiled and updated via **GitHub Actions** and hosted using **GitHub Pages**.

## Packages Included

1.  **`dory`** (compiled from `dory-git` as stable) - Nemo-based file picker.
2.  **`grub-silent-ldfix`** - Suppressed boot output version of GRUB with linker bugfix.
3.  **`xdg-desktop-portal-xapp-filepicker`** (compiled from `xdg-desktop-portal-xapp-filepicker-git` as stable) - Portal backend using XApp file dialogs.
4.  **`viewmd`** - Lightweight GTK-based markdown viewer.
5.  **`httptoolkit-bin`** - Binary release of HTTP Toolkit debugging client.

---

## How to Add this Repository to Arch/AliveOS

Add the following to the bottom of your `/etc/pacman.conf`:

```ini
[aliveos-repo]
SigLevel = Optional TrustAll
Server = https://<your-github-username>.github.io/aliveos-repo/x86_64
```

*Replace `<your-github-username>` with your actual GitHub username.*

Then synchronize your package database and update:

```bash
sudo pacman -Syu
```

Now you can install the custom packages directly:

```bash
sudo pacman -S dory grub-silent-ldfix xdg-desktop-portal-xapp-filepicker viewmd httptoolkit-bin
```

---

## Build Actions Pipeline

The repository build pipeline runs on a scheduled weekly cron inside a privileged Arch Linux runner container:
1.  Downloads packages from AUR.
2.  Renames specified packages (e.g. `*-git` to stable names) and updates provides/conflicts parameters using `clean_pkgbuild.py`.
3.  Compiles the packages via `makepkg`.
4.  Assembles the repository file database (`aliveos-repo.db`) via `repo-add`.
5.  Deploys the static files (`x86_64/*.pkg.tar.zst` and index databases) to the `gh-pages` branch, making them instantly downloadable.
