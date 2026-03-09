# HIL Bench Controller

Automated Hardware-in-the-Loop (HIL) firmware testing on Raspberry Pi 5 for the Aharoni Lab.

Turns a Raspberry Pi 5 into a self-hosted GitHub Actions runner that can flash MCU firmware, observe serial output, toggle GPIO pins, and report results — enabling automated firmware testing in CI pipelines.

## Features

- **Flash firmware** via Atmel-ICE (edbg) or OpenOCD
- **Serial communication** — listen, send, and pattern-match (`expect`)
- **GPIO control** — set, get, pulse pins (libgpiod/gpiod, Pi 5 compatible)
- **Health monitoring** — probe, serial, GPIO, and runner status checks
- **CI integration** — org-level GitHub Actions runner with example workflows
- **Idempotent bootstrap** — single script to provision a fresh Pi

## Quick Start

### 1. Bootstrap a Pi

```bash
git clone https://github.com/Aharoni-Lab/hil-bench-controller.git
cd hil-bench-controller
sudo ./bootstrap/bootstrap_pi.sh aharoni-samd51-bench-01 <github-org-token>
```

### 2. Edit config

```bash
sudo vim /etc/hil-bench/config.yaml
benchctl config validate
```

### 3. Flash and test

```bash
benchctl flash --firmware build/firmware.bin --target samd51
benchctl serial expect --target samd51 --pattern "BOOT OK" --timeout 10
benchctl gpio get --pin fault --target samd51
benchctl health
```

## CLI Reference

```
benchctl [--config PATH] [--verbose] [--dry-run]
  flash     --firmware PATH --target NAME [--verify] [--power-cycle]
  serial    listen|send|expect  --target NAME [--timeout N]
  gpio      set|get|pulse  --pin NAME|NUM --value high|low
  health    [--json]
  config    show|validate|generate
```

## CI Integration

Add HIL testing to any firmware repo. See [`examples/firmware-ci.yml`](examples/firmware-ci.yml) for a complete 2-job workflow (build on GitHub → test on bench).

```yaml
hil-test:
  runs-on: [self-hosted, linux, ARM64, hil, samd51, bench01]
  steps:
    - uses: actions/download-artifact@v4
      with: { name: firmware }
    - run: benchctl flash --firmware firmware.bin --target samd51 --verify
    - run: benchctl serial expect --target samd51 --pattern "BOOT OK" --timeout 15
```

## Development

```bash
pip install -e ".[dev]"
ruff check src/ tests/
pytest -m "not hardware"
```

## Project Structure

```
src/hilbench/          Python package
  config.py            Pydantic config models + YAML loader
  probe.py             edbg/OpenOCD flash abstraction
  serial_io.py         pyserial wrapper
  gpio.py              gpiod (libgpiod) wrapper
  relay.py             Power relay control (stubbed)
  health.py            Health check logic
  artifacts.py         Firmware artifact resolution
  cli/                 Click CLI commands
bootstrap/             Pi provisioning scripts
configs/               Config templates
systemd/               Health check timer
udev/                  Device permission rules
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
