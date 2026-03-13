"""Tests for firmware artifact path resolution."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from hilbench.artifacts import resolve_firmware_path
from hilbench.exceptions import ArtifactError


class TestResolveFirmwarePath:
    def test_absolute_path_returned_as_is(self, tmp_path: Path) -> None:
        fw = tmp_path / "firmware.elf"
        fw.write_bytes(b"\x00")
        result = resolve_firmware_path(str(fw), workspace=tmp_path / "ws")
        assert result == fw

    def test_cwd_takes_priority_over_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A file in CWD is found before the workspace is checked."""
        cwd_dir = tmp_path / "cwd"
        ws_dir = tmp_path / "ws"
        cwd_dir.mkdir()
        ws_dir.mkdir()

        cwd_fw = cwd_dir / "test.bin"
        cwd_fw.write_bytes(b"\x01")
        ws_fw = ws_dir / "test.bin"
        ws_fw.write_bytes(b"\x02")

        monkeypatch.chdir(cwd_dir)
        result = resolve_firmware_path("test.bin", workspace=ws_dir)
        assert result == cwd_fw

    def test_workspace_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Falls back to workspace when CWD doesn't contain the file."""
        cwd_dir = tmp_path / "cwd"
        ws_dir = tmp_path / "ws"
        cwd_dir.mkdir()
        ws_dir.mkdir()

        ws_fw = ws_dir / "test.bin"
        ws_fw.write_bytes(b"\x02")

        monkeypatch.chdir(cwd_dir)
        result = resolve_firmware_path("test.bin", workspace=ws_dir)
        assert result == ws_fw

    def test_glob_cwd_first(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Glob matches CWD before workspace."""
        cwd_dir = tmp_path / "cwd"
        ws_dir = tmp_path / "ws"
        cwd_dir.mkdir()
        ws_dir.mkdir()

        cwd_fw = cwd_dir / "firmware.elf"
        cwd_fw.write_bytes(b"\x01")

        monkeypatch.chdir(cwd_dir)
        result = resolve_firmware_path("*.elf", workspace=ws_dir)
        assert result == cwd_fw

    def test_glob_workspace_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Glob falls back to workspace when no CWD matches."""
        cwd_dir = tmp_path / "cwd"
        ws_dir = tmp_path / "ws"
        cwd_dir.mkdir()
        ws_dir.mkdir()

        ws_fw = ws_dir / "firmware.elf"
        ws_fw.write_bytes(b"\x02")

        monkeypatch.chdir(cwd_dir)
        result = resolve_firmware_path("*.elf", workspace=ws_dir)
        assert result == ws_fw

    def test_not_found_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cwd_dir = tmp_path / "cwd"
        ws_dir = tmp_path / "ws"
        cwd_dir.mkdir()
        ws_dir.mkdir()
        monkeypatch.chdir(cwd_dir)

        with pytest.raises(ArtifactError, match="not found"):
            resolve_firmware_path("nope.bin", workspace=ws_dir)

    def test_ambiguous_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cwd_dir = tmp_path / "cwd"
        cwd_dir.mkdir()
        (cwd_dir / "a.elf").write_bytes(b"\x01")
        (cwd_dir / "b.elf").write_bytes(b"\x02")
        monkeypatch.chdir(cwd_dir)

        with pytest.raises(ArtifactError, match="ambiguous"):
            resolve_firmware_path("*.elf", workspace=tmp_path / "ws")
