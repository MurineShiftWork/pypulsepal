"""Constants of the PulsePal USB serial protocol.

Sources:
    https://sites.google.com/site/pulsepalwiki/usb-serial-interface/usb-interface-v2-x
    https://sites.google.com/site/pulsepalwiki/usb-serial-interface/usb-interface-v1-x
    https://sites.google.com/site/pulsepalwiki/parameter-guide
"""

#: Hardware timer rate: one cycle is 50 us, so time values are sent as cycles.
PULSEPAL_CYCLE_FREQUENCY = 20000

#: Firmware builds from this number on are model 2 hardware (16-bit DAC).
MODEL_2_MIN_FIRMWARE = 20

#: Full-scale DAC code per hardware model; 0 is -10 V and the maximum is +10 V.
DAC_MAX = {1: 255, 2: 65535}

#: Six characters sent with the client ID opcode, shown on the device display.
CLIENT_NAME = b"PYTHON"

#: Output channel parameters in code order: the parameter code is the position + 1.
_CHANNEL_PARAMS = (
    "isBiphasic",
    "phase1Voltage",
    "phase2Voltage",
    "phase1Duration",
    "interPhaseInterval",
    "phase2Duration",
    "interPulseInterval",
    "burstDuration",
    "interBurstInterval",
    "pulseTrainDuration",
    "pulseTrainDelay",
    "linkTriggerChannel1",
    "linkTriggerChannel2",
    "customTrainID",
    "customTrainTarget",
    "customTrainLoop",
    "restingVoltage",
)
TRIGGER_MODE_PARAM_CODE = 128

PARAM_CODES = dict(enumerate(_CHANNEL_PARAMS, start=1))
PARAM_CODES[TRIGGER_MODE_PARAM_CODE] = "triggerMode"
PARAM_NAMES = {name: code for code, name in PARAM_CODES.items()}

#: Codes 4 to 11: durations, 32-bit cycle counts, in program-all order.
TIME_PARAMS = tuple(PARAM_CODES[code] for code in range(4, 12))
#: Codes 2, 3 and 17: voltages as DAC codes, in program-all order.
VOLTAGE_PARAMS = tuple(PARAM_CODES[code] for code in (2, 3, 17))
VOLTAGE_PARAM_NAMES = set(VOLTAGE_PARAMS)

TRIGGER_MODE_VALUES = {0: "normal", 1: "toggle", 2: "gated"}
TRIGGER_MODE_NAMES = {name: value for value, name in TRIGGER_MODE_VALUES.items()}


def _wire_dtypes(voltage_dtype: str) -> dict[str, str]:
    """Wire dtype per parameter: times uint32, voltages per model, the rest uint8."""
    dtypes = {}
    for name in PARAM_NAMES:
        if name in TIME_PARAMS:
            dtypes[name] = "uint32"
        elif name in VOLTAGE_PARAM_NAMES:
            dtypes[name] = voltage_dtype
        else:
            dtypes[name] = "uint8"
    return dtypes


PARAM_DTYPE_MODEL_1 = _wire_dtypes("uint8")
PARAM_DTYPE_MODEL_2 = _wire_dtypes("uint16")
PARAM_DTYPES = {1: PARAM_DTYPE_MODEL_1, 2: PARAM_DTYPE_MODEL_2}

#: Factor from natural units to wire units; voltages are converted separately.
PARAM_SCALING = {
    name: PULSEPAL_CYCLE_FREQUENCY if name in TIME_PARAMS else 1 for name in PARAM_NAMES
}


class SendMessageHeader:
    """Opcodes sent from host to device, each after the prefix byte 213.

    See: https://sites.google.com/site/pulsepalwiki/usb-serial-interface/usb-interface-v2-x
    """

    HANDSHAKE = "H"  # opcode 72
    PROGRAM_ALL = 73  # every parameter of every channel in one block
    PROGRAM_ONE = 74  # param code, channel (1-4), value
    PROGRAM_CUSTOM_1 = 75  # pulse count, times, voltages
    PROGRAM_CUSTOM_2 = 76
    SOFT_TRIGGER = 77  # one byte, bit n selects output channel n + 1
    DISPLAY = 78
    PROGRAM_VOLT = 79  # channel, DAC code
    ABORT_ALL = 80
    DISCONNECT = 81  # also stores the current parameters on the device
    CONTINUOUS = 82  # channel, 0 or 1
    READ_SD = 85
    LOGIC_SET = 86  # line, level
    LOGIC_GET = 87  # line; device replies with the level
    CLIENT_ID = 89  # six ASCII characters
    SETTINGS = 90  # SD settings file: op, name length, name


class ReceiveMessageHeader:
    """Replies sent from device to host.

    See: https://sites.google.com/site/pulsepalwiki/usb-serial-interface/usb-interface-v2-x
    """

    HANDSHAKE_OK = "K"  # followed by the firmware build as uint32
    ACK = 1


#: Custom train slot (0 or 1) to its upload opcode.
CUSTOM_PULSE_TRAIN_OPCODES = {
    0: SendMessageHeader.PROGRAM_CUSTOM_1,
    1: SendMessageHeader.PROGRAM_CUSTOM_2,
}

#: Operation byte of the SETTINGS opcode that writes the settings file.
SD_SAVE = 1


def resolve_param_name_code_pair(param_name_or_code=None) -> tuple[str, int]:
    """Return ``(name, code)`` for a parameter given by either one.

    Raises:
        ValueError: for an unknown name or code, or a value of another type.
    """
    name: str | None
    code: int | None
    if isinstance(param_name_or_code, str):
        name, code = param_name_or_code, PARAM_NAMES.get(param_name_or_code)
    elif isinstance(param_name_or_code, int):
        name, code = PARAM_CODES.get(param_name_or_code), param_name_or_code
    else:
        name = code = None
    if name is None or code is None:
        raise ValueError(f"unknown PulsePal parameter {param_name_or_code!r}")
    return name, code
