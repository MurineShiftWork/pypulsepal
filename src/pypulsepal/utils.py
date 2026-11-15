import math

import numpy as np

#: Output range of every channel: DAC code 0 is V_MIN, full scale is V_MIN + V_SPAN.
V_MIN = -10.0
V_SPAN = 20.0


def volts_to_dac(volts: float, dac_max: int) -> int:
    """DAC code for an output voltage, rounded up and clamped to ``[0, dac_max]``.

    Args:
        volts: Output voltage in volts.
        dac_max: Full-scale code of the DAC (255 on model 1, 65535 on model 2).
    """
    fraction = (volts - V_MIN) / V_SPAN
    code = math.ceil(fraction * dac_max)
    return min(max(code, 0), dac_max)


def encode_message(*message_parts, encoding=None) -> bytes:
    """Pack scalars or sequences as little-endian ``encoding`` and concatenate."""
    dtype = np.dtype(encoding).newbyteorder("<")
    return b"".join(np.asarray(part, dtype=dtype).tobytes() for part in message_parts)
