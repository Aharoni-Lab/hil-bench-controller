# Getting Started: Raspberry Pi 5 HIL Bench from Scratch

This guide walks through every step from a brand-new Raspberry Pi 5 to a working
hardware-in-the-loop bench. Follow it in order — each section builds on the last.

---

## 1. Gather hardware

| Item | Notes |
|------|-------|
| Raspberry Pi 5 (4 GB+) | 8 GB recommended if running other services |
| microSD card (32 GB+) | Class A2 recommended for speed |
| USB-C power supply (5V / 5A) | Use the official Pi 5 PSU or a PD supply that negotiates 5V/5A |
| Atmel-ICE programmer | JTAG/SWD programmer for SAMD51 targets |
| USB-serial adapter | FTDI FT232R or similar 3.3V-level adapter |
| Target MCU board | SAMD51-based (or other supported family) |
| SWD cable / jumper wires | For Atmel-ICE → target SWD header |
| Ethernet cable or WiFi | Ethernet is more reliable for CI runners |
| A computer with SD card reader | For flashing the OS image |

Optional:
- Pi 5 active cooler or heatsink case (recommended — Pi 5 runs hot)
- Level shifter if target is not 3.3V logic
- USB hub if ports are scarce

---

## 2. Flash Raspberry Pi OS to SD card

### 2a. Download Raspberry Pi Imager

Install the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your
computer (available for Windows, macOS, and Linux).

### 2b. Configure and flash

1. Insert the microSD card into your computer.
2. Open Raspberry Pi Imager.
3. Click **Choose Device** → select **Raspberry Pi 5**.
4. Click **Choose OS** → select **Raspberry Pi OS (64-bit)** (Bookworm, Desktop or
   Lite — Lite is fine for a headless bench).
5. Click **Choose Storage** → select your SD card.
6. Click **Next**, then click **Edit Settings** when prompted.

### 2c. Customize OS settings (important)

In the **General** tab:
- **Set hostname**: e.g. `hil-bench-01`
- **Set username and password**: e.g. `pi` / pick a strong password
- **Configure wireless LAN**: enter your WiFi SSID and password (skip if using Ethernet)
- **Set locale settings**: your timezone and keyboard layout

In the **Services** tab:
- **Enable SSH**: select **Use password authentication** (or paste a public key for
  key-based auth)

Click **Save**, then **Yes** to flash. Wait for it to finish and verify.

---

## 3. First boot

1. Insert the SD card into the Pi 5.
2. Connect Ethernet (recommended) or rely on the WiFi you configured.
3. Plug in the USB-C power supply.
4. Wait ~60 seconds for the first boot to complete.

### Find the Pi on your network

From your computer:

```bash
# If you set the hostname to hil-bench-01:
ping hil-bench-01.local

# Or scan your network (install nmap if needed):
nmap -sn 192.168.1.0/24 | grep -i raspberry
```

If `ping hostname.local` doesn't work, check your router's DHCP client list for the
Pi's IP address.

### SSH in

```bash
ssh pi@hil-bench-01.local
# Enter the password you set in Pi Imager
```

> **Tip**: If you plan to SSH frequently, copy your public key now:
> ```bash
> ssh-copy-id pi@hil-bench-01.local
> ```

---

## 4. Initial Pi configuration

Once SSH'd in:

```bash
# Update the system
sudo apt update && sudo apt upgrade -y

# Verify you're on 64-bit Bookworm
cat /etc/os-release | grep PRETTY_NAME
uname -m   # should show aarch64
```

### Set a static IP (optional but recommended for CI runners)

Edit the NetworkManager connection (Pi OS Bookworm uses NetworkManager):

```bash
# List connections
nmcli con show

# Set static IP (adjust for your network)
sudo nmcli con mod "Wired connection 1" \
    ipv4.addresses 192.168.1.100/24 \
    ipv4.gateway 192.168.1.1 \
    ipv4.dns "8.8.8.8,8.8.4.4" \
    ipv4.method manual

# Apply
sudo nmcli con up "Wired connection 1"
```

### Reboot

```bash
sudo reboot
```

SSH back in after reboot.

---

## 5. Connect hardware

Plug in hardware **before** running the bootstrap so udev rules can be verified:

1. **Atmel-ICE** → connect to any Pi USB port
2. **USB-serial adapter** → connect to another Pi USB port
3. **SWD wires** → Atmel-ICE SAM port to target MCU (see [wiring guide](wiring-guide.md))
4. **Serial wires** → USB-serial adapter to target UART (see [wiring guide](wiring-guide.md))
5. **Power the target** MCU board

Verify the hardware is visible:

```bash
# Should show Atmel-ICE and FTDI (or your serial adapter)
lsusb

# Check if serial adapter shows up
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

---

## 6. Clone the repo and run bootstrap

```bash
cd ~
git clone https://github.com/Aharoni-Lab/hil-bench-controller.git
cd hil-bench-controller
```

### Run the bootstrap script

Without GitHub Actions runner (you can add it later):

```bash
sudo ./bootstrap/bootstrap_pi.sh hil-bench-01
```

With GitHub Actions runner registration:

```bash
# Generate a runner registration token at:
# https://github.com/organizations/<your-org>/settings/actions/runners/new
sudo ./bootstrap/bootstrap_pi.sh hil-bench-01 YOUR_TOKEN your-github-org
```

The bootstrap script runs these steps in order (each is idempotent):

1. **configure_hostname.sh** — sets Pi hostname to match bench name
2. **install_system_packages.sh** — installs libgpiod, openocd, builds `edbg` from source
3. **install_udev_rules.sh** — creates stable device names (`/dev/atmel-ice-0`, etc.)
4. **install_python_env.sh** — creates venv at `/opt/hil-bench/venv`, installs `benchctl`
5. **generate_local_config.sh** — generates `/etc/hil-bench/config.yaml` from template
6. **install_health_timer.sh** — installs systemd timer for periodic health checks
7. **install_runner.sh** — (if token provided) registers GitHub Actions runner

If any step fails, fix the issue and re-run — the script is safe to re-run.

---

## 7. Configure hardware paths

After bootstrap, udev rules are installed. Unplug and replug the Atmel-ICE and serial
adapter to trigger the rules, then check:

```bash
# Atmel-ICE should appear here
ls -la /dev/atmel-ice-*

# Find your serial adapter's stable path
ls -la /dev/serial/by-id/
```

Edit the generated config:

```bash
sudo nano /etc/hil-bench/config.yaml
```

Update these fields with your actual device paths:

```yaml
targets:
  samd51:
    family: samd51
    probe:
      type: edbg
      device_path: /dev/atmel-ice-0
    serial:
      device_path: /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_XXXXXXXX-if00-port0
      baud_rate: 115200
```

Replace `usb-FTDI_FT232R_USB_UART_XXXXXXXX-if00-port0` with the actual path from
`ls /dev/serial/by-id/`.

---

## 8. Verify the bench

Add the benchctl venv to your path for convenience:

```bash
echo 'export PATH="/opt/hil-bench/venv/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Run checks:

```bash
# Validate config syntax
benchctl config validate

# Run all health checks
benchctl health

# Check individual components
benchctl health --json
```

Expected output for a fully wired bench — all checks pass. If something fails,
see [Troubleshooting](#troubleshooting) below.

---

## 9. Test flash (optional)

If you have a firmware binary ready:

```bash
benchctl flash --firmware /path/to/firmware.bin --target samd51
```

To test serial communication after flashing:

```bash
# Listen for serial output (Ctrl+C to stop)
benchctl serial listen --target samd51

# Wait for a specific pattern
benchctl serial expect --target samd51 --pattern "BOOT OK" --timeout 10
```

---

## 10. Set up CI integration (optional)

If you registered a GitHub Actions runner during bootstrap, verify it's running:

```bash
systemctl status actions.runner.*
```

Then add a workflow to your firmware repo. Copy the example:

```bash
cat ~/hil-bench-controller/examples/firmware-ci.yml
```

See [GitHub integration guide](github-integration.md) for full details.

---

## Troubleshooting

### Cannot find Pi on network

- Verify the SD card is properly seated
- Try connecting a monitor and keyboard to see boot output
- If using WiFi, double-check SSID/password in Pi Imager settings
- Try `arp -a` or check your router's DHCP leases

### `edbg` build fails

```bash
# Re-run just the system packages step
sudo ~/hil-bench-controller/bootstrap/install_system_packages.sh
```

Requires `build-essential` and `libudev-dev` (installed by the script).

### Probe not detected

- Check USB connection: `lsusb | grep -i atmel`
- Reload udev rules: `sudo udevadm control --reload-rules && sudo udevadm trigger`
- Check udev rule is installed: `ls /etc/udev/rules.d/99-hil-bench.rules`

### Serial permission denied

```bash
# Add your user to the dialout group
sudo usermod -aG dialout $USER
# Log out and back in for it to take effect
```

### Runner not picking up jobs

- Check service status: `systemctl status actions.runner.*`
- Verify labels in your workflow's `runs-on:` match the runner labels
- Check the runner token hasn't expired (re-register if needed)

### Health checks fail

Run with JSON output for details:

```bash
benchctl health --json
```

Fix each failing check individually. Common issues:
- **probe**: USB not connected or udev rule not triggered
- **serial**: wrong `device_path` in config, or adapter not plugged in
- **gpio**: wrong chip (Pi 5 uses `gpiochip4`, not `gpiochip0`)

---

## What's next

- [Wiring guide](wiring-guide.md) — detailed pin connections
- [GitHub integration](github-integration.md) — CI workflow setup
- [Dashboard setup](dashboard-setup.md) — optional remote monitoring via Supabase
- [Publisher architecture](publisher-architecture.md) — how the status publisher works
