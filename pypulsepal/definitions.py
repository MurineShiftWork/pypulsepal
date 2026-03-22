# https://sites.google.com/site/pulsepalwiki/matlab-gnu-octave/functions/programpulsepalparam
PARAM_CODES = {
    1: "isBiphasic",
    2: "phase1Voltage",
    3: "phase2Voltage",
    4: "phase1Duration",
    5: "interPhaseInterval",
    6: "phase2Duration",
    7: "interPulseInterval",
    8: "burstDuration",
    9: "interBurstInterval",
    10: "pulseTrainDuration",
    11: "pulseTrainDelay",
    12: "linkTriggerChannel1",
    13: "linkTriggerChannel2",
    14: "customTrainID",
    15: "customTrainTarget",
    16: "customTrainLoop",
    17: "restingVoltage",
    128: "triggerMode",
}
PARAM_NAMES = {v: k for k, v in PARAM_CODES.items()}
CHANNEL_PARAM_DEFAULTS = {
    "isBiphasic": False,
    "phase1Voltage": 5,
    "phase2Voltage": -5,
    "phase1Duration": 0.001,
    "interPhaseInterval": 0.001,
    "phase2Duration": 0.001,
    "interPulseInterval": 0.01,
    "burstDuration": 0,
    "interBurstInterval": 0,
    "pulseTrainDuration": 1,
    "pulseTrainDelay": 0,
    "linkTriggerChannel1": 1,
    "linkTriggerChannel2": 0,
    "customTrainID": 0,
    "customTrainTarget": 0,
    "customTrainLoop": 0,
    "restingVoltage": 0,
    # "triggerMode": 0,  # not a channel param
}
CHANNEL_PARAM_TEST = {
    "isBiphasic": False,
    "phase1Voltage": 1.85,
    "phase2Voltage": -2.45,
    "phase1Duration": 0.029,
    "interPhaseInterval": 0.251,
    "phase2Duration": 0.051,
    "interPulseInterval": 0.111,
    "burstDuration": 1.1,
    "interBurstInterval": 2.66,
    "pulseTrainDuration": 4.55,
    "pulseTrainDelay": 0.444,
    "linkTriggerChannel1": 0,
    "linkTriggerChannel2": 1,
    "customTrainID": 0,
    "customTrainTarget": 0,
    "customTrainLoop": 0,
    "restingVoltage": 4.99,
    "triggerMode": 1,  # not a channel param
}
TRIGGER_PARAM_TEST = {
    "triggerMode": 2,
}
TRIGGER_PARAM_DEFAULTS = {
    "triggerMode": 0,
}
TRIGGER_MODE_VALUES = {
    0: "normal",
    1: "toggle",
    2: "gated",
}
TRIGGER_MODE_NAMES = {v: k for k, v in TRIGGER_MODE_VALUES.items()}
# TYPES:
#   volt @ [2,3,17] -> "uint16",
#   ELIF [4-11] -> "uint32",
#   ELSE (for 1/biphasic, [12-16]/custom*, 128/triggerMode) -> "uint8"
PARAM_DTYPE_MODEL_1 = {
    "isBiphasic": "uint8",
    "phase1Voltage": "uint8",  # v1: uint8
    "phase2Voltage": "uint8",  # v1: uint8
    "phase1Duration": "uint32",  # param 4
    "interPhaseInterval": "uint32",
    "phase2Duration": "uint32",
    "interPulseInterval": "uint32",
    "burstDuration": "uint32",
    "interBurstInterval": "uint32",
    "pulseTrainDuration": "uint32",
    "pulseTrainDelay": "uint32",
    "linkTriggerChannel1": "uint8",
    "linkTriggerChannel2": "uint8",
    "customTrainID": "uint8",
    "customTrainTarget": "uint8",
    "customTrainLoop": "uint8",
    "restingVoltage": "uint8",  # v1: uint8, param: 17
    "triggerMode": "uint8",  # parma 128
}
PARAM_DTYPE_MODEL_2 = {
    "isBiphasic": "uint8",
    "phase1Voltage": "uint16",  # v1: uint8
    "phase2Voltage": "uint16",
    "phase1Duration": "uint32",  # param 4
    "interPhaseInterval": "uint32",
    "phase2Duration": "uint32",
    "interPulseInterval": "uint32",
    "burstDuration": "uint32",
    "interBurstInterval": "uint32",
    "pulseTrainDuration": "uint32",
    "pulseTrainDelay": "uint32",
    "linkTriggerChannel1": "uint8",
    "linkTriggerChannel2": "uint8",
    "customTrainID": "uint8",
    "customTrainTarget": "uint8",
    "customTrainLoop": "uint8",
    "restingVoltage": "uint16",  # v1: uint8, param: 17
    "triggerMode": "uint8",  # parma 128
}
PULSEPAL_CYCLE_FREQUENCY = 20000
VOLTAGE_PARAM_NAMES = {"phase1Voltage", "phase2Voltage", "restingVoltage"}
PARAM_SCALING = {
    "isBiphasic": 1,
    "phase1Voltage": 1,
    "phase2Voltage": 1,
    "phase1Duration": PULSEPAL_CYCLE_FREQUENCY,  # param 4
    "interPhaseInterval": PULSEPAL_CYCLE_FREQUENCY,
    "phase2Duration": PULSEPAL_CYCLE_FREQUENCY,
    "interPulseInterval": PULSEPAL_CYCLE_FREQUENCY,
    "burstDuration": PULSEPAL_CYCLE_FREQUENCY,
    "interBurstInterval": PULSEPAL_CYCLE_FREQUENCY,
    "pulseTrainDuration": PULSEPAL_CYCLE_FREQUENCY,
    "pulseTrainDelay": PULSEPAL_CYCLE_FREQUENCY,  # param 11
    "linkTriggerChannel1": 1,
    "linkTriggerChannel2": 1,
    "customTrainID": 1,
    "customTrainTarget": 1,
    "customTrainLoop": 1,
    "restingVoltage": 1,  # param: 17
    "triggerMode": 1,  # parma 128
}


class SendMessageHeader:
    """
    https://sites.google.com/site/pulsepalwiki/usb-serial-interface/usb-interface-v2-x
    """

    HANDSHAKE = "H"  # "H" == chr(72)

    PROGRAM_ALL = 73
    PROGRAM_ONE = 74  # next: param code, then channel, then time/voltage
    PROGRAM_CUSTOM_1 = 75
    PROGRAM_CUSTOM_2 = 76
    SOFT_TRIGGER = 77
    DISPLAY = 78
    PROGRAM_VOLT = 79

    ABORT_ALL = 80
    DISCONNECT = 81

    CONTINUOUS = 82  # channel, state

    CLIENT_ID = 89  # 6 char, e.g. python/matlab

    SETTINGS = 90

    LOGIC_SET = 86
    LOGIC_GET = 87


class ReceiveMessageHeader:
    """
    https://sites.google.com/site/pulsepalwiki/usb-serial-interface/usb-interface-v2-x
    """

    HANDSHAKE_OK = "K"  # "K" == chr(75)  # + 32-bit int for firmware version

    PROGRAM_ALL_OK = 1
    PROGRAM_ONE_OK = 1


CUSTOM_PULSE_TRAIN_OPCODES = {
    0: SendMessageHeader.PROGRAM_CUSTOM_1,
    1: SendMessageHeader.PROGRAM_CUSTOM_2,
}


def resolve_param_name_code_pair(param_name_or_code=None):
    """Expect parameter name or code (integer) and return both name and code"""
    param_name = param_code = param_name_or_code
    if isinstance(param_name_or_code, str):
        param_code = PARAM_NAMES.get(param_name_or_code)
    elif isinstance(param_name_or_code, int):
        param_name = PARAM_CODES.get(param_name_or_code)
    else:
        raise ValueError(param_name_or_code)

    assert param_name is not None and param_code is not None
    return param_name, param_code


def resolve_trigger_name_code_pair(trigger_name_or_code=None):
    trigger_name = trigger_code = trigger_name_or_code
    if isinstance(trigger_name_or_code, str):
        trigger_code = PARAM_NAMES.get(trigger_name_or_code)
    elif isinstance(trigger_name_or_code, int):
        trigger_name = PARAM_CODES.get(trigger_name_or_code)
    else:
        raise ValueError(trigger_name_or_code)

    assert trigger_name is not None and trigger_code is not None
    return trigger_name, trigger_code
