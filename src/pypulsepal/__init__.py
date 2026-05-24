__author__ = "Lars B. Rollik"

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pypulsepal")
except PackageNotFoundError:
    __version__ = "unknown"

from pypulsepal.pulsepal import PulsePal as PulsePal
