"""Firmware artifact path resolution from GitHub Actions runner work directory."""

from __future__ import annotations

import logging
from pathlib import Path

from hilbench.exceptions import ArtifactError

logger = logging.getLogger(__name__)

RUNNER_WORK_DIR = Path("/opt/hil-bench/_work")


def resolve_firmware_path(
    firmware: str | Path,
    workspace: Path = RUNNER_WORK_DIR,
) -> Path:
    """Resolve a firmware path — absolute, relative to CWD, or relative to workspace.

    Resolution order:
      1. Absolute path: returned as-is
      2. Relative to CWD: if it exists
      3. Relative to runner workspace: if it exists
      4. Glob against CWD, then workspace: if exactly one match
    """
    path = Path(firmware)

    # Absolute path — trust the caller to handle missing files
    if path.is_absolute():
        return path

    # Relative to CWD first
    cwd_resolved = Path.cwd() / path
    if cwd_resolved.exists():
        return cwd_resolved

    # Relative to workspace
    ws_resolved = workspace / path
    if ws_resolved.exists():
        return ws_resolved

    # Try glob — CWD first, then workspace
    pattern = str(firmware)

    cwd_matches = sorted(Path.cwd().glob(pattern))
    if len(cwd_matches) == 1:
        return cwd_matches[0]
    if len(cwd_matches) > 1:
        raise ArtifactError(f"ambiguous firmware path {firmware!r}: matched {len(cwd_matches)} files in CWD")

    ws_matches = sorted(workspace.glob(pattern))
    if len(ws_matches) == 1:
        return ws_matches[0]
    if len(ws_matches) > 1:
        raise ArtifactError(f"ambiguous firmware path {firmware!r}: matched {len(ws_matches)} files in workspace")

    raise ArtifactError(
        f"firmware {firmware!r} not found in CWD ({Path.cwd()}) or workspace ({workspace})"
    )
