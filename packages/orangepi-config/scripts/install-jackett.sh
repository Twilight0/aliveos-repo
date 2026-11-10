#!/bin/bash
set -euo pipefail

echo "=== Jackett Installer for Orange Pi Zero (ARM32) ==="
INSTALL_DIR="/opt/Jackett"
SERVICE_FILE="/etc/systemd/system/jackett.service"

echo "[1/4] Ensuring runtime dependencies (icu, curl, tar, gzip, openssl)..."
pacman -S --needed --noconfirm icu curl tar gzip openssl

echo "[2/4] Querying latest Jackett release from GitHub..."
LATEST_TAG=$(curl -sL https://api.github.com/repos/Jackett/Jackett/releases/latest | grep '"tag_name":' | head -n 1 | cut -d '"' -f 4 || true)
if [ -z "${LATEST_TAG:-}" ]; then
    echo "Warning: GitHub API rate limited or unavailable, falling back to release redirect check..."
    LATEST_TAG=$(curl -sI https://github.com/Jackett/Jackett/releases/latest | grep -i "location:" | awk -F/ '{print $NF}' | tr -d '\r\n')
fi

echo "Identified release tag: ${LATEST_TAG}"
TARBALL_URL="https://github.com/Jackett/Jackett/releases/download/${LATEST_TAG}/Jackett.Binaries.LinuxARM32.tar.gz"

echo "[3/4] Downloading and unpacking Jackett into ${INSTALL_DIR}..."
TMP_TARBALL="/var/tmp/Jackett.Binaries.LinuxARM32.tar.gz"
curl -sL "${TARBALL_URL}" -o "${TMP_TARBALL}"

# Stop service if running
if systemctl is-active --quiet jackett.service 2>/dev/null; then
    echo "Stopping active jackett.service..."
    systemctl stop jackett.service
fi

mkdir -p /opt
tar -xzf "${TMP_TARBALL}" -C /opt
rm -f "${TMP_TARBALL}"
chmod +x "${INSTALL_DIR}/jackett"

echo "[4/4] Setting up systemd service jackett.service..."
cat << 'SVC' > "${SERVICE_FILE}"
[Unit]
Description=Jackett Torrent Indexer Proxy Server
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/Jackett/jackett --NoRestart --NoUpdates
Restart=always
RestartSec=10
TimeoutStopSec=20
WorkingDirectory=/opt/Jackett

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable --now jackett.service

echo ""
echo "=== Jackett Installation Complete! ==="
echo "Service status: $(systemctl is-active jackett.service 2>/dev/null || echo 'unknown')"
echo "Web UI accessible at: http://$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}' || echo '<ip>'):9117"
