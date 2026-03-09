"""Structured logging setup with rich console output."""

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

console = Console(stderr=True)


def setup_logging(*, verbose: bool = False, log_file: Path | None = None) -> logging.Logger:
    """Configure root logger with rich console handler and optional file handler."""
    level = logging.DEBUG if verbose else logging.INFO
    handlers: list[logging.Handler] = [
        RichHandler(console=console, show_time=True, show_path=verbose, markup=True)
    ]

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s")
        )
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)
    return logging.getLogger("hilbench")
