# Remote Web TUI Access via Port 46363 (`ttyd`)

This guide explains how to access, secure, and manage the `orangepi-config` Web TUI remotely over local networks or the internet.

---

## 1. How It Works

- **Engine:** [`ttyd`](https://github.com/tsl0922/ttyd) (installed via `pacman -S ttyd`).
- **RAM Footprint:** ~1.0 MB resident memory.
- **Port:** `46363` (configurable).
- **Service:** Systemd unit `orangepi-config-web.service`.
- **Authentication:** HTTP Basic Authentication enabled (`admin:GoToDev2026!!!!`).

---

## 2. Connecting to the Web TUI

### From Your Local Network:
Open any web browser on your phone, tablet, or PC and navigate to:
```
http://192.168.1.125:46363
```

When prompted, enter:
- **Username:** `admin`
- **Password:** `GoToDev2026!!!!`

### From the Internet (Port Forwarding):
1. Log in to your home router.
2. Under **Port Forwarding / NAT Rules**, add:
   - **External Port:** `46363` (TCP)
   - **Internal IP:** `192.168.1.125`
   - **Internal Port:** `46363` (TCP)
3. Navigate to `http://<your-public-ip>:46363` in any browser.

---

## 3. Managing the Service

### Check Service Status:
```bash
sudo systemctl status orangepi-config-web
```

### Restart Service:
```bash
sudo systemctl restart orangepi-config-web
```

### Changing the Port or Password:
Edit the service configuration:
```bash
sudo nano /etc/systemd/system/orangepi-config-web.service
```
Update the `ExecStart` line:
```ini
ExecStart=/usr/bin/ttyd -W -p <NEW_PORT> -c <USER>:<PASSWORD> -t fontSize=15 -t theme={"background":"#000000"} /usr/local/bin/orangepi-config
```
Then reload systemd and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart orangepi-config-web
```
