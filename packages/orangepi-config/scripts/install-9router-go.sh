#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing 9router-go from AliveOS Repository..."

if pacman -Si 9router-go >/dev/null 2>&1; then
  pacman -S --needed --noconfirm 9router-go
else
  ARCH="$(uname -m)"
  case "${ARCH}" in
    armv7l|armv7h) PKG_ARCH="armv7h" ;;
    x86_64)        PKG_ARCH="x86_64" ;;
    *)
      echo "Unsupported architecture: ${ARCH}" >&2
      exit 1
      ;;
  esac

  TMP_DIR="$(mktemp -d /tmp/9router-go-install.XXXXXX)"
  trap 'rm -rf "${TMP_DIR}"' EXIT

  PKG_URL="$(curl -fsSL https://api.github.com/repos/Twilight0/aliveos-repo/releases/tags/latest | \
    python3 -c "import sys, json; data = json.load(sys.stdin); assets = [a['browser_download_url'] for a in data.get('assets', []) if a['name'].startswith('9router-go-') and a['name'].endswith('-${PKG_ARCH}.pkg.tar.zst') and '-debug-' not in a['name']]; print(assets[0] if assets else '')")"

  if [ -z "${PKG_URL}" ]; then
    PKG_URL="https://github.com/Twilight0/aliveos-repo/releases/download/latest/9router-go-1.9.17.exp.5-1-${PKG_ARCH}.pkg.tar.zst"
  fi

  echo "==> Downloading ${PKG_URL}..."
  curl -fSL -o "${TMP_DIR}/9router-go.pkg.tar.zst" "${PKG_URL}"
  pacman -U --noconfirm "${TMP_DIR}/9router-go.pkg.tar.zst"
fi

echo ""
echo "==> 9router-go installed successfully!"
echo "    Data directory: /var/lib/9router"
echo "    Config overrides: /etc/default/9router-go"
echo "    Enable & start service: systemctl enable --now 9router-go"
