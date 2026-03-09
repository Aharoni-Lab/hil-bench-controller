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
    """Resolve a firmware path — absolute or relative to runner workspace.

    Accepts:
      - Absolute path: returned as-is if it exists
      - Relative path: resolved against the runner workspace directory
      - Glob pattern: if exactly one match, return it
    """
    path = Path(firmware)

    # Absolute path
    if path.is_absolute():
        if path.exists():
            return path
        raise ArtifactError(f"firmware not found: {path}")

    # Relative to workspace
    resolved = workspace / path
    if resolved.exists():
        return resolved

    # Try glob
    pattern = str(firmware)
    matches = sorted(workspace.glob(pattern))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ArtifactError(f"ambiguous firmware path {firmware!r}: matched {len(matches)} files")

    raise ArtifactError(f"firmware {firmware!r} not found in workspace {workspace}")
