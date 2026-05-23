__author__ = "Lars B. Rollik"

try:
    from importlib.metadata import version

    __version__ = version("pypulsepal")
except Exception:
    __version__ = "0.1.0"

from pypulsepal.pulsepal import PulsePal as PulsePal


def run():
    raise NotImplementedError(
        "placeholder for commandline interface to program from given config file"
    )
