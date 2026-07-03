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
  "aur:xlibre-input-libinput:"
  "aur:xlibre-video-amdgpu:"
  "aur:xlibre-video-ati:"
  "aur:xlibre-video-intel:"
  "aur:xlibre-video-nouveau:"
  "aur:xlibre-video-vesa:"
  "aur:xlibre-video-fbdev:"
  "aur:xlibre-video-vmware:"
  "aur:dory-git:dory"
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
  "aur:xdg-desktop-portal-xapp-filepicker-git:xdg-desktop-portal-xapp-filepicker"
  "aur:cinnamon-no-nemo:"
  "aur:nerd-dictation-git:nerd-dictation"
  "local:aliveos-settings"
  "local:aliveos-assets"
  "aur:grub-silent-ldfix:"
  "aur:viewmd:"
  "aur:valuate-git:valuate"
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
    
    # Install compiled package locally to satisfy dependencies for subsequent builds
    echo "Installing compiled package locally..."
    sudo pacman -U --noconfirm *.pkg.tar.zst || pacman -U --noconfirm *.pkg.tar.zst
    
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

    # Run makepkg
    makepkg --syncdeps --noconfirm --nocheck --clean

    # Copy built packages to output directory
    echo "Copying built packages to $OUTPUT_DIR..."
    cp "${target_name}"-*.pkg.tar.zst "$OUTPUT_DIR/"
    
    # Install compiled package locally to satisfy dependencies for subsequent builds
    echo "Installing compiled package locally..."
    sudo pacman -U --noconfirm "${target_name}"-*.pkg.tar.zst || pacman -U --noconfirm "${target_name}"-*.pkg.tar.zst
    
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

echo "=== Build Complete ==="
echo "Output files in $OUTPUT_DIR:"
ls -lh
