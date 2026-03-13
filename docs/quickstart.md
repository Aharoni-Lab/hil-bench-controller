# Quick Start

Shortest path from fresh Pi to working HIL bench.

## Prerequisites

- Raspberry Pi 5 running Pi OS Bookworm (64-bit)
- Atmel-ICE connected via USB
- Target MCU wired to Atmel-ICE SWD and UART (via USB-serial adapter)
- GitHub org token with runner registration permissions

## Steps

### 1. Clone and bootstrap

```bash
git clone https://github.com/Aharoni-Lab/hil-bench-controller.git
cd hil-bench-controller
sudo ./bootstrap/bootstrap_pi.sh my-bench-01 YOUR_RUNNER_TOKEN
```

This installs system packages, builds edbg, creates a Python venv, registers a GitHub Actions runner at org scope, and generates `/etc/hil-bench/config.yaml`.

### 2. Edit configuration

```bash
sudo vim /etc/hil-bench/config.yaml
```

Update `device_path` for your probe and serial adapter. Use `ls /dev/serial/by-id/` and `lsusb` to find the correct paths.

```bash
benchctl config validate
```

### 3. Verify the bench

```bash
benchctl health
```

All checks should pass. If probe or serial checks fail, check wiring and device paths.

### 4. Flash firmware manually

```bash
benchctl flash --firmware /path/to/firmware.bin --target samd51
```

### 5. Add CI workflow to your firmware repo

Copy `examples/firmware-ci.yml` to your firmware repo at `.github/workflows/hil-test.yml`. Push, and the bench will automatically pick up the job.

## Next Steps

- [Full bench setup guide](bench-setup.md)
- [Wiring guide](wiring-guide.md)
- [GitHub integration details](github-integration.md)
