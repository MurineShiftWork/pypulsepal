import numpy as np


def volts_to_bytes(volt=None, dac_bitMax=None):
    """Convert volts to bytes, given scaling by DAC maximum bit value"""
    return np.ceil(((volt + 10) / float(20)) * dac_bitMax)


def encode_message(*message_parts, encoding=None):
    """Encode message as byte string for serial interface communication"""
    message = [np.array(part, dtype=encoding).tobytes() for part in message_parts]
    out = b"".join(message)
    return out
