# RGB LED Status Display

The HIL bench controller supports a WS2812B (NeoPixel) addressable LED strip as a visual status indicator. Operators can see bench state at a glance — idle, flashing firmware, running tests, or in an error state.

## Architecture

```
benchctl led set-scene ...  ──┐
Publisher hooks (flash/health)──┼── LedClient ── Unix socket ── LED Daemon ── rpi_ws281x
GitHub Actions steps          ──┘                /run/hil-bench/led.sock
```

- **Daemon** (`hil-bench-led.service`) owns the LED hardware exclusively, runs a 30 FPS animation loop, and listens on a Unix domain socket for commands.
- **Clients** send JSON commands over the socket. Any process on the Pi can trigger scene changes.
- **Scenes** are self-contained animation classes that produce frames. All animations are time-based (not frame-count-based) so they look consistent at any FPS.

## Quick Start

### 1. Enable in config

Add to `/etc/hil-bench/config.yaml`:

```yaml
led:
  enabled: true
  led_count: 16        # number of LEDs on your strip
  gpio_pin: 18         # GPIO pin (PWM0 — default for NeoPixels)
  brightness: 128      # 0-255
  fps: 30              # animation frame rate
  socket_path: /run/hil-bench/led.sock
```

### 2. Install the hardware dependency

```bash
sudo /opt/hil-bench/venv/bin/pip install "rpi_ws281x>=5.0"
```

Or during bootstrap, this is handled by `install_led_service.sh`.

### 3. Start the daemon

```bash
# Via systemd (production)
sudo systemctl start hil-bench-led
sudo systemctl enable hil-bench-led

# Or directly (for testing)
benchctl led daemon          # real hardware
benchctl led daemon --stub   # no hardware, in-memory strip
```

### 4. Control the LEDs

```bash
# Set a scene
benchctl led set-scene idle
benchctl led set-scene rainbow --speed 2.0
benchctl led set-scene solid --color 255,0,0 --brightness 200
benchctl led set-scene progress --percent 75 --color 0,255,0

# Turn off
benchctl led off

# Check status
benchctl led status
benchctl led list-scenes
```

## Built-in Scenes

| Scene | Description | Parameters |
|-------|-------------|------------|
| `idle` | Slow sine-wave breathing, dim↔bright | `color` (default: blue), `speed` |
| `flashing` | Knight-rider sweep back and forth | `color` (default: orange), `speed` |
| `testing` | Chase pattern, segments moving along strip | `color` (default: cyan), `speed` |
| `error` | Red pulsing/flashing alert | `color` (default: red), `speed` |
| `success` | Green burst, auto-reverts to idle | `color`, `duration_ms`, `revert_to` |
| `booting` | Sequential fill from one end | `color` (default: blue), `speed` |
| `off` | All pixels off | — |
| `solid` | Static single color | `color`, `brightness` |
| `rainbow` | HSV rainbow cycling across strip | `speed` |
| `progress` | LED bar graph proportional to percent | `color`, `bg_color`, `percent` |

### Parameters

- **`color`**: RGB tuple as `R,G,B` on CLI or `[R, G, B]` in JSON/Python (e.g., `255,0,0` for red)
- **`speed`**: Animation speed multiplier (default varies per scene)
- **`brightness`**: Strip brightness 0-255
- **`percent`**: For `progress` scene, 0-100
- **`duration_ms`**: For `success` scene, how long before auto-reverting
- **`revert_to`**: For `success` scene, which scene to switch to after duration (default: `idle`)

## Automatic Scene Changes

The publisher hooks automatically trigger LED scenes during bench operations:

| Event | Scene |
|-------|-------|
| Flash starts | `flashing` |
| Flash succeeds | `success` (auto-reverts to `idle`) |
| Flash fails | `error` |
| Health check passes | `idle` |
| Health check fails | `error` |
| Daemon starts | `booting` → `idle` (after 2s) |

These are **best-effort** — if the LED daemon isn't running, hooks silently continue without error.

## Using the Python Client

From any Python code on the Pi:

```python
from hilbench.led import LedClient

client = LedClient("/run/hil-bench/led.sock")

# Check if daemon is running
if client.is_daemon_running():
    # Set a scene
    resp = client.set_scene("rainbow", {"speed": 2.0})
    print(resp.ok, resp.current_scene)

    # Get status
    status = client.status()
    print(f"Scene: {status.current_scene}, LEDs: {status.led_count}")

    # List available scenes
    scenes = client.list_scenes()

    # Turn off
    client.off()
```

## Using from GitHub Actions Workflows

In your workflow steps, use `benchctl` to signal bench state:

```yaml
steps:
  - name: Signal test start
    run: benchctl led set-scene testing --color 0,200,255

  - name: Run tests
    run: pytest tests/ -v

  - name: Signal result
    if: always()
    run: |
      if [ "${{ job.status }}" = "success" ]; then
        benchctl led set-scene success
      else
        benchctl led set-scene error
      fi
```

## Socket Protocol

The daemon listens on a Unix domain socket. Commands are newline-delimited JSON:

```json
// Set scene
→ {"command": "set_scene", "scene": "idle", "params": {"color": [0, 255, 0], "speed": 0.5}}
← {"ok": true, "current_scene": "idle"}

// Get status
→ {"command": "status"}
← {"running": true, "current_scene": "idle", "led_count": 16, "uptime_s": 42.5}

// List scenes
→ {"command": "list_scenes"}
← {"ok": true, "scenes": ["booting", "error", "flashing", ...]}
```

Any language can communicate with the daemon — just open a Unix socket, send JSON, read the response.

## Adding a Custom Scene

### 1. Create the scene class

Add your scene to `src/hilbench/led/_scenes.py`:

```python
@register_scene
class MyCustomScene:
    """Description of your animation."""

    @property
    def name(self) -> str:
        return "my_custom"  # This is the name used in CLI and IPC

    def setup(self, strip: LedStrip, params: dict[str, Any]) -> None:
        """Called once when the scene is activated. Parse params here."""
        self._color = _parse_color(params, (255, 255, 255))  # default white
        self._speed = float(params.get("speed", 1.0))

    def tick(self, strip: LedStrip, elapsed_ms: float) -> None:
        """Called every frame. elapsed_ms is time since scene started.

        IMPORTANT: Use elapsed_ms for timing, not frame counts.
        Use strip.num_pixels to adapt to any LED count.
        """
        n = strip.num_pixels
        t = elapsed_ms / 1000.0  # convert to seconds

        for i in range(n):
            # Your animation logic here
            # Use strip.set_pixel(i, r, g, b) for each LED
            # Or strip.set_all(r, g, b) for uniform color
            pass

    def teardown(self, strip: LedStrip) -> None:
        """Called when switching away from this scene. Optional cleanup."""
        pass
```

### 2. Key rules for scenes

- **Use `@register_scene` decorator** — this automatically registers the scene by name.
- **Time-based animations** — use `elapsed_ms` for all timing. Never count frames.
- **Adapt to strip length** — use `strip.num_pixels`, never hardcode LED count.
- **Use `_parse_color()`** — helper that handles `[R,G,B]` lists, `{"r":R,"g":G,"b":B}` dicts, and defaults.
- **Use `_clamp()`** — helper to keep values in 0-255 range.
- **Keep `tick()` fast** — it runs at 30 FPS. Avoid I/O or heavy computation.

### 3. Auto-reverting scenes

If your scene should auto-revert (like `success`), add these properties:

```python
@property
def should_revert(self) -> bool:
    return self._done  # True when it's time to switch

@property
def revert_scene(self) -> str:
    return self._revert_to  # Scene name to switch to
```

The daemon checks for `should_revert` on `SuccessScene` instances each frame. To support this on a custom scene, the daemon's animation loop would need to be updated to check your scene type too — or you can subclass `SuccessScene`.

### 4. Test your scene

Add tests in `tests/test_led_scenes.py` using `StubStrip`:

```python
class TestMyCustomScene:
    def test_basic(self) -> None:
        strip = StubStrip(8)
        scene = MyCustomScene()
        scene.setup(strip, {})

        # Tick at t=0
        scene.tick(strip, 0.0)
        # Assert something about strip.pixels
        assert any(p != (0, 0, 0) for p in strip.pixels)

        # Tick at t=500ms
        scene.tick(strip, 500.0)
        # Assert animation progressed

        scene.teardown(strip)
```

### 5. Verify

```bash
# Check it appears in the list
benchctl led list-scenes

# Run the tests
pytest tests/test_led_scenes.py -v

# Lint
ruff check src/hilbench/led/_scenes.py
ruff format src/hilbench/led/_scenes.py
```

## Hardware Wiring

Connect the WS2812B strip to the Raspberry Pi:

| Strip Wire | Pi Pin | Notes |
|-----------|--------|-------|
| 5V (red) | Pin 2 or 4 (5V) | Or external 5V supply for long strips |
| GND (white/black) | Pin 6 (GND) | Common ground with Pi |
| DIN (green) | Pin 12 (GPIO 18) | PWM0 — default `gpio_pin` |

For strips longer than ~30 LEDs, use an external 5V power supply (the Pi's 5V rail can only provide ~1A). Always connect the ground of the external supply to the Pi's ground.

## Troubleshooting

**Daemon won't start**: Check `journalctl -u hil-bench-led` for errors. Common issues:
- `rpi_ws281x` not installed: `pip install rpi_ws281x`
- Not running as root: the daemon needs root for GPIO access
- Socket directory doesn't exist: `RuntimeDirectory=hil-bench` in the systemd unit creates it

**LEDs not lighting up**:
- Check wiring, especially GND connection
- Try `benchctl led daemon --stub` to verify the daemon runs without hardware
- Check brightness isn't 0 in config

**Health check shows `led_daemon: not reachable`**:
- Is the daemon running? `systemctl status hil-bench-led`
- Is `led.enabled` set to `true` in config? (When `false`, health check auto-passes)

**Permission denied on socket**:
- The daemon runs as root and creates the socket. Clients need to be able to connect — this works by default since the socket is in `/run/hil-bench/` which is created by systemd's `RuntimeDirectory`.

## File Reference

| File | Purpose |
|------|---------|
| `src/hilbench/led/__init__.py` | Package init, re-exports |
| `src/hilbench/led/_models.py` | Pydantic IPC models |
| `src/hilbench/led/_strip.py` | LedStrip Protocol + Ws281xStrip + StubStrip |
| `src/hilbench/led/_scenes.py` | Scene Protocol, registry, built-in scenes |
| `src/hilbench/led/_daemon.py` | Animation loop + Unix socket server |
| `src/hilbench/led/_client.py` | Client library for IPC |
| `src/hilbench/cli/led_cmd.py` | CLI commands |
| `systemd/hil-bench-led.service` | Systemd unit file |
| `bootstrap/install_led_service.sh` | Installation script |
