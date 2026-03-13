"""Tests for LED client IPC."""

from __future__ import annotations

import json
import socket
import threading
from typing import TYPE_CHECKING

from hilbench.led._client import LedClient
from hilbench.led._models import DaemonStatus, SceneResponse

if TYPE_CHECKING:
    from pathlib import Path


def _run_mock_server(sock_path: str, responses: list[str], ready: threading.Event) -> None:
    """Simple mock daemon that replies with pre-canned responses."""
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    srv.listen(1)
    srv.settimeout(5.0)
    ready.set()

    for resp_data in responses:
        try:
            conn, _ = srv.accept()
            conn.recv(4096)  # read request
            conn.sendall((resp_data + "\n").encode())
            conn.close()
        except TimeoutError:
            break
    srv.close()


class TestLedClient:
    def test_set_scene(self, tmp_path: Path) -> None:
        sock_path = str(tmp_path / "led.sock")
        resp = SceneResponse(ok=True, current_scene="rainbow").model_dump_json()
        ready = threading.Event()
        t = threading.Thread(target=_run_mock_server, args=(sock_path, [resp], ready))
        t.start()
        ready.wait()

        client = LedClient(sock_path)
        result = client.set_scene("rainbow", {"speed": 2.0})
        assert result.ok
        assert result.current_scene == "rainbow"
        t.join(timeout=2)

    def test_off(self, tmp_path: Path) -> None:
        sock_path = str(tmp_path / "led.sock")
        resp = SceneResponse(ok=True, current_scene="off").model_dump_json()
        ready = threading.Event()
        t = threading.Thread(target=_run_mock_server, args=(sock_path, [resp], ready))
        t.start()
        ready.wait()

        client = LedClient(sock_path)
        result = client.off()
        assert result.ok
        assert result.current_scene == "off"
        t.join(timeout=2)

    def test_status(self, tmp_path: Path) -> None:
        sock_path = str(tmp_path / "led.sock")
        status = DaemonStatus(
            running=True, current_scene="idle", led_count=16, uptime_s=10.0
        ).model_dump_json()
        ready = threading.Event()
        t = threading.Thread(target=_run_mock_server, args=(sock_path, [status], ready))
        t.start()
        ready.wait()

        client = LedClient(sock_path)
        result = client.status()
        assert result.running
        assert result.current_scene == "idle"
        t.join(timeout=2)

    def test_list_scenes(self, tmp_path: Path) -> None:
        sock_path = str(tmp_path / "led.sock")
        resp = json.dumps({"ok": True, "scenes": ["idle", "off", "rainbow"]})
        ready = threading.Event()
        t = threading.Thread(target=_run_mock_server, args=(sock_path, [resp], ready))
        t.start()
        ready.wait()

        client = LedClient(sock_path)
        result = client.list_scenes()
        assert "idle" in result
        assert "rainbow" in result
        t.join(timeout=2)

    def test_is_daemon_running_false_when_no_socket(self, tmp_path: Path) -> None:
        client = LedClient(str(tmp_path / "nonexistent.sock"))
        assert client.is_daemon_running() is False

    def test_is_daemon_running_true(self, tmp_path: Path) -> None:
        sock_path = str(tmp_path / "led.sock")
        status = DaemonStatus(
            running=True, current_scene="idle", led_count=16, uptime_s=1.0
        ).model_dump_json()
        ready = threading.Event()
        t = threading.Thread(target=_run_mock_server, args=(sock_path, [status], ready))
        t.start()
        ready.wait()

        client = LedClient(sock_path)
        assert client.is_daemon_running() is True
        t.join(timeout=2)
