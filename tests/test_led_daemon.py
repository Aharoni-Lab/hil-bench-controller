"""Tests for LED daemon."""

from __future__ import annotations

import json
import socket
import threading
import time
from typing import TYPE_CHECKING

from hilbench.led._daemon import LedDaemon

if TYPE_CHECKING:
    from pathlib import Path


def _wait_for_socket(sock_path: str, timeout: float = 5.0) -> bool:
    """Wait until the daemon socket is accepting connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(sock_path)
            s.close()
            return True
        except (ConnectionRefusedError, FileNotFoundError):
            time.sleep(0.05)
    return False


def _send_command(sock_path: str, command: dict[str, object]) -> dict[str, object]:
    """Send a JSON command and parse the response."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect(sock_path)
    s.sendall((json.dumps(command) + "\n").encode())
    data = s.recv(4096).decode().strip()
    s.close()
    return json.loads(data)


class TestLedDaemon:
    def test_starts_and_responds_to_status(self, tmp_path: Path) -> None:
        sock_path = str(tmp_path / "led.sock")
        daemon = LedDaemon(led_count=8, fps=30, socket_path=sock_path, use_stub=True)

        t = threading.Thread(target=daemon.run, daemon=True)
        t.start()
        assert _wait_for_socket(sock_path)

        resp = _send_command(sock_path, {"command": "status"})
        assert resp["running"] is True
        assert resp["led_count"] == 8

        daemon._shutdown = True
        t.join(timeout=3)

    def test_set_scene(self, tmp_path: Path) -> None:
        sock_path = str(tmp_path / "led.sock")
        daemon = LedDaemon(led_count=8, fps=30, socket_path=sock_path, use_stub=True)

        t = threading.Thread(target=daemon.run, daemon=True)
        t.start()
        assert _wait_for_socket(sock_path)

        resp = _send_command(
            sock_path,
            {"command": "set_scene", "scene": "solid", "params": {"color": [255, 0, 0]}},
        )
        assert resp["ok"] is True
        assert resp["current_scene"] == "solid"

        daemon._shutdown = True
        t.join(timeout=3)

    def test_set_unknown_scene(self, tmp_path: Path) -> None:
        sock_path = str(tmp_path / "led.sock")
        daemon = LedDaemon(led_count=4, fps=30, socket_path=sock_path, use_stub=True)

        t = threading.Thread(target=daemon.run, daemon=True)
        t.start()
        assert _wait_for_socket(sock_path)

        resp = _send_command(
            sock_path, {"command": "set_scene", "scene": "does_not_exist", "params": {}}
        )
        assert resp["ok"] is False
        assert "unknown scene" in resp["error"]

        daemon._shutdown = True
        t.join(timeout=3)

    def test_list_scenes(self, tmp_path: Path) -> None:
        sock_path = str(tmp_path / "led.sock")
        daemon = LedDaemon(led_count=4, fps=30, socket_path=sock_path, use_stub=True)

        t = threading.Thread(target=daemon.run, daemon=True)
        t.start()
        assert _wait_for_socket(sock_path)

        resp = _send_command(sock_path, {"command": "list_scenes"})
        assert resp["ok"] is True
        assert "idle" in resp["scenes"]
        assert "rainbow" in resp["scenes"]

        daemon._shutdown = True
        t.join(timeout=3)

    def test_invalid_json(self, tmp_path: Path) -> None:
        sock_path = str(tmp_path / "led.sock")
        daemon = LedDaemon(led_count=4, fps=30, socket_path=sock_path, use_stub=True)

        t = threading.Thread(target=daemon.run, daemon=True)
        t.start()
        assert _wait_for_socket(sock_path)

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect(sock_path)
        s.sendall(b"not json\n")
        data = s.recv(4096).decode().strip()
        s.close()
        resp = json.loads(data)
        assert resp["ok"] is False

        daemon._shutdown = True
        t.join(timeout=3)

    def test_boots_to_idle(self, tmp_path: Path) -> None:
        sock_path = str(tmp_path / "led.sock")
        daemon = LedDaemon(led_count=4, fps=60, socket_path=sock_path, use_stub=True)

        t = threading.Thread(target=daemon.run, daemon=True)
        t.start()
        assert _wait_for_socket(sock_path)

        # Wait for boot→idle transition (2 seconds)
        time.sleep(2.5)
        resp = _send_command(sock_path, {"command": "status"})
        assert resp["current_scene"] == "idle"

        daemon._shutdown = True
        t.join(timeout=3)

    def test_socket_cleaned_up_on_shutdown(self, tmp_path: Path) -> None:
        sock_path = str(tmp_path / "led.sock")
        daemon = LedDaemon(led_count=4, fps=30, socket_path=sock_path, use_stub=True)

        t = threading.Thread(target=daemon.run, daemon=True)
        t.start()
        assert _wait_for_socket(sock_path)

        daemon._shutdown = True
        t.join(timeout=3)

        import os

        assert not os.path.exists(sock_path)
