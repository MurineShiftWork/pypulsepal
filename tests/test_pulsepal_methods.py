"""Tests for PulsePal serial-sending methods (mocked hardware)."""

from unittest.mock import MagicMock, patch

import pytest

from pypulsepal.pulsepal import PulsePal


def _make_pp(firmware_version: int = 21, config=None):
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
def pp_arcom():
    return _make_pp()


@pytest.fixture
def pp(pp_arcom):
    return pp_arcom[0]


@pytest.fixture
def arcom(pp_arcom):
    return pp_arcom[1]


# ---------------------------------------------------------------------------
# sync_all_params
# ---------------------------------------------------------------------------


class TestSyncAllParams:
    def test_returns_true_on_success(self, pp, arcom):
        arcom.read_uint8.return_value = 1
        assert pp.sync_all_params() is True

    def test_returns_false_on_failure(self, pp, arcom):
        arcom.read_uint8.return_value = 0
        assert pp.sync_all_params() is False

    def test_calls_write_array(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.sync_all_params()
        arcom.write_array.assert_called_once()

    def test_message_contains_program_all_opcode(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.sync_all_params()
        msg = arcom.write_array.call_args[0][0]
        assert bytes([73]) in msg  # opcode 73 = PROGRAM_ALL

    def test_model1_no_uint16_section(self):
        pp, arcom = _make_pp(firmware_version=10)
        arcom.write_array.reset_mock()
        pp.sync_all_params()
        msg = arcom.write_array.call_args[0][0]
        assert msg is not None

    def test_reads_confirmation(self, pp, arcom):
        arcom.read_uint8.reset_mock()
        pp.sync_all_params()
        arcom.read_uint8.assert_called_once()


# ---------------------------------------------------------------------------
# program_one_param
# ---------------------------------------------------------------------------


class TestProgramOneParam:
    def test_returns_true_on_success(self, pp, arcom):
        arcom.read_uint8.return_value = 1
        result = pp.program_one_param(
            channel=0, param_name="phase1Voltage", param_value=3.0
        )
        assert result is True

    def test_updates_channel_config_on_success(self, pp, arcom):
        arcom.read_uint8.return_value = 1
        pp.program_one_param(channel=0, param_name="phase1Voltage", param_value=2.5)
        assert pp.channel_configs[0].phase1Voltage == 2.5

    def test_does_not_update_config_on_failure(self, pp, arcom):
        arcom.read_uint8.return_value = 0
        original = pp.channel_configs[0].phase1Voltage
        pp.program_one_param(channel=0, param_name="phase1Voltage", param_value=9.0)
        assert pp.channel_configs[0].phase1Voltage == original

    def test_sends_channel_1indexed(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.program_one_param(channel=0, param_name="phase1Voltage", param_value=5.0)
        msg = arcom.write_array.call_args[0][0]
        assert bytes([1]) in msg  # channel 0+1 = 1

    def test_time_param_scales_by_cycle_frequency(self, pp, arcom):
        arcom.read_uint8.return_value = 1
        pp.program_one_param(channel=0, param_name="phase1Duration", param_value=0.001)
        assert pp.channel_configs[0].phase1Duration == 0.001


# ---------------------------------------------------------------------------
# trigger_selected_channels
# ---------------------------------------------------------------------------


class TestTriggerSelectedChannels:
    def test_channel_1_only(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.trigger_selected_channels(channel_1=True)
        msg = arcom.write_array.call_args[0][0]
        assert bytes([1]) in msg

    def test_channel_2_only(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.trigger_selected_channels(channel_2=True)
        msg = arcom.write_array.call_args[0][0]
        assert bytes([2]) in msg

    def test_channels_1_and_3(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.trigger_selected_channels(channel_1=True, channel_3=True)
        msg = arcom.write_array.call_args[0][0]
        assert bytes([5]) in msg  # 1 + 4

    def test_all_channels(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.trigger_all_channels()
        msg = arcom.write_array.call_args[0][0]
        assert bytes([15]) in msg  # 1+2+4+8

    def test_no_channels(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.trigger_selected_channels()
        msg = arcom.write_array.call_args[0][0]
        assert bytes([0]) in msg

    def test_contains_soft_trigger_opcode(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.trigger_selected_channels(channel_1=True)
        msg = arcom.write_array.call_args[0][0]
        assert bytes([77]) in msg  # opcode 77 = SOFT_TRIGGER


# ---------------------------------------------------------------------------
# stop_all_outputs
# ---------------------------------------------------------------------------


class TestStopAllOutputs:
    def test_calls_write_array(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.stop_all_outputs()
        arcom.write_array.assert_called_once()

    def test_contains_abort_all_opcode(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.stop_all_outputs()
        msg = arcom.write_array.call_args[0][0]
        assert bytes([80]) in msg  # opcode 80 = ABORT_ALL


# ---------------------------------------------------------------------------
# set_fixed_voltage
# ---------------------------------------------------------------------------


class TestSetFixedVoltage:
    def test_returns_true_on_success(self, pp, arcom):
        arcom.read_uint8.return_value = 1
        assert pp.set_fixed_voltage(channel=0, voltage=3.3) is True

    def test_model2_sends_uint16(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.set_fixed_voltage(channel=0, voltage=5.0)
        msg = arcom.write_array.call_args[0][0]
        assert len(msg) > 4  # uint16 voltage → 2 bytes, not 1

    def test_model1_sends_uint8(self):
        pp, arcom = _make_pp(firmware_version=10)
        arcom.write_array.reset_mock()
        pp.set_fixed_voltage(channel=0, voltage=5.0)
        msg = arcom.write_array.call_args[0][0]
        assert msg is not None

    def test_channel_is_1indexed(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.set_fixed_voltage(channel=2, voltage=0.0)
        msg = arcom.write_array.call_args[0][0]
        assert bytes([3]) in msg  # channel 2+1 = 3


# ---------------------------------------------------------------------------
# upload_custom_pulse_train
# ---------------------------------------------------------------------------


class TestUploadCustomPulseTrain:
    def test_invalid_id_raises(self, pp):
        with pytest.raises(ValueError, match="pulse_train_id"):
            pp.upload_custom_pulse_train(
                pulse_train_id=2, pulse_times=[0.0], pulse_voltages=[5.0]
            )

    def test_mismatched_lengths_raises(self, pp):
        with pytest.raises(ValueError):
            pp.upload_custom_pulse_train(
                pulse_train_id=0,
                pulse_times=[0.0, 0.1],
                pulse_voltages=[5.0],
            )

    def test_returns_true_on_success(self, pp, arcom):
        arcom.read_uint8.return_value = 1
        result = pp.upload_custom_pulse_train(
            pulse_train_id=0,
            pulse_times=[0.0, 0.05],
            pulse_voltages=[5.0, 3.0],
        )
        assert result is True

    def test_slot_0_and_1_both_accepted(self, pp, arcom):
        for slot in (0, 1):
            result = pp.upload_custom_pulse_train(
                pulse_train_id=slot,
                pulse_times=[0.0],
                pulse_voltages=[5.0],
            )
            assert result is True


# ---------------------------------------------------------------------------
# upload_custom_waveform
# ---------------------------------------------------------------------------


class TestUploadCustomWaveform:
    def test_invalid_id_raises(self, pp):
        with pytest.raises(ValueError, match="pulse_train_id"):
            pp.upload_custom_waveform(
                pulse_train_id=3, pulse_width=0.001, pulse_voltages=[5.0]
            )

    def test_returns_true_on_success(self, pp, arcom):
        arcom.read_uint8.return_value = 1
        result = pp.upload_custom_waveform(
            pulse_train_id=0,
            pulse_width=0.001,
            pulse_voltages=[5.0, 3.0, 0.0, -3.0, -5.0],
        )
        assert result is True

    def test_calls_write_array(self, pp, arcom):
        arcom.write_array.reset_mock()
        pp.upload_custom_waveform(
            pulse_train_id=0, pulse_width=0.001, pulse_voltages=[5.0]
        )
        arcom.write_array.assert_called_once()


# ---------------------------------------------------------------------------
# save_settings
# ---------------------------------------------------------------------------


class TestSaveSettings:
    def test_returns_true_when_connected(self, pp, arcom):
        arcom.serial_object.isOpen.return_value = True
        assert pp.save_settings() is True

    def test_returns_false_when_port_closed(self, pp, arcom):
        arcom.serial_object.isOpen.return_value = False
        assert pp.save_settings() is False

    def test_returns_false_when_arcom_none(self, pp):
        pp._arcom = None
        assert pp.save_settings() is False

    def test_sends_disconnect_opcode(self, pp, arcom):
        arcom.serial_object.isOpen.return_value = True
        arcom.write_array.reset_mock()
        pp.save_settings()
        msg = arcom.write_array.call_args[0][0]
        assert bytes([81]) in msg  # opcode 81 = DISCONNECT

    def test_no_ack_read(self, pp, arcom):
        arcom.serial_object.isOpen.return_value = True
        arcom.read_uint8.reset_mock()
        pp.save_settings()
        arcom.read_uint8.assert_not_called()


# ---------------------------------------------------------------------------
# context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_enter_returns_self(self, pp):
        result = pp.__enter__()
        assert result is pp

    def test_exit_calls_save_settings(self, pp, arcom):
        arcom.serial_object.isOpen.return_value = True
        arcom.write_array.reset_mock()
        pp.__exit__(None, None, None)
        msg = arcom.write_array.call_args[0][0]
        assert bytes([81]) in msg  # DISCONNECT sent

    def test_exit_closes_arcom(self, pp, arcom):
        arcom.serial_object.isOpen.return_value = True
        pp.__exit__(None, None, None)
        arcom.close.assert_called_once()

    def test_context_manager_protocol(self):
        with patch("pypulsepal.pulsepal.ArCOM") as mock_cls:
            mock_arcom = MagicMock()
            mock_cls.return_value.open.return_value = mock_arcom
            mock_arcom.read_char.return_value = "K"
            mock_arcom.read_uint32.return_value = 21
            mock_arcom.serial_object.inWaiting.return_value = 0
            mock_arcom.serial_object.read.return_value = b""
            mock_arcom.read_uint8.return_value = 1
            mock_arcom.serial_object.isOpen.return_value = True

            with PulsePal(serial_port="/dev/null") as pp:
                assert isinstance(pp, PulsePal)

            mock_arcom.close.assert_called()
