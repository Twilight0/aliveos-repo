#!/usr/bin/env bash

# Exit on errors
set -e

# Optimize makepkg to compile on all available CPU cores
export MAKEFLAGS="-j$(nproc)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$REPO_DIR/build"
OUTPUT_DIR="$REPO_DIR/x86_64"

# Define packages to build in precise dependency order
# Format: "local:NAME" or "aur:AUR_NAME:TARGET_NAME"
PACKAGES=(
  "local:xlibre-xserver-legacyabi"
  "local:linux-cachyos-lts-v2"
  "aur:xlibre-input-libinput:"
  "aur:xlibre-video-amdgpu:"
  "aur:xlibre-video-ati:"
  "aur:xlibre-video-intel:"
  "aur:xlibre-video-nouveau:"
  "aur:xlibre-video-vesa:"
  "aur:xlibre-video-fbdev:"
  "aur:xlibre-video-vmware:"
  "aur:nvidia-390xx-utils:"
  "aur:lib32-nvidia-390xx-utils:"
  "aur:nvidia-390xx-settings:"
  "aur:dory:"
  "aur:dory-python-git:dory-python"
  "aur:dory-audio-tab-git:dory-audio-tab"
  "aur:dory-compare-git:dory-compare"
  "aur:dory-dropbox-git:dory-dropbox"
  "aur:dory-emblems-git:dory-emblems"
  "aur:dory-fileroller-git:dory-fileroller"
  "aur:dory-image-converter-git:dory-image-converter"
  "aur:dory-media-columns-git:dory-media-columns"
  "aur:dory-pastebin-git:dory-pastebin"
  "aur:cogl:"
  "aur:clutter:"
  "aur:clutter-gtk:"
  "aur:clutter-gst:"
  "aur:dory-preview-git:dory-preview"
  "aur:dory-repairer-git:dory-repairer"
  "aur:dory-seahorse-git:dory-seahorse"
  "aur:dory-share-git:dory-share"
  "aur:dory-terminal-git:dory-terminal"
  "aur:zenity-gtk3:"
  "aur:xdg-desktop-portal-xapp-filepicker:"
  "aur:cinnamon-aliveos:"
  "aur:nerd-dictation-git:nerd-dictation"
  "local:aliveos-settings"
  "local:aliveos-assets"
  "aur:grub-silent-ldfix:"
  "aur:valuate:"
  "aur:markpad:"
  "aur:respite:"
  "aur:graphite-gtk-theme-git:"
  "aur:tela-icon-theme:"
  "aur:httptoolkit:"
  "aur:xconnect:"
)

echo "=== AliveOS Package Repository Builder ==="
mkdir -p "$BUILD_DIR"
mkdir -p "$OUTPUT_DIR"

# Clean previous builds in build directory
rm -rf "$BUILD_DIR"/*

# Build all packages sequentially
for item in "${PACKAGES[@]}"; do
  IFS=':' read -r type pkg_name target_name <<< "$item"
  
  if [ "$type" == "local" ]; then
    echo ""
    echo "----------------------------------------"
    echo "Building local package: $pkg_name"
    echo "----------------------------------------"
    
    cd "$REPO_DIR/packages/$pkg_name"
    
    # Run makepkg
    makepkg --syncdeps --noconfirm --nocheck --clean
    
    echo "Copying built packages to $OUTPUT_DIR..."
    cp *.pkg.tar.zst "$OUTPUT_DIR/"
    
    # Fix epoch versions in copied files
    cd "$OUTPUT_DIR"
    for f in *-1.*-*-x86_64.pkg.tar.zst *-1.*-*-any.pkg.tar.zst; do
      [ -f "$f" ] || continue
      if [[ "$f" =~ ^(.+)-([0-9]+)\.([0-9]+\.[0-9]+\.[0-9]+)-([0-9]+)-(x86_64|any)\.pkg\.tar\.zst$ ]]; then
        pkgname="${BASH_REMATCH[1]}"
        epoch="${BASH_REMATCH[2]}"
        pkgver="${BASH_REMATCH[3]}"
        pkgrel="${BASH_REMATCH[4]}"
        arch="${BASH_REMATCH[5]}"
        newname="${pkgname}-${epoch}:${pkgver}-${pkgrel}-${arch}.pkg.tar.zst"
        if [ "$f" != "$newname" ]; then
          echo "Renaming: $f -> $newname"
          mv "$f" "$newname"
        fi
      fi
    done
    cd "$REPO_DIR/packages/$pkg_name"
    
    # Install compiled package locally to satisfy dependencies for subsequent builds
    echo "Installing compiled package locally..."
    sudo pacman -U --noconfirm --overwrite '*' *.pkg.tar.zst || pacman -U --noconfirm --overwrite '*' *.pkg.tar.zst || true
    
    cd "$REPO_DIR"
  else
    if [ -z "$target_name" ]; then
      target_name="$pkg_name"
    fi

    echo ""
    echo "----------------------------------------"
    echo "Building AUR package: $pkg_name -> $target_name"
    echo "----------------------------------------"

    cd "$BUILD_DIR"

    # Clone AUR package with retry loop (handles transient AUR SSL/network drops)
    max_attempts=5
    attempt=1
    while [ "$attempt" -le "$max_attempts" ]; do
      rm -rf "$pkg_name"
      echo "Cloning AUR package (attempt $attempt/$max_attempts)..."
      if git clone --depth=1 "https://aur.archlinux.org/${pkg_name}.git" "$pkg_name"; then
        break
      fi
      if [ "$attempt" -eq "$max_attempts" ]; then
        echo "ERROR: Failed to clone $pkg_name from AUR after $max_attempts attempts" >&2
        exit 1
      fi
      echo "Clone failed, retrying in $((attempt * 10)) seconds..."
      sleep $((attempt * 10))
      attempt=$((attempt + 1))
    done
    cd "$pkg_name"

    # Rename package if needed
    if [ "$pkg_name" != "$target_name" ]; then
      python3 "$SCRIPT_DIR/clean_pkgbuild.py" PKGBUILD "$pkg_name" "$target_name"
    fi

    # Replace gtk2 with gtk2-compat in dependency arrays for nvidia-settings packages
    if [[ "$pkg_name" == nvidia-*-settings ]]; then
      sed -i '/^depends=/s/\bgtk2\b/gtk2-compat/g; /^makedepends=/s/\bgtk2\b/gtk2-compat/g; /^optdepends=/s/\bgtk2\b/gtk2-compat/g' PKGBUILD
      echo "Replaced gtk2 with gtk2-compat in $pkg_name PKGBUILD dependencies"
    fi

    # Run makepkg
    makepkg --syncdeps --noconfirm --nocheck --clean

    # Copy built packages to output directory
    echo "Copying built packages to $OUTPUT_DIR..."
    cp "${target_name}"-*.pkg.tar.zst "$OUTPUT_DIR/"
    
    # Fix epoch versions in copied files
    cd "$OUTPUT_DIR"
    for f in *-1.*-*-x86_64.pkg.tar.zst *-1.*-*-any.pkg.tar.zst; do
      [ -f "$f" ] || continue
      if [[ "$f" =~ ^(.+)-([0-9]+)\.([0-9]+\.[0-9]+\.[0-9]+)-([0-9]+)-(x86_64|any)\.pkg\.tar\.zst$ ]]; then
        pkgname="${BASH_REMATCH[1]}"
        epoch="${BASH_REMATCH[2]}"
        pkgver="${BASH_REMATCH[3]}"
        pkgrel="${BASH_REMATCH[4]}"
        arch="${BASH_REMATCH[5]}"
        newname="${pkgname}-${epoch}:${pkgver}-${pkgrel}-${arch}.pkg.tar.zst"
        if [ "$f" != "$newname" ]; then
          echo "Renaming: $f -> $newname"
          mv "$f" "$newname"
        fi
      fi
    done
    cd "$BUILD_DIR/$pkg_name"
    
    # Install compiled package locally to satisfy dependencies for subsequent builds
    echo "Installing compiled package locally..."
    sudo pacman -U --noconfirm --overwrite '*' "${target_name}"-*.pkg.tar.zst || pacman -U --noconfirm --overwrite '*' "${target_name}"-*.pkg.tar.zst || true
    
    cd "$REPO_DIR"
  fi
done

echo ""
echo "=== Generating Pacman Repository Database ==="
cd "$OUTPUT_DIR"

# Remove old database files if they exist (repo-add will regenerate them)
rm -f aliveos-repo.db*
rm -f aliveos-repo.files*

# Run repo-add to create database
repo-add aliveos-repo.db.tar.gz *.pkg.tar.zst

# Create symlinks to match standard pacman repos
ln -sf aliveos-repo.db.tar.gz aliveos-repo.db
ln -sf aliveos-repo.files.tar.gz aliveos-repo.files

# Fix epoch versions in filenames: replace dots with colons for repo-add compatibility
# makepkg generates filenames like "pkg-1.25.0.1-4.pkg.tar.zst" but repo-add expects "pkg-1:25.0.1-4.pkg.tar.zst"
echo ""
echo "=== Fixing epoch versions in filenames ==="
cd "$OUTPUT_DIR"
for f in *-1.*-*-x86_64.pkg.tar.zst *-1.*-*-any.pkg.tar.zst; do
  [ -f "$f" ] || continue
  # Check if this is an epoch version (first number after last dash before version has a dot pattern)
  if [[ "$f" =~ ^(.+)-([0-9]+)\.([0-9]+\.[0-9]+\.[0-9]+)-([0-9]+)-(x86_64|any)\.pkg\.tar\.zst$ ]]; then
    pkgname="${BASH_REMATCH[1]}"
    epoch="${BASH_REMATCH[2]}"
    pkgver="${BASH_REMATCH[3]}"
    pkgrel="${BASH_REMATCH[4]}"
    arch="${BASH_REMATCH[5]}"
    newname="${pkgname}-${epoch}:${pkgver}-${pkgrel}-${arch}.pkg.tar.zst"
    if [ "$f" != "$newname" ]; then
      echo "Renaming: $f -> $newname"
      mv "$f" "$newname"
    fi
  fi
done

echo "=== Build Complete ==="
echo "Output files in $OUTPUT_DIR:"
ls -lh
