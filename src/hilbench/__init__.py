"""HIL Bench Controller — automated MCU firmware testing on Raspberry Pi."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("hil-bench-controller")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
