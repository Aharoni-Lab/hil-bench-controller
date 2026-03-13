"""Custom exception hierarchy for HIL Bench Controller."""


class HilBenchError(Exception):
    """Base exception for all HIL bench errors."""


class ConfigError(HilBenchError):
    """Configuration loading or validation error."""


class ProbeError(HilBenchError):
    """Probe communication or flash error."""


class FlashError(ProbeError):
    """Firmware flash operation failed."""


class SerialError(HilBenchError):
    """Serial port communication error."""


class GpioError(HilBenchError):
    """GPIO operation error."""


class HealthCheckError(HilBenchError):
    """One or more health checks failed."""


class ArtifactError(HilBenchError):
    """Firmware artifact not found or invalid."""


class LedError(HilBenchError):
    """LED strip or daemon error."""
