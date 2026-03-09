# Wiring Guide

Physical connections between the Raspberry Pi 5, Atmel-ICE, and target MCU.

## Overview

```
┌──────────┐  USB   ┌───────────┐  SWD   ┌────────────┐
│  Pi 5    │───────▶│ Atmel-ICE │───────▶│ Target MCU │
│          │        └───────────┘        │  (SAMD51)  │
│          │  USB   ┌───────────┐  UART  │            │
│          │───────▶│ USB-Serial│───────▶│            │
│          │        └───────────┘        │            │
│  GPIO    │─────────────────────────────│ Reset/Rdy  │
└──────────┘                             └────────────┘
```

## Atmel-ICE SWD Connection

Connect the Atmel-ICE SAM port to the target's SWD header:

| Atmel-ICE Pin | Signal | Target Pin |
|---|---|---|
| 1 | VTref | VCC (3.3V) |
| 2 | SWDIO | SWDIO |
| 3 | GND | GND |
| 4 | SWCLK | SWCLK |
| 10 | nRESET | RESET (optional) |

The Atmel-ICE connects to the Pi via USB. After installing udev rules, it appears as `/dev/atmel-ice-0`.

## Serial / UART Connection

Connect a USB-serial adapter between the Pi and the target's UART:

| USB-Serial | Target |
|---|---|
| TX | RX |
| RX | TX |
| GND | GND |

Do **not** connect VCC between the adapter and target unless the target needs power from it.

The adapter appears at `/dev/serial/by-id/usb-FTDI_...`. Use `by-id` paths in config for stability.

## GPIO Connections (Optional)

Direct GPIO wires between Pi and target for reset, ready, and fault signals:

| Pi GPIO | Config Name | Function | Direction |
|---|---|---|---|
| GPIO 17 | `reset` | Hardware reset of target | Pi → Target |
| GPIO 27 | `ready` | Target signals ready | Target → Pi |
| GPIO 22 | `fault` | Target signals fault | Target → Pi |

Use the Pi 5's main GPIO chip (`/dev/gpiochip4`). Logic levels must match (3.3V).

### Level shifting

If the target runs at a different voltage, use a level shifter between Pi GPIO and target signals.

## Power Relay (Future)

When relay hardware is standardized:

| Pi GPIO | Config Name | Function |
|---|---|---|
| GPIO 4 | `relay_pin` | Controls relay for target power |

The relay module is currently stubbed in software. Update `power.type` to `relay` in config when hardware is ready.
