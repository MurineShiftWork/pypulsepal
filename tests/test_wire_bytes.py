"""Exact bytes written to the serial port for every public method.

The expected transcripts live in ``wire_bytes.json`` next to this file. Each
entry is the ordered list of writes for one scenario, tagged with the call
that carried them (``A`` for ``ArCOM.write_array``, ``S`` for a raw
``serial_object.write``). Regenerate with ``python tests/test_wire_bytes.py``
only when the protocol output is meant to change.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pypulsepal.models import ChannelConfig, PulsePalConfig, TriggerConfig
from pypulsepal.pulsepal import PulsePal

GOLDEN = Path(__file__).with_name("wire_bytes.json")

FIRMWARE = {"model1": 10, "fw20": 20, "model2": 21}

VOLTAGES = [-10.0, -9.999, -5.0, -0.04, 0.0, 0.001, 1.234, 3.3, 5.0, 9.96, 10.0]


def _connect(firmware_version):
    writes: list[tuple[str, bytes]] = []
    with patch("pypulsepal.pulsepal.ArCOM") as mock_cls:
        arcom = MagicMock()
        mock_cls.return_value.open.return_value = arcom
        arcom.read_char.return_value = "K"
        arcom.read_uint32.return_value = firmware_version
        arcom.read_uint8.return_value = 1
        arcom.serial_object.inWaiting.return_value = 0
        arcom.serial_object.read.return_value = b""
        arcom.write_array.side_effect = lambda b: writes.append(("A", bytes(b)))
        arcom.serial_object.write.side_effect = lambda b: writes.append(("S", bytes(b)))
        pp = PulsePal(serial_port="/dev/null")
    return pp, writes


def _varied_config():
    channels = {}
    for i in range(1, 5):
        channels[i] = ChannelConfig(
            isBiphasic=bool(i % 2),
            phase1Voltage=round(-9.5 + 4.3 * i, 3),
            phase2Voltage=round(7.7 - 3.9 * i, 3),
            restingVoltage=round(-0.37 * i, 3),
            phase1Duration=0.0001 * i,
            interPhaseInterval=0.00035 * i,
            phase2Duration=0.0013 * i,
            interPulseInterval=0.0101 * i,
            burstDuration=0.25 * (i - 1),
            interBurstInterval=0.333 * i,
            pulseTrainDuration=1.5 * i,
            pulseTrainDelay=0.0007 * (i - 1),
            linkTriggerChannel1=i % 2,
            linkTriggerChannel2=(i + 1) % 2,
            customTrainID=(i + 1) % 2,
            customTrainTarget=i % 2,
            customTrainLoop=(i // 2) % 2,
        )
    triggers = {1: TriggerConfig(triggerMode=2), 2: TriggerConfig(triggerMode=1)}
    return PulsePalConfig(channels=channels, triggers=triggers)


def _apply(pp, config):
    pp.channel_configs = [config.channels[i + 1] for i in range(4)]
    pp.trigger_configs = [config.triggers[i + 1] for i in range(2)]


def _program_each_param(pp):
    values = {
        "isBiphasic": 1,
        "phase1Duration": 0.0123,
        "interPhaseInterval": 0.00005,
        "phase2Duration": 2.5,
        "interPulseInterval": 0.1,
        "burstDuration": 0.0,
        "interBurstInterval": 3599.99995,
        "pulseTrainDuration": 12.3456,
        "pulseTrainDelay": 0.00015,
        "linkTriggerChannel1": 1,
        "linkTriggerChannel2": 0,
        "customTrainID": 1,
        "customTrainTarget": 1,
        "customTrainLoop": 1,
    }
    for channel in range(4):
        for name, value in values.items():
            pp.program_one_param(channel=channel, param_name=name, param_value=value)
        for name in ("phase1Voltage", "phase2Voltage", "restingVoltage"):
            for volts in VOLTAGES:
                pp.program_one_param(
                    channel=channel, param_name=name, param_value=volts
                )
    pp.program_one_param(channel=1, param_name=7, param_value=0.004)
    pp.program_one_param(channel=0, param_name=2, param_value=-2.5)


def _trigger_combinations(pp):
    for mask in range(16):
        pp.trigger_selected_channels(*(bool(mask >> bit & 1) for bit in range(4)))
    pp.trigger_selected_channels(channel_3=True)
    pp.trigger_all_channels()


SCENARIOS = {
    "connect": lambda pp: None,
    "program_one_param": _program_each_param,
    "program_trigger_channel": lambda pp: [
        pp.program_trigger_channel(trigger_channel=0, trigger_mode="gated"),
        pp.program_trigger_channel(trigger_channel=1, trigger_mode=1),
        pp.program_trigger_channel(trigger_channel=0, trigger_mode="normal"),
    ],
    "sync_all_params_default": lambda pp: pp.sync_all_params(),
    "sync_all_params_varied": lambda pp: (
        _apply(pp, _varied_config()),
        pp.sync_all_params(),
    ),
    "upload_all_varied": lambda pp: (_apply(pp, _varied_config()), pp.upload_all()),
    "set_resting_voltage": lambda pp: [
        pp.set_resting_voltage(channel=c, voltage=v) for c in range(4) for v in VOLTAGES
    ],
    "set_fixed_voltage": lambda pp: [
        pp.set_fixed_voltage(channel=c, voltage=v) for c in range(4) for v in VOLTAGES
    ],
    "upload_custom_pulse_train": lambda pp: [
        pp.upload_custom_pulse_train(
            0, [0.0, 0.001, 0.00235, 0.5], [5.0, -5.0, 0.0, 9.99]
        ),
        pp.upload_custom_pulse_train(
            1, [0.0001 * k for k in range(40)], VOLTAGES * 3 + [0.1] * 7
        ),
        pp.upload_custom_pulse_train(0, [], []),
    ],
    "upload_custom_waveform": lambda pp: [
        pp.upload_custom_waveform(0, 0.001, [0.0, 2.5, 5.0, 2.5, 0.0, -2.5, -5.0]),
        pp.upload_custom_waveform(1, 0.00013, VOLTAGES),
        pp.upload_custom_waveform(1, 0.0001, [1.0] * 25),
        pp.upload_custom_waveform(0, 0.001, []),
    ],
    "set_continuous": lambda pp: [
        pp.set_continuous(channel=c, state=s) for c in range(4) for s in (0, 1)
    ],
    "logic": lambda pp: [
        (pp.set_logic(channel=c, level=c % 2), pp.get_logic(channel=c))
        for c in range(4)
    ],
    "trigger_selected_channels": _trigger_combinations,
    "stop_all_outputs": lambda pp: pp.stop_all_outputs(),
    "save_settings": lambda pp: pp.save_settings(),
    "save_to_sd": lambda pp: [pp.save_to_sd(), pp.save_to_sd("protocol_b.pps")],
    "read_sd_params": lambda pp: pp.read_sd_params(),
}


def _transcript(model, scenario):
    with patch("pypulsepal.pulsepal.time.sleep"):
        pp, writes = _connect(FIRMWARE[model])
        if scenario != "connect":
            writes.clear()
        SCENARIOS[scenario](pp)
        out = [f"{tag}:{data.hex()}" for tag, data in writes]
        pp._arcom = None
    return out


CASES = [(m, s) for m in FIRMWARE for s in SCENARIOS]


@pytest.fixture(scope="module")
def golden():
    return json.loads(GOLDEN.read_text())


@pytest.mark.parametrize(("model", "scenario"), CASES)
def test_wire_bytes_unchanged(golden, model, scenario):
    assert _transcript(model, scenario) == golden[f"{model}/{scenario}"]


if __name__ == "__main__":
    data = {f"{m}/{s}": _transcript(m, s) for m, s in CASES}
    GOLDEN.write_text(json.dumps(data, indent=1) + "\n")
    sys.stdout.write(f"wrote {len(data)} transcripts to {GOLDEN}\n")
