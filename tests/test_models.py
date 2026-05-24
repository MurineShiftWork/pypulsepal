import pytest
from pydantic import ValidationError

from pypulsepal.models import ChannelConfig, PulsePalConfig, TriggerConfig


class TestChannelConfig:
    def test_defaults(self):
        cfg = ChannelConfig()
        assert cfg.phase1Voltage == 5.0
        assert cfg.phase2Voltage == -5.0
        assert cfg.restingVoltage == 0.0
        assert cfg.isBiphasic is False
        assert cfg.phase1Duration == 0.001
        assert cfg.interPulseInterval == 0.01
        assert cfg.pulseTrainDuration == 1.0
        assert cfg.linkTriggerChannel1 == 1
        assert cfg.linkTriggerChannel2 == 0
        assert cfg.customTrainID == 0
        assert cfg.customTrainLoop == 0

    def test_voltage_above_max(self):
        with pytest.raises(ValidationError):
            ChannelConfig(phase1Voltage=10.1)

    def test_voltage_below_min(self):
        with pytest.raises(ValidationError):
            ChannelConfig(phase1Voltage=-10.1)

    def test_all_voltage_fields_validated(self):
        for field in ("phase1Voltage", "phase2Voltage", "restingVoltage"):
            with pytest.raises(ValidationError):
                ChannelConfig(**{field: 11.0})

    def test_duration_negative(self):
        with pytest.raises(ValidationError):
            ChannelConfig(phase1Duration=-0.001)

    def test_all_duration_fields_validated(self):
        for field in (
            "phase1Duration",
            "interPhaseInterval",
            "phase2Duration",
            "interPulseInterval",
            "burstDuration",
            "interBurstInterval",
            "pulseTrainDuration",
            "pulseTrainDelay",
        ):
            with pytest.raises(ValidationError):
                ChannelConfig(**{field: -0.001})

    def test_flag_above_max(self):
        with pytest.raises(ValidationError):
            ChannelConfig(linkTriggerChannel1=2)

    def test_flag_below_min(self):
        with pytest.raises(ValidationError):
            ChannelConfig(customTrainID=-1)

    def test_validate_assignment_rejects_bad_voltage(self):
        cfg = ChannelConfig()
        with pytest.raises(ValidationError):
            cfg.phase1Voltage = 15.0

    def test_validate_assignment_accepts_valid_voltage(self):
        cfg = ChannelConfig()
        cfg.phase1Voltage = 3.5
        assert cfg.phase1Voltage == 3.5

    def test_validate_assignment_rejects_negative_duration(self):
        cfg = ChannelConfig()
        with pytest.raises(ValidationError):
            cfg.phase1Duration = -1.0

    def test_boundary_voltages_accepted(self):
        cfg = ChannelConfig(phase1Voltage=10.0, phase2Voltage=-10.0, restingVoltage=0.0)
        assert cfg.phase1Voltage == 10.0
        assert cfg.phase2Voltage == -10.0

    def test_zero_duration_accepted(self):
        cfg = ChannelConfig(burstDuration=0.0)
        assert cfg.burstDuration == 0.0


class TestTriggerConfig:
    def test_default(self):
        cfg = TriggerConfig()
        assert cfg.triggerMode == 0

    def test_valid_modes(self):
        for mode in (0, 1, 2):
            assert TriggerConfig(triggerMode=mode).triggerMode == mode

    def test_mode_above_max(self):
        with pytest.raises(ValidationError):
            TriggerConfig(triggerMode=3)

    def test_mode_below_min(self):
        with pytest.raises(ValidationError):
            TriggerConfig(triggerMode=-1)

    def test_validate_assignment(self):
        cfg = TriggerConfig()
        with pytest.raises(ValidationError):
            cfg.triggerMode = 5


class TestPulsePalConfig:
    def test_default_channel_count(self):
        assert len(PulsePalConfig().channels) == 4

    def test_default_trigger_count(self):
        assert len(PulsePalConfig().triggers) == 2

    def test_channels_keyed_1_to_4(self):
        assert set(PulsePalConfig().channels.keys()) == {1, 2, 3, 4}

    def test_triggers_keyed_1_to_2(self):
        assert set(PulsePalConfig().triggers.keys()) == {1, 2}

    def test_channels_are_default(self):
        for ch in PulsePalConfig().channels.values():
            assert ch == ChannelConfig()

    def test_triggers_are_default(self):
        for tr in PulsePalConfig().triggers.values():
            assert tr == TriggerConfig()

    def test_custom_channel(self):
        ch = ChannelConfig(phase1Voltage=2.0)
        cfg = PulsePalConfig(
            channels={1: ch, 2: ChannelConfig(), 3: ChannelConfig(), 4: ChannelConfig()}
        )
        assert cfg.channels[1].phase1Voltage == 2.0
        assert cfg.channels[2].phase1Voltage == 5.0  # default

    def test_model_validate_from_dict_int_keys(self):
        data = {
            "channels": {1: {"phase1Voltage": 1.0}, 2: {}, 3: {}, 4: {}},
            "triggers": {1: {"triggerMode": 1}, 2: {}},
        }
        cfg = PulsePalConfig.model_validate(data)
        assert cfg.channels[1].phase1Voltage == 1.0
        assert cfg.triggers[1].triggerMode == 1

    def test_model_validate_from_dict_string_keys(self):
        data = {
            "channels": {"1": {"phase1Voltage": 1.5}, "2": {}, "3": {}, "4": {}},
            "triggers": {"1": {"triggerMode": 2}, "2": {}},
        }
        cfg = PulsePalConfig.model_validate(data)
        assert cfg.channels[1].phase1Voltage == 1.5
        assert cfg.triggers[1].triggerMode == 2

    def test_model_dump_round_trip(self):
        cfg = PulsePalConfig()
        cfg.channels[1].phase1Voltage = 3.0
        dumped = cfg.model_dump()
        restored = PulsePalConfig.model_validate(dumped)
        assert restored.channels[1].phase1Voltage == 3.0
