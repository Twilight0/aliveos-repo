#!/usr/bin/env bash

# Exit on errors
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$REPO_DIR/build"
OUTPUT_DIR="$REPO_DIR/x86_64"

# Define packages to build (Format: "AUR_NAME:TARGET_NAME")
# If target name is empty, it will not be renamed.
PACKAGES=(
  "xlibre-xserver:"
  "xlibre-input-libinput:"
  "xlibre-video-amdgpu:"
  "xlibre-video-ati:"
  "xlibre-video-intel:"
  "xlibre-video-nouveau:"
  "xlibre-video-vesa:"
  "xlibre-video-fbdev:"
  "xlibre-video-vmware:"
  "dory:"
  "dory-audio-tab-git:dory-audio-tab"
  "dory-compare-git:dory-compare"
  "dory-dropbox-git:dory-dropbox"
  "dory-emblems-git:dory-emblems"
  "dory-fileroller-git:dory-fileroller"
  "dory-image-converter-git:dory-image-converter"
  "dory-media-columns-git:dory-media-columns"
  "dory-pastebin-git:dory-pastebin"
  "dory-preview-git:dory-preview"
  "dory-python-git:dory-python"
  "dory-repairer-git:dory-repairer"
  "dory-seahorse-git:dory-seahorse"
  "dory-share-git:dory-share"
  "dory-terminal-git:dory-terminal"
  "cinnamon-no-nemo:"
  "grub-silent-ldfix:"
  "xdg-desktop-portal-xapp-filepicker-git:xdg-desktop-portal-xapp-filepicker"
  "viewmd:"
  "httptoolkit-bin:"
  "nerd-dictation-git:nerd-dictation"
)

echo "=== AliveOS Package Repository Builder ==="
mkdir -p "$BUILD_DIR"
mkdir -p "$OUTPUT_DIR"

# Clean previous builds in build directory
rm -rf "$BUILD_DIR"/*

# 1. Build AUR Packages
for item in "${PACKAGES[@]}"; do
  IFS=':' read -r aur_name target_name <<< "$item"
  if [ -z "$target_name" ]; then
    target_name="$aur_name"
  fi

  echo ""
  echo "----------------------------------------"
  echo "Building AUR package: $aur_name -> $target_name"
  echo "----------------------------------------"

  cd "$BUILD_DIR"
  
  # Clone AUR package
  git clone --depth=1 "https://aur.archlinux.org/${aur_name}.git" "$aur_name"
  cd "$aur_name"

  # Rename package if needed
  if [ "$aur_name" != "$target_name" ]; then
    python3 "$SCRIPT_DIR/clean_pkgbuild.py" PKGBUILD "$aur_name" "$target_name"
  fi

  # Run makepkg
  makepkg --syncdeps --noconfirm --nocheck --clean

  # Copy built packages to output directory
  echo "Copying built packages to $OUTPUT_DIR..."
  cp *.pkg.tar.zst "$OUTPUT_DIR/"
  
  # Install compiled package locally to satisfy dependencies for subsequent builds
  echo "Installing compiled package locally..."
  sudo pacman -U --noconfirm *.pkg.tar.zst || pacman -U --noconfirm *.pkg.tar.zst
  
  cd "$REPO_DIR"
done

# 2. Build Local Packages
echo ""
echo "=== Building Local Packages ==="
if [ -d "$REPO_DIR/packages" ]; then
  for pkg_dir in "$REPO_DIR"/packages/*; do
    if [ -d "$pkg_dir" ]; then
      pkg_name=$(basename "$pkg_dir")
      echo ""
      echo "----------------------------------------"
      echo "Building local package: $pkg_name"
      echo "----------------------------------------"
      
      cd "$pkg_dir"
      
      # Run makepkg
      makepkg --syncdeps --noconfirm --nocheck --clean
      
      echo "Copying built packages to $OUTPUT_DIR..."
      cp *.pkg.tar.zst "$OUTPUT_DIR/"
      
      # Install compiled package locally to satisfy dependencies for subsequent builds
      echo "Installing compiled package locally..."
      sudo pacman -U --noconfirm *.pkg.tar.zst || pacman -U --noconfirm *.pkg.tar.zst
      
      cd "$REPO_DIR"
    fi
  done
fi

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
