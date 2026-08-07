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
# Format: "local:NAME" or "aur:AUR_NAME:TARGET_NAME" or "upstream:REPO_URL:TARGET_NAME:TAG"
PACKAGES=(
  "local:xlibre-xserver-legacyabi"
  "upstream:https://github.com/CachyOS/linux-cachyos.git:linux-cachyos-lts:master"
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
  "upstream:https://github.com/Twilight0/dory.git:dory:"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-python:dory-python"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-audio-tab:dory-audio-tab"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-compare:dory-compare"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-dropbox:dory-dropbox"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-emblems:dory-emblems"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-fileroller:dory-fileroller"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-image-converter:dory-image-converter"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-media-columns:dory-media-columns"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-pastebin:dory-pastebin"
  "aur:cogl:"
  "aur:clutter:"
  "aur:clutter-gtk:"
  "aur:clutter-gst:"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-preview:dory-preview"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-repairer:dory-repairer"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-seahorse:dory-seahorse"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-share:dory-share"
  "upstream:https://github.com/Twilight0/dory-extensions.git:dory-terminal:dory-terminal"
  "aur:zenity-gtk3:"
  "aur:xdg-desktop-portal-xapp-filepicker:"
  "upstream:https://github.com/Twilight0/cinnamon-aliveos.git:cinnamon-aliveos:"
  "aur:nerd-dictation-git:nerd-dictation"
  "local:aliveos-settings"
  "local:aliveos-assets"
  "aur:grub-silent-ldfix:"
  "aur:valuate:"
  "aur:markpad:"
  "upstream:https://github.com/Twilight0/respite.git:respite:"
  "aur:graphite-gtk-theme-git:"
  "aur:tela-icon-theme:"
  "upstream:https://github.com/httptoolkit/httptoolkit-desktop.git:httptoolkit:"
  "upstream:https://github.com/Twilight0/xconnect.git:xconnect:"
)

echo "=== AliveOS Package Repository Builder ==="
mkdir -p "$BUILD_DIR"
mkdir -p "$OUTPUT_DIR"

# Clean previous builds in build directory
rm -rf "$BUILD_DIR"/*

# Security scan function: check PKGBUILD for malicious patterns
scan_pkgbuild() {
  local pkgbuild="$1"
  local pkg_name="$2"
  local issues=0

  if [ ! -f "$pkgbuild" ]; then
    echo "  WARNING: PKGBUILD not found at $pkgbuild"
    return 1
  fi

  echo "  Scanning PKGBUILD for security issues..."

  # Check for known malicious npm packages (Atomic Arch attack)
  if grep -qi "atomic-lockfile\|js-digest" "$pkgbuild"; then
    echo "  CRITICAL: Known malicious npm package detected (atomic-lockfile/js-digest)"
    issues=$((issues + 1))
  fi

  # Check for npm install in non-JavaScript packages
  if grep -qi "npm install\|npm i " "$pkgbuild"; then
    # Allow if package name suggests it's a JS/Node project
    if ! echo "$pkg_name" | grep -qi "node\|npm\|js\|javascript"; then
      echo "  WARNING: npm install found in non-JavaScript package"
      issues=$((issues + 1))
    fi
  fi

  # Check for suspicious download patterns
  if grep -qiE "curl.*\|.*sh|wget.*\|.*sh|bash.*-c.*curl\|bash.*-c.*wget" "$pkgbuild"; then
    echo "  WARNING: Suspicious curl/wget pipe to shell detected"
    issues=$((issues + 1))
  fi

  # Check for base64 decode (common obfuscation)
  if grep -qi "base64.*-d\|base64.*--decode" "$pkgbuild"; then
    echo "  WARNING: base64 decode detected (possible obfuscation)"
    issues=$((issues + 1))
  fi

  # Check for encoded executables
  if grep -qiE "echo.*\\\\x[0-9a-f]{2}.*>.*\.sh\|printf.*\\\\x[0-9a-f]{2}" "$pkgbuild"; then
    echo "  WARNING: Encoded executable content detected"
    issues=$((issues + 1))
  fi

  # Check for /dev/tcp (reverse shell indicator)
  if grep -qi "/dev/tcp/" "$pkgbuild"; then
    echo "  CRITICAL: /dev/tcp detected (possible reverse shell)"
    issues=$((issues + 1))
  fi

  # Check for recent maintainer email changes (heuristic)
  if grep -qiE " Maintainer.*<.*@.*>" "$pkgbuild"; then
    echo "  INFO: Maintainer field found — verify it matches AUR records"
  fi

  # Check for post_install/post_upgrade hooks with suspicious content
  if grep -qiE "post_install|post_upgrade" "$pkgbuild"; then
    local hooks
    hooks=$(grep -A5 -E "post_install|post_upgrade" "$pkgbuild" | grep -iE "curl|wget|exec|eval|nc |ncat |python.*-c|perl.*-e")
    if [ -n "$hooks" ]; then
      echo "  WARNING: Suspicious content in post_install/post_upgrade hook"
      issues=$((issues + 1))
    fi
  fi

  # Check for systemd service installation (potential persistence)
  if grep -qiE "\.service.*install|install.*\.service" "$pkgbuild"; then
    echo "  INFO: Systemd service installation detected — verify legitimacy"
  fi

  # Check for polkit rules (privilege escalation)
  if grep -qiE "polkit.*\.rules|pkla.*\.pkla" "$pkgbuild"; then
    echo "  INFO: Polkit rules detected — verify no privilege escalation"
  fi

  if [ "$issues" -gt 0 ]; then
    echo "  SCAN RESULT: $issues issue(s) found in $pkg_name PKGBUILD"
    return 1
  else
    echo "  SCAN RESULT: No issues detected"
    return 0
  fi
}

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
  elif [ "$type" == "upstream" ]; then
    # upstream:REPO_URL:TARGET_NAME:TAG_OR_SUBDIR
    IFS=':' read -r _ repo_url pkg_name target_name tag <<< "$item"
    
    if [ -z "$target_name" ]; then
      target_name="$pkg_name"
    fi

    echo ""
    echo "----------------------------------------"
    echo "Building upstream package: $pkg_name -> $target_name"
    echo "----------------------------------------"

    cd "$BUILD_DIR"

    # Clone upstream repo with retry loop
    max_attempts=5
    attempt=1
    while [ "$attempt" -le "$max_attempts" ]; do
      rm -rf "$pkg_name"
      echo "Cloning upstream repo (attempt $attempt/$max_attempts)..."
      if git clone --depth=1 "$repo_url" "$pkg_name"; then
        break
      fi
      if [ "$attempt" -eq "$max_attempts" ]; then
        echo "ERROR: Failed to clone $repo_url after $max_attempts attempts" >&2
        exit 1
      fi
      echo "Clone failed, retrying in $((attempt * 10)) seconds..."
      sleep $((attempt * 10))
      attempt=$((attempt + 1))
    done
    cd "$pkg_name"

    # If tag/subdir is provided, checkout tag or cd into subdirectory
    if [ -n "$tag" ]; then
      if [ -d "$tag" ]; then
        # It's a subdirectory (e.g., linux-cachyos-lts)
        cd "$tag"
      else
        # It's a git tag
        git fetch --tags
        git checkout "$tag"
      fi
    fi

    # Security scan before building
    if ! scan_pkgbuild "PKGBUILD" "$pkg_name"; then
      echo ""
      echo "SECURITY WARNING: Issues detected in $pkg_name"
      echo "Skipping this package."
      cd "$REPO_DIR"
      continue
    fi

    # Run makepkg
    makepkg --syncdeps --noconfirm --nocheck --clean

    # Copy built packages to output directory
    echo "Copying built packages to $OUTPUT_DIR..."
    cp "${target_name}"-*.pkg.tar.zst "$OUTPUT_DIR/"
    
    # Install compiled package locally to satisfy dependencies for subsequent builds
    echo "Installing compiled package locally..."
    sudo pacman -U --noconfirm --overwrite '*' "${target_name}"-*.pkg.tar.zst || pacman -U --noconfirm --overwrite '*' "${target_name}"-*.pkg.tar.zst || true
    
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

    # Security scan before building
    if ! scan_pkgbuild "PKGBUILD" "$pkg_name"; then
      echo ""
      echo "SECURITY WARNING: Issues detected in $pkg_name"
      echo "Review the PKGBUILD manually before building:"
      echo "  cat $BUILD_DIR/$pkg_name/PKGBUILD"
      echo ""
      echo "Skipping this package. Fix issues and re-run the build."
      cd "$REPO_DIR"
      continue
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
