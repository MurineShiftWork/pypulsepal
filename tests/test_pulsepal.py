import struct
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pypulsepal.definitions import PULSEPAL_CYCLE_FREQUENCY
from pypulsepal.models import ChannelConfig, PulsePalConfig, TriggerConfig
from pypulsepal.pulsepal import PulsePal


def _make_pp(config: PulsePalConfig | None = None, firmware_version: int = 21):
    """Construct a PulsePal with a mocked serial connection.

    firmware_version=21 → model 2, no v20 bug-warning noise.
    Returns (pp, mock_arcom). The patch exits after construction; pp._arcom
    remains the mock, so subsequent method calls on pp work without re-patching.
    """
    with patch("pypulsepal.pulsepal.ArCOM") as mock_cls:
        mock_arcom = MagicMock()
        mock_cls.return_value.open.return_value = mock_arcom
        mock_arcom.read_char.return_value = "K"
        mock_arcom.read_uint32.return_value = firmware_version
        mock_arcom.serial_object.inWaiting.return_value = 0
        mock_arcom.serial_object.read.return_value = b""
        mock_arcom.read_uint8.return_value = 1

        if config is not None:
            pp = PulsePal.from_config(config, serial_port="/dev/null")
        else:
            pp = PulsePal(serial_port="/dev/null")

    return pp, mock_arcom


@pytest.fixture
def pp():
    instance, _ = _make_pp()
    return instance


@pytest.fixture
def pp_and_arcom():
    return _make_pp()


class TestInit:
    def test_model2_detected(self, pp):
        assert pp.model == 2

    def test_firmware_version_stored(self, pp):
        assert pp.firmware_version == 21

    def test_dac_bitmax_model2(self, pp):
        assert pp.dac_bitMax == 65535

    def test_channel_configs_count(self, pp):
        assert len(pp.channel_configs) == 4

    def test_trigger_configs_count(self, pp):
        assert len(pp.trigger_configs) == 2

    def test_channel_configs_are_default(self, pp):
        for ch in pp.channel_configs:
            assert ch == ChannelConfig()

    def test_trigger_configs_are_default(self, pp):
        for tr in pp.trigger_configs:
            assert tr == TriggerConfig()

    def test_model1_detected(self):
        pp, _ = _make_pp(firmware_version=10)
        assert pp.model == 1
        assert pp.dac_bitMax == 255


class TestConfigProperty:
    def test_returns_pulsepalconfig(self, pp):
        assert isinstance(pp.config, PulsePalConfig)

    def test_config_channel_count(self, pp):
        assert len(pp.config.channels) == 4

    def test_config_trigger_count(self, pp):
        assert len(pp.config.triggers) == 2

    def test_config_reflects_channel_state(self, pp):
        pp.channel_configs[0].phase1Voltage = 3.0
        assert pp.config.channels[1].phase1Voltage == 3.0  # channel_configs[0] → key 1

    def test_config_reflects_trigger_state(self, pp):
        pp.trigger_configs[1].triggerMode = 2
        assert pp.config.triggers[2].triggerMode == 2  # trigger_configs[1] → key 2

    def test_config_channels_are_defaults_initially(self, pp):
        for ch in pp.config.channels.values():
            assert ch == ChannelConfig()


class TestResetToDefaults:
    def test_resets_channel_voltage(self, pp_and_arcom):
        pp, _ = pp_and_arcom
        pp.channel_configs[0].phase1Voltage = 3.0
        pp.reset_to_defaults()
        assert pp.channel_configs[0].phase1Voltage == ChannelConfig().phase1Voltage

    def test_resets_all_channels(self, pp_and_arcom):
        pp, _ = pp_and_arcom
        for i in range(pp.nr_output_channels):
            pp.channel_configs[i].phase1Voltage = float(i)
        pp.reset_to_defaults()
        for ch in pp.channel_configs:
            assert ch == ChannelConfig()

    def test_resets_trigger_mode(self, pp_and_arcom):
        pp, _ = pp_and_arcom
        pp.trigger_configs[0].triggerMode = 2
        pp.reset_to_defaults()
        assert pp.trigger_configs[0].triggerMode == TriggerConfig().triggerMode

    def test_calls_sync(self, pp_and_arcom):
        pp, mock_arcom = pp_and_arcom
        mock_arcom.read_uint8.reset_mock()
        pp.reset_to_defaults()
        mock_arcom.read_uint8.assert_called()

    def test_produces_fresh_instances(self, pp_and_arcom):
        pp, _ = pp_and_arcom
        old_ch = pp.channel_configs[0]
        pp.reset_to_defaults()
        assert pp.channel_configs[0] is not old_ch


class TestFromConfig:
    def test_channels_applied(self):
        cfg = PulsePalConfig(
            channels={
                1: ChannelConfig(phase1Voltage=2.5),
                2: ChannelConfig(),
                3: ChannelConfig(),
                4: ChannelConfig(),
            },
            triggers={1: TriggerConfig(), 2: TriggerConfig()},
        )
        pp, _ = _make_pp(config=cfg)
        assert pp.channel_configs[0].phase1Voltage == 2.5
        assert pp.channel_configs[1].phase1Voltage == ChannelConfig().phase1Voltage

    def test_triggers_applied(self):
        cfg = PulsePalConfig(
            channels={i: ChannelConfig() for i in range(1, 5)},
            triggers={1: TriggerConfig(triggerMode=1), 2: TriggerConfig(triggerMode=2)},
        )
        pp, _ = _make_pp(config=cfg)
        assert pp.trigger_configs[0].triggerMode == 1
        assert pp.trigger_configs[1].triggerMode == 2

    def test_syncs_after_apply(self):
        cfg = PulsePalConfig()
        pp, mock_arcom = _make_pp(config=cfg)
        # read_uint8 must have been called at least once (sync confirmation)
        assert mock_arcom.read_uint8.call_count >= 1

    def test_configs_are_copies(self):
        cfg = PulsePalConfig()
        pp, _ = _make_pp(config=cfg)
        pp.channel_configs[0].phase1Voltage = 9.9
        assert cfg.channels[1].phase1Voltage != 9.9

    def test_returns_pulsepal_instance(self):
        pp, _ = _make_pp(config=PulsePalConfig())
        assert isinstance(pp, PulsePal)


def _make_sd_payload(channels=None, triggers=None) -> bytes:
    """Build a synthetic 178-byte SD payload matching the firmware byte layout."""
    time_names = [
        "phase1Duration",
        "interPhaseInterval",
        "phase2Duration",
        "interPulseInterval",
        "burstDuration",
        "interBurstInterval",
        "pulseTrainDuration",
        "pulseTrainDelay",
    ]
    if channels is None:
        channels = [ChannelConfig() for _ in range(4)]
    if triggers is None:
        triggers = [TriggerConfig() for _ in range(2)]

    buf = b""
    for cfg in channels:
        for name in time_names:
            cycles = int(getattr(cfg, name) * PULSEPAL_CYCLE_FREQUENCY)
            buf += struct.pack("<I", cycles)
        buf += bytes([int(cfg.isBiphasic)])
        for name in ("phase1Voltage", "phase2Voltage", "restingVoltage"):
            v = getattr(cfg, name)
            bits = int(np.ceil(((v + 10) / 20.0) * 65535))
            buf += struct.pack("<H", bits)
        buf += bytes([cfg.customTrainID, cfg.customTrainTarget, cfg.customTrainLoop])
    for tr in triggers:
        buf += bytes([tr.triggerMode, 1, 0, 0, 0])

    assert len(buf) == 178
    return buf


class TestSDMethods:
    def test_save_to_sd_no_ack_read(self, pp_and_arcom):
        pp, mock_arcom = pp_and_arcom
        mock_arcom.read_uint8.reset_mock()
        with patch("pypulsepal.pulsepal.time.sleep"):
            pp.save_to_sd()
        mock_arcom.read_uint8.assert_not_called()

    def test_save_to_sd_sends_settings_opcode(self, pp_and_arcom):
        pp, mock_arcom = pp_and_arcom
        with patch("pypulsepal.pulsepal.time.sleep"):
            pp.save_to_sd(filename="test.pps")
        written = mock_arcom.serial_object.write.call_args[0][0]
        assert bytes([90]) in written  # opcode 90 = SETTINGS

    def test_save_to_sd_encodes_filename(self, pp_and_arcom):
        pp, mock_arcom = pp_and_arcom
        with patch("pypulsepal.pulsepal.time.sleep"):
            pp.save_to_sd(filename="test.pps")
        written = mock_arcom.serial_object.write.call_args[0][0]
        assert b"test.pps" in written

    def test_save_to_sd_sleeps(self, pp_and_arcom):
        pp, _ = pp_and_arcom
        with patch("pypulsepal.pulsepal.time.sleep") as mock_sleep:
            pp.save_to_sd()
        mock_sleep.assert_called_once_with(0.1)

    def test_read_sd_params_returns_none_on_bad_length(self, pp_and_arcom):
        pp, mock_arcom = pp_and_arcom
        mock_arcom.serial_object.read.return_value = b"\x00" * 10
        with patch("pypulsepal.pulsepal.time.sleep"):
            result = pp.read_sd_params()
        assert result is None

    def test_read_sd_params_sends_opcode_85(self, pp_and_arcom):
        pp, mock_arcom = pp_and_arcom
        mock_arcom.serial_object.read.return_value = _make_sd_payload()
        with patch("pypulsepal.pulsepal.time.sleep"):
            pp.read_sd_params()
        written = mock_arcom.serial_object.write.call_args[0][0]
        assert bytes([85]) in written

    def test_read_sd_params_default_config(self, pp_and_arcom):
        pp, mock_arcom = pp_and_arcom
        channels = [ChannelConfig() for _ in range(4)]
        mock_arcom.serial_object.read.return_value = _make_sd_payload(channels=channels)
        with patch("pypulsepal.pulsepal.time.sleep"):
            result = pp.read_sd_params()
        assert result is not None
        assert abs(result["phase1Duration"][0] - 0.001) < 1e-6
        assert abs(result["phase1Voltage"][0] - 5.0) < 0.01
        assert abs(result["restingVoltage"][0] - 0.0) < 0.01

    def test_read_sd_params_custom_voltage(self, pp_and_arcom):
        pp, mock_arcom = pp_and_arcom
        channels = [ChannelConfig(phase1Voltage=3.0)] + [ChannelConfig()] * 3
        mock_arcom.serial_object.read.return_value = _make_sd_payload(channels=channels)
        with patch("pypulsepal.pulsepal.time.sleep"):
            result = pp.read_sd_params()
        assert result is not None
        assert abs(result["phase1Voltage"][0] - 3.0) < 0.01
        assert abs(result["phase1Voltage"][1] - 5.0) < 0.01  # other channels default

    def test_read_sd_params_trigger_mode(self, pp_and_arcom):
        pp, mock_arcom = pp_and_arcom
        triggers = [TriggerConfig(triggerMode=1), TriggerConfig(triggerMode=2)]
        mock_arcom.serial_object.read.return_value = _make_sd_payload(triggers=triggers)
        with patch("pypulsepal.pulsepal.time.sleep"):
            result = pp.read_sd_params()
        assert result["triggerMode"] == [1, 2]

    def test_read_sd_params_all_channels_parsed(self, pp_and_arcom):
        pp, mock_arcom = pp_and_arcom
        channels = [ChannelConfig(phase1Voltage=float(i)) for i in range(4)]
        mock_arcom.serial_object.read.return_value = _make_sd_payload(channels=channels)
        with patch("pypulsepal.pulsepal.time.sleep"):
            result = pp.read_sd_params()
        for i in range(4):
            assert abs(result["phase1Voltage"][i] - float(i)) < 0.01
