import pytest

from pypulsepal.definitions import (
    PARAM_CODES,
    PARAM_DTYPE_MODEL_1,
    PARAM_DTYPE_MODEL_2,
    PARAM_NAMES,
    PARAM_SCALING,
    TIME_PARAMS,
    VOLTAGE_PARAMS,
    resolve_param_name_code_pair,
)

# Parameter codes and wire sizes as listed by the USB serial interface pages.
EXPECTED_CODES = {
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


def _expected_dtype(code, voltage_dtype):
    if 4 <= code <= 11:
        return "uint32"
    if code in (2, 3, 17):
        return voltage_dtype
    return "uint8"


def test_param_codes():
    assert PARAM_CODES == EXPECTED_CODES
    assert list(PARAM_CODES) == list(EXPECTED_CODES)
    assert {name: code for code, name in EXPECTED_CODES.items()} == PARAM_NAMES


def test_program_all_orders():
    assert TIME_PARAMS == (
        "phase1Duration",
        "interPhaseInterval",
        "phase2Duration",
        "interPulseInterval",
        "burstDuration",
        "interBurstInterval",
        "pulseTrainDuration",
        "pulseTrainDelay",
    )
    assert VOLTAGE_PARAMS == ("phase1Voltage", "phase2Voltage", "restingVoltage")


@pytest.mark.parametrize(
    ("table", "voltage_dtype"),
    [(PARAM_DTYPE_MODEL_1, "uint8"), (PARAM_DTYPE_MODEL_2, "uint16")],
)
def test_param_dtypes(table, voltage_dtype):
    assert table == {
        name: _expected_dtype(code, voltage_dtype)
        for code, name in EXPECTED_CODES.items()
    }


def test_param_scaling():
    assert {
        name: 20000 if 4 <= code <= 11 else 1 for code, name in EXPECTED_CODES.items()
    } == PARAM_SCALING


def test_resolve_by_name_and_code():
    assert resolve_param_name_code_pair("restingVoltage") == ("restingVoltage", 17)
    assert resolve_param_name_code_pair(128) == ("triggerMode", 128)


@pytest.mark.parametrize("bad", ["phase3Voltage", 18, 1.0, None])
def test_resolve_unknown_raises(bad):
    with pytest.raises(ValueError):
        resolve_param_name_code_pair(bad)
