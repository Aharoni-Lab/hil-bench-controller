# ESP32 Targets (esptool probe)

How to put an ESP32-C6 (or other ESP32-family chip with native USB) on the bench.
Nothing in this document has been run on hardware yet; every hardware behavior
below is marked UNTESTED until someone checks it on a bench.

## How the `esptool` probe works

Probe type `esptool` flashes over the chip's built-in USB Serial/JTAG controller
(USB VID `303a`, PID `1001`, CDC-ACM). There is no USB-UART chip and no debug probe.
The same port is used for both flashing and the firmware console.

`benchctl flash` runs (esptool v5 spelling):

```
esptool --chip esp32c6 --port <device_path> --baud 460800 \
        --before usb-reset --after hard-reset write-flash 0x0 <firmware>
```

- `--before usb-reset` makes esptool reset the chip into the ROM download mode over the
  USB port itself, so no BOOT/EN wiring is needed for flashing.
- `--after hard-reset` runs the new firmware when done.
- `write-flash` verifies the written data (MD5) by default in esptool v5 and has no
  `--verify` flag, so `--verify/--no-verify` on `benchctl flash` is accepted but does nothing
  for this probe.
- `flash_offset` defaults to `0x0`: the CI artifact is a merged image (bootloader +
  partition table + app) that is written at offset 0 on the C6.
- esptool must be installed in the benchctl environment: `pip install -e ".[esp]"`
  (the bootstrap scripts do this). Requires `esptool>=5`.

Sources: esptool docs
(<https://docs.espressif.com/projects/esptool/en/latest/esp32c6/esptool/basic-commands.html>)
and `esptool --help` of v5.5.0 for the option spellings and the verification text.

`benchctl health` works with this probe: the probe check only verifies that the port
exists. It never resets the chip.

## Port re-enumeration

After `--after hard-reset` the USB device disappears and comes back. The `/dev/ttyACMn`
node (and the `/dev/serial/by-id/...` symlink) is absent for a moment.

- `benchctl flash` waits for the serial `device_path` to reappear before it returns
  (`--wait-port SECONDS`, default 10) and fails if it does not.
- `benchctl serial listen|send|expect` retry the open for `--wait-port SECONDS`
  (default 5), so a workflow step right after a flash does not race the re-enumeration.
- `device_path` may contain a glob (`*`); the first sorted match is used. Use the
  `/dev/serial/by-id/` form so the path survives re-enumeration (`ttyACMn` can change).

## Wiring to the Pi

The Pi GPIO is 3.3 V, the same as the ESP32-C6, so no level shifting is needed.

| Config name | Direction (from the Pi) | DUT net | Notes |
|---|---|---|---|
| `hv_dis` | input | HV_DIS | HIGH means the APD high-voltage supply is off |
| `reset` | output | EN | pull EN low to reset |
| `boot` | output | BOOT / IO9 | low at reset selects download mode |
| `fault` | input | fault output | board specific |

EN and BOOT have pull-ups to 3.3 V on the DUT. Do not drive them push-pull from a Pi pin
(a hard high would fight the board and a hard low is only safe through a limit). Use an
open-drain style drive: an N-channel MOSFET or NPN transistor from the net to GND, gate or
base driven by the Pi pin (with a series resistor and a pulldown on the gate so the line is
released while the Pi boots). The Pi output high then means "pull the net low".
Match the logic polarity in your own scripts. UNTESTED on hardware.

Since `usb-reset` handles download mode, `reset` and `boot` are only needed for power-on
tests, recovering a hung chip, or forcing download mode when USB is not responding.

## Config

See the commented `esp32c6_receiver` target in `configs/config.template.yaml` and
`configs/bench-config.example.yaml`.

## udev

`udev/99-hil-bench.rules` adds a rule for `303a:1001` on the tty subsystem (mode 0666,
symlink `esp32-usbjtag-%n`, tag `hil-bench`) and a plain usb rule. The `by-id` symlinks
come from the systemd/udev default rules and include the chip MAC address.

## CI

See the ESP-IDF build job pattern in [github-integration.md](github-integration.md).

## Not confirmed

- Everything above on real hardware (usb-reset into download mode, re-enumeration timing,
  the 10 s and 5 s default waits).
- Behavior of `--before usb-reset` when the firmware under test disables USB Serial/JTAG
  or reconfigures the USB pins. The chip may then need `reset`/`boot` GPIO drive.
