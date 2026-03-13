"""LED animation daemon with Unix socket IPC."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import selectors
import signal
import socket
import time
from typing import Any

from hilbench.led._models import SceneRequest, SceneResponse
from hilbench.led._scenes import Scene, SuccessScene, get_scene, list_scenes
from hilbench.led._strip import LedStrip, StubStrip, Ws281xStrip

logger = logging.getLogger(__name__)


class LedDaemon:
    """Single-threaded LED animation daemon with Unix socket IPC."""

    def __init__(
        self,
        led_count: int = 16,
        gpio_pin: int = 18,
        brightness: int = 128,
        fps: int = 30,
        socket_path: str = "/run/hil-bench/led.sock",
        use_stub: bool = False,
    ) -> None:
        self._fps = fps
        self._frame_interval = 1.0 / fps
        self._socket_path = socket_path
        self._shutdown = False
        self._start_time = 0.0
        self._scene_start_time = 0.0

        if use_stub:
            self._strip: LedStrip = StubStrip(led_count)
        else:
            self._strip = Ws281xStrip(led_count, gpio_pin, brightness)

        self._scene: Scene | None = None
        self._sel = selectors.DefaultSelector()
        self._server_sock: socket.socket | None = None

    def _setup_socket(self) -> None:
        """Create the Unix domain socket and start listening."""
        sock_dir = os.path.dirname(self._socket_path)
        if sock_dir:
            os.makedirs(sock_dir, exist_ok=True)

        if os.path.exists(self._socket_path):
            os.unlink(self._socket_path)

        self._server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server_sock.setblocking(False)
        self._server_sock.bind(self._socket_path)
        self._server_sock.listen(5)
        self._sel.register(self._server_sock, selectors.EVENT_READ, self._accept_client)
        logger.info("Listening on %s", self._socket_path)

    def _accept_client(self, sock: socket.socket) -> None:
        """Accept a new client connection."""
        conn, _ = sock.accept()
        conn.setblocking(False)
        self._sel.register(conn, selectors.EVENT_READ, self._handle_client)

    def _handle_client(self, conn: socket.socket) -> None:
        """Read a command from a client and send a response."""
        try:
            data = conn.recv(4096)
            if not data:
                self._sel.unregister(conn)
                conn.close()
                return

            for line in data.decode().strip().split("\n"):
                if not line:
                    continue
                response = self._process_command(line)
                conn.sendall((response + "\n").encode())
        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception:
            logger.warning("Error handling client", exc_info=True)
        finally:
            with contextlib.suppress(KeyError, ValueError):
                self._sel.unregister(conn)
            conn.close()

    def _process_command(self, raw: str) -> str:
        """Process a JSON command and return a JSON response."""
        try:
            req = SceneRequest.model_validate_json(raw)
        except Exception as exc:
            resp = SceneResponse(ok=False, error=f"invalid request: {exc}")
            return resp.model_dump_json()

        if req.command == "set_scene":
            return self._cmd_set_scene(req.scene, req.params)
        if req.command == "status":
            return self._cmd_status()
        if req.command == "list_scenes":
            return json.dumps({"ok": True, "scenes": list_scenes()})

        resp = SceneResponse(ok=False, error=f"unknown command: {req.command!r}")
        return resp.model_dump_json()

    def _cmd_set_scene(self, scene_name: str, params: dict[str, Any]) -> str:
        """Switch to a new scene."""
        try:
            self._set_scene(scene_name, params)
        except Exception as exc:
            resp = SceneResponse(ok=False, error=str(exc))
            return resp.model_dump_json()

        resp = SceneResponse(ok=True, current_scene=scene_name)
        return resp.model_dump_json()

    def _cmd_status(self) -> str:
        """Return daemon status."""
        from hilbench.led._models import DaemonStatus

        status = DaemonStatus(
            running=True,
            current_scene=self._scene.name if self._scene else "",
            led_count=self._strip.num_pixels,
            uptime_s=time.monotonic() - self._start_time,
        )
        return status.model_dump_json()

    def _set_scene(self, name: str, params: dict[str, Any] | None = None) -> None:
        """Internal helper to switch scenes."""
        scene = get_scene(name)
        if self._scene is not None:
            self._scene.teardown(self._strip)
        self._scene = scene
        self._scene_start_time = time.monotonic()
        self._scene.setup(self._strip, params or {})

    def run(self) -> None:
        """Main animation loop."""
        self._start_time = time.monotonic()

        def _handle_signal(signum: int, frame: Any) -> None:
            logger.info("Received signal %s, shutting down LED daemon", signum)
            self._shutdown = True

        import threading

        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGTERM, _handle_signal)
            signal.signal(signal.SIGINT, _handle_signal)

        self._setup_socket()
        self._set_scene("booting")
        logger.info("LED daemon started (fps=%d, pixels=%d)", self._fps, self._strip.num_pixels)

        # Transition to idle after boot animation
        boot_end = self._start_time + 2.0

        while not self._shutdown:
            frame_start = time.monotonic()

            # Check for boot→idle transition
            if (
                self._scene is not None
                and self._scene.name == "booting"
                and frame_start >= boot_end
            ):
                self._set_scene("idle")

            # Poll for socket events (non-blocking)
            events = self._sel.select(timeout=0)
            for key, _ in events:
                callback = key.data
                callback(key.fileobj)

            # Tick the current scene
            if self._scene is not None:
                elapsed_ms = (frame_start - self._scene_start_time) * 1000.0
                self._scene.tick(self._strip, elapsed_ms)

                # Handle auto-revert for SuccessScene
                if isinstance(self._scene, SuccessScene) and self._scene.should_revert:
                    self._set_scene(self._scene.revert_scene)

            self._strip.show()

            # Sleep for the remainder of the frame
            elapsed = time.monotonic() - frame_start
            sleep_time = self._frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        self._shutdown_cleanup()

    def _shutdown_cleanup(self) -> None:
        """Clean up on shutdown."""
        logger.info("Shutting down LED daemon")
        if self._scene is not None:
            self._scene.teardown(self._strip)
        self._strip.set_all(0, 0, 0)
        self._strip.show()

        if self._server_sock is not None:
            self._sel.unregister(self._server_sock)
            self._server_sock.close()
        self._sel.close()

        if os.path.exists(self._socket_path):
            os.unlink(self._socket_path)
        logger.info("LED daemon stopped")
