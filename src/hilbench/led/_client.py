"""Client library for communicating with the LED daemon."""

from __future__ import annotations

import json
import logging
import socket
from typing import TYPE_CHECKING

from hilbench.led._models import DaemonStatus, SceneRequest, SceneResponse

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class LedClient:
    """Short-lived Unix socket client for the LED daemon."""

    def __init__(self, socket_path: str | Path = "/run/hil-bench/led.sock") -> None:
        self._socket_path = str(socket_path)

    def _send(self, request: SceneRequest) -> str:
        """Send a request and return the raw JSON response."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect(self._socket_path)
            sock.sendall((request.model_dump_json() + "\n").encode())
            data = sock.recv(4096)
            return data.decode().strip()
        finally:
            sock.close()

    def set_scene(
        self,
        scene: str,
        params: dict[str, object] | None = None,
    ) -> SceneResponse:
        """Set the active scene on the daemon."""
        req = SceneRequest(command="set_scene", scene=scene, params=params or {})
        raw = self._send(req)
        return SceneResponse.model_validate_json(raw)

    def off(self) -> SceneResponse:
        """Turn off all LEDs."""
        return self.set_scene("off")

    def status(self) -> DaemonStatus:
        """Get daemon status."""
        req = SceneRequest(command="status")
        raw = self._send(req)
        return DaemonStatus.model_validate_json(raw)

    def list_scenes(self) -> list[str]:
        """List available scene names."""
        req = SceneRequest(command="list_scenes")
        raw = self._send(req)
        data = json.loads(raw)
        return list(data.get("scenes", []))

    def is_daemon_running(self) -> bool:
        """Check if the daemon is reachable."""
        try:
            self.status()
        except (ConnectionRefusedError, FileNotFoundError, OSError):
            return False
        return True
