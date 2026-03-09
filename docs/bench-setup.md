# Bench Setup Guide

Complete walkthrough for bringing up a new HIL bench from scratch.

## Hardware Requirements

| Component | Notes |
|---|---|
| Raspberry Pi 5 | 4GB+ RAM, Pi OS Bookworm 64-bit |
| Atmel-ICE | JTAG/SWD programmer for SAMD51 |
| USB-serial adapter | FTDI or similar, for target UART |
| Target MCU board | SAMD51-based (or other supported family) |
| USB cables | Atmel-ICE → Pi, serial adapter → Pi |
| SWD wires | Atmel-ICE → target SWD header |
| Power supply | 5V/3A+ for Pi, target power as needed |

## 1. Prepare the Pi

Flash Pi OS Bookworm 64-bit to SD card. Boot, connect to network, enable SSH.

```bash
sudo apt update && sudo apt upgrade -y
```

## 2. Clone the repo

```bash
git clone https://github.com/Aharoni-Lab/hil-bench-controller.git
cd hil-bench-controller
```

## 3. Run bootstrap

```bash
sudo ./bootstrap/bootstrap_pi.sh <bench-name> <github-org-token>
```

The bootstrap script runs these steps in order:

1. **configure_hostname.sh** — Sets the Pi hostname to match the bench name
2. **install_system_packages.sh** — Installs libgpiod, openocd, builds edbg
3. **install_udev_rules.sh** — Installs udev rules for stable device names
4. **install_python_env.sh** — Creates venv at `/opt/hil-bench/venv`, installs package
5. **generate_local_config.sh** — Generates `/etc/hil-bench/config.yaml` from template
6. **install_runner.sh** — Registers GitHub Actions runner at org scope

Each subscript is idempotent — safe to re-run after fixing issues.

## 4. Configure hardware paths

Find your devices:

```bash
# List USB devices
lsusb

# Find serial ports
ls -la /dev/serial/by-id/

# Check udev-created symlinks
ls -la /dev/atmel-ice-*
```

Edit `/etc/hil-bench/config.yaml` with the correct paths:

```yaml
targets:
  samd51:
    probe:
      device_path: /dev/atmel-ice-0
    serial:
      device_path: /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_XXXXXXXX-if00-port0
```

## 5. Validate and test

```bash
benchctl config validate
benchctl health
benchctl flash --firmware test.bin --target samd51 --dry-run
```

## 6. Enable health monitoring

```bash
sudo cp systemd/hil-bench-health.service /etc/systemd/system/
sudo cp systemd/hil-bench-health.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hil-bench-health.timer
```

Check status:

```bash
systemctl status hil-bench-health.timer
journalctl -u hil-bench-health.service --since "1 hour ago"
```

## Troubleshooting

### Probe not detected

- Check USB connection: `lsusb | grep 03eb`
- Check udev rules: `udevadm test /dev/bus/usb/...`
- Try: `sudo udevadm control --reload-rules && sudo udevadm trigger`

### Serial port permission denied

- Verify udev rules installed: `ls /etc/udev/rules.d/99-hil-bench.rules`
- Add user to `dialout` group: `sudo usermod -aG dialout $USER`

### Runner not picking up jobs

- Check service: `systemctl status actions.runner.*`
- Check labels match workflow `runs-on`
- Verify token hasn't expired
