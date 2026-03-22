import logging

from pybpodapi.com.arcom import ArCOM

from pypulsepal.definitions import (
    CUSTOM_PULSE_TRAIN_OPCODES,
    PARAM_DTYPE_MODEL_1,
    PARAM_DTYPE_MODEL_2,
    PARAM_SCALING,
    PULSEPAL_CYCLE_FREQUENCY,
    VOLTAGE_PARAM_NAMES,
    ReceiveMessageHeader,
    SendMessageHeader,
    resolve_param_name_code_pair,
    resolve_trigger_name_code_pair,
)
from pypulsepal.models import ChannelConfig, TriggerConfig
from pypulsepal.utils import encode_message, volts_to_bytes

ENCODING_UINT8 = "uint8"


class PulsePalError(Exception):
    """Convenience error object for PulsePal"""

    pass


class PulsePal:
    """"""

    # communication
    _arcom = None
    serial_port = None
    baudrate = 115200

    # hardware attributes
    firmware_version = None
    model = None
    dac_bitMax = None
    cycle_frequency = 20000
    nr_output_channels = 4
    nr_trigger_channels = 2
    opcode = 213
    param_dtype_lookup = None

    def __init__(
        self,
        serial_port=None,
        baudrate=115200,
        cycle_frequency=PULSEPAL_CYCLE_FREQUENCY,
        nr_output_channels=4,
        nr_trigger_channels=2,
        opcode=213,
        **kwargs,
    ):
        """
        :param serial_port:
        :param baudrate:
        :param cycle_frequency:
        :param nr_output_channels:
        :param nr_trigger_channels:
        :param kwargs:
        """
        super().__init__()

        self.serial_port = serial_port
        self.baudrate = baudrate
        self.cycle_frequency = cycle_frequency
        self.nr_output_channels = nr_output_channels
        self.nr_trigger_channels = nr_trigger_channels
        self.opcode = opcode

        self.channel_configs = [ChannelConfig() for _ in range(nr_output_channels)]
        self.trigger_configs = [TriggerConfig() for _ in range(nr_trigger_channels)]

        # Convenience updates for debug inputs
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

        self.connect(serial_port=serial_port, baudrate=baudrate)

    @property
    def encoded_opcode(self):
        return encode_message(self.opcode, encoding=ENCODING_UINT8)

    @encoded_opcode.setter
    def encoded_opcode(self, value=None):
        self.opcode = value

    def _clear_read_queue(self):
        """Clears leftover items from serial read queue"""
        return self._arcom.serial_object.read(self._arcom.serial_object.inWaiting())

    def _read_confirmation(self):
        """Returns True for successful receipt of previous message"""
        return self._arcom.read_uint8() == 1

    def _pulsepal_handshake(self):
        """Confirm connectivity with hardware.

        :return: handshake success bool
        """
        self._arcom.serial_object.write(
            self.encoded_opcode + str.encode(SendMessageHeader.HANDSHAKE)
        )
        handshake = self._arcom.read_char()
        firmware_version = self._arcom.read_uint32()
        self._clear_read_queue()

        handshake_ok = handshake == ReceiveMessageHeader.HANDSHAKE_OK
        if handshake_ok:
            self.firmware_version = firmware_version
            if firmware_version < 20:
                self.model = 1
                self.dac_bitMax = 255
                self.param_dtype_lookup = PARAM_DTYPE_MODEL_1
            else:
                self.model = 2
                self.dac_bitMax = 65535
                self.param_dtype_lookup = PARAM_DTYPE_MODEL_2
            if firmware_version == 20:
                logging.warning(
                    "Firmware v20 has a bug in Pulse Gated trigger mode when used with "
                    "multiple inputs. See https://sites.google.com/site/pulsepalwiki/updating-firmware"
                )
            # Send client name
            self._arcom.write_array(
                self.encoded_opcode
                + encode_message(SendMessageHeader.CLIENT_ID, encoding=ENCODING_UINT8)
                + str.encode("PYTHON")
            )

        return bool(handshake_ok)

    def connect(self, serial_port, baudrate=115200, timeout=1):
        """Connect (& handshake) with hardware

        :param serial_port:
        :param baudrate:
        :param timeout:
        :return:
        """
        self._arcom = ArCOM().open(
            serial_port=serial_port, baudrate=baudrate, timeout=timeout
        )
        handshake_ok = self._pulsepal_handshake()
        if not handshake_ok:
            raise PulsePalError(
                f"Could not connect PulsePal at '{serial_port}' "
                f"with baudrate {baudrate}"
            )
        return self

    def _pulsepal_set_display(self, message="--> Py"):
        """"""
        message_ascii = [ord(s) for s in message]
        self._arcom.write_array(
            *[
                self.encoded_opcode,
                encode_message(SendMessageHeader.DISPLAY, encoding=ENCODING_UINT8),
                *message_ascii,
            ]
        )

    def _update_param(self, channel, param_name, param_value):
        if param_name in ChannelConfig.model_fields:
            setattr(self.channel_configs[channel], param_name, param_value)
        elif param_name in TriggerConfig.model_fields:
            setattr(self.trigger_configs[channel], param_name, param_value)

    def program_one_param(self, channel=None, param_name=None, param_value=None):
        """Program one channel parameter (one parameter on one channel)."""
        original_value = param_value
        param_name, param_code = resolve_param_name_code_pair(
            param_name_or_code=param_name
        )
        param_dtype = self.param_dtype_lookup.get(param_name)
        param_scaling = PARAM_SCALING.get(param_name)

        if param_name in VOLTAGE_PARAM_NAMES:
            wire_value = volts_to_bytes(volt=param_value, dac_bitMax=self.dac_bitMax)
        else:
            wire_value = param_value * param_scaling

        message = [
            self.encoded_opcode,
            encode_message(SendMessageHeader.PROGRAM_ONE, encoding=ENCODING_UINT8),
            encode_message(param_code, encoding=ENCODING_UINT8),
            encode_message(channel + 1, encoding=ENCODING_UINT8),
            encode_message(wire_value, encoding=param_dtype),
        ]
        self._arcom.write_array(b"".join(message))

        write_ok = self._read_confirmation()
        if write_ok:
            self._update_param(
                channel=channel, param_name=param_name, param_value=original_value
            )

        return write_ok

    def program_trigger_channel(self, trigger_channel=None, trigger_mode=None):
        """"""
        _, trigger_mode_value = resolve_trigger_name_code_pair(
            trigger_name_or_code=trigger_mode
        )
        write_ok = self.program_one_param(
            channel=trigger_channel,
            param_name="triggerMode",
            param_value=trigger_mode_value,
        )
        return write_ok

    def upload_all(self):
        """Program all channel and trigger parameters via individual serial writes.

        Prefer sync_all_params() for faster bulk upload.
        """
        for param_name in ChannelConfig.model_fields:
            for channel in range(self.nr_output_channels):
                param_value = getattr(self.channel_configs[channel], param_name)
                success = self.program_one_param(
                    channel=channel,
                    param_name=param_name,
                    param_value=param_value,
                )
                logging.debug(f"{param_name} ch{channel} = {param_value} ok: {success}")
                if not success:
                    raise ValueError

        for channel in range(self.nr_trigger_channels):
            param_value = self.trigger_configs[channel].triggerMode
            success = self.program_one_param(
                channel=channel,
                param_name="triggerMode",
                param_value=param_value,
            )
            logging.debug(f"triggerMode ch{channel} = {param_value} ok: {success}")
            if not success:
                raise ValueError

    def sync_all_params(self):
        """Upload all parameters in a single bulk serial write (opcode 73).

        Faster than upload_all() which does one serial round trip per parameter.
        Byte layout differs between model 1 and model 2.
        """
        time_param_names = [
            "phase1Duration",
            "interPhaseInterval",
            "phase2Duration",
            "interPulseInterval",
            "burstDuration",
            "interBurstInterval",
            "pulseTrainDuration",
            "pulseTrainDelay",
        ]
        volt_param_names = ["phase1Voltage", "phase2Voltage", "restingVoltage"]

        # 32-bit time parameters: 8 params × 4 channels, interleaved by channel
        program_values_32 = []
        for channel in range(self.nr_output_channels):
            cfg = self.channel_configs[channel]
            for param in time_param_names:
                program_values_32.append(
                    int(getattr(cfg, param) * self.cycle_frequency)
                )

        # Voltage and 8-bit parameters differ by model
        if self.model == 2:
            # 16-bit voltages: 3 volt params × 4 channels
            program_values_16 = []
            for channel in range(self.nr_output_channels):
                cfg = self.channel_configs[channel]
                for param in volt_param_names:
                    program_values_16.append(
                        int(
                            volts_to_bytes(
                                volt=getattr(cfg, param), dac_bitMax=self.dac_bitMax
                            )
                        )
                    )
            # 8-bit params: 4 params × 4 channels
            program_values_8 = []
            for channel in range(self.nr_output_channels):
                cfg = self.channel_configs[channel]
                program_values_8.append(int(cfg.isBiphasic))
                program_values_8.append(int(cfg.customTrainID))
                program_values_8.append(int(cfg.customTrainTarget))
                program_values_8.append(int(cfg.customTrainLoop))
        else:  # model 1: voltages are uint8 and packed into the 8-bit section
            program_values_16 = None
            program_values_8 = []
            for channel in range(self.nr_output_channels):
                cfg = self.channel_configs[channel]
                program_values_8.append(int(cfg.isBiphasic))
                v2b = lambda v: int(volts_to_bytes(volt=v, dac_bitMax=self.dac_bitMax))  # noqa: E731
                program_values_8.append(v2b(cfg.phase1Voltage))
                program_values_8.append(v2b(cfg.phase2Voltage))
                program_values_8.append(int(cfg.customTrainID))
                program_values_8.append(int(cfg.customTrainTarget))
                program_values_8.append(int(cfg.customTrainLoop))
                program_values_8.append(v2b(cfg.restingVoltage))

        # Trigger link params: linkTriggerChannel1 per channel, then linkTriggerChannel2
        program_values_tl = [
            int(self.channel_configs[ch].linkTriggerChannel1)
            for ch in range(self.nr_output_channels)
        ] + [
            int(self.channel_configs[ch].linkTriggerChannel2)
            for ch in range(self.nr_output_channels)
        ]

        # Trigger modes for all trigger channels
        trigger_modes = [
            int(self.trigger_configs[ch].triggerMode)
            for ch in range(self.nr_trigger_channels)
        ]

        message = [
            self.encoded_opcode,
            encode_message(SendMessageHeader.PROGRAM_ALL, encoding=ENCODING_UINT8),
            encode_message(program_values_32, encoding="uint32"),
        ]
        if program_values_16 is not None:
            message.append(encode_message(program_values_16, encoding="uint16"))
        message += [
            encode_message(program_values_8, encoding=ENCODING_UINT8),
            encode_message(program_values_tl, encoding=ENCODING_UINT8),
            encode_message(trigger_modes, encoding=ENCODING_UINT8),
        ]
        self._arcom.write_array(b"".join(message))
        return self._read_confirmation()

    def set_resting_voltage(self, channel=None, voltage=None):
        """Convenience function to set restingVoltage parameter on one channel.

        :param channel:
        :param voltage:
        :return:
        """
        return self.program_one_param(
            channel=channel,
            param_name="restingVoltage",
            param_value=voltage,
        )

    def set_fixed_voltage(self, channel=None, voltage=None):
        """Set a channel to a fixed DC voltage immediately, outside of any pulse train.

        :param channel: 0-indexed output channel
        :param voltage: target voltage in volts [-10, 10]
        """
        voltage_bits = volts_to_bytes(volt=voltage, dac_bitMax=self.dac_bitMax)
        if self.model == 1:
            message = [
                self.encoded_opcode,
                encode_message(SendMessageHeader.PROGRAM_VOLT, encoding=ENCODING_UINT8),
                encode_message(channel + 1, encoding=ENCODING_UINT8),
                encode_message(voltage_bits, encoding=ENCODING_UINT8),
            ]
        else:
            message = [
                self.encoded_opcode,
                encode_message(SendMessageHeader.PROGRAM_VOLT, encoding=ENCODING_UINT8),
                encode_message(channel + 1, encoding=ENCODING_UINT8),
                encode_message(voltage_bits, encoding="uint16"),
            ]
        self._arcom.write_array(b"".join(message))
        return self._read_confirmation()

    def upload_custom_pulse_train(
        self, pulse_train_id=None, pulse_times=None, pulse_voltages=None
    ):
        """"""
        if pulse_train_id not in (0, 1):
            raise ValueError(f"pulse_train_id must be 0 or 1, got {pulse_train_id}")
        if len(pulse_times) != len(pulse_voltages):
            raise ValueError("pulse_times and pulse_voltages must have the same length")

        scaled_pulse_times = []
        scaled_pulse_voltages = []
        for pulse_time, pulse_voltage in zip(pulse_times, pulse_voltages):
            scaled_pulse_times.append(pulse_time * self.cycle_frequency)
            scaled_pulse_voltages.append(
                volts_to_bytes(volt=pulse_voltage, dac_bitMax=self.dac_bitMax)
            )

        message = [
            self.encoded_opcode,
            encode_message(
                CUSTOM_PULSE_TRAIN_OPCODES.get(pulse_train_id),
                encoding=ENCODING_UINT8,
            ),
        ]
        if self.model == 1:
            message.append(encode_message(0, encoding=ENCODING_UINT8))
        message += [
            encode_message(len(scaled_pulse_times), encoding="uint32"),
            encode_message(scaled_pulse_times, encoding="uint32"),
            encode_message(
                scaled_pulse_voltages,
                encoding=self.param_dtype_lookup.get("phase1Voltage"),
            ),
        ]
        self._arcom.write_array(b"".join(message))
        return self._read_confirmation()

    def upload_custom_waveform(
        self, pulse_train_id=None, pulse_width=None, pulse_voltages=None
    ):
        """"""
        if pulse_train_id not in (0, 1):
            raise ValueError(f"pulse_train_id must be 0 or 1, got {pulse_train_id}")

        scaled_pulse_times = []
        scaled_pulse_voltages = []
        for pulse_index, pulse_voltage in enumerate(pulse_voltages):
            pulse_time = pulse_index * pulse_width * self.cycle_frequency
            scaled_pulse_times.append(pulse_time)
            scaled_pulse_voltages.append(
                volts_to_bytes(volt=pulse_voltage, dac_bitMax=self.dac_bitMax)
            )

        message = [
            self.encoded_opcode,
            encode_message(
                CUSTOM_PULSE_TRAIN_OPCODES.get(pulse_train_id),
                encoding=ENCODING_UINT8,
            ),
        ]
        if self.model == 1:
            message.append(encode_message(0, encoding=ENCODING_UINT8))
        message += [
            encode_message(len(scaled_pulse_times), encoding="uint32"),
            encode_message(scaled_pulse_times, encoding="uint32"),
            encode_message(
                scaled_pulse_voltages,
                encoding=self.param_dtype_lookup.get("phase1Voltage"),
            ),
        ]
        self._arcom.write_array(b"".join(message))
        return self._read_confirmation()

    def set_continuous(self, channel=None, state=None):
        """"""
        message = [
            self.encoded_opcode,
            encode_message(SendMessageHeader.CONTINUOUS, encoding=ENCODING_UINT8),
            encode_message(channel, encoding=ENCODING_UINT8),
            encode_message(state, encoding=ENCODING_UINT8),
        ]
        self._arcom.write_array(b"".join(message))
        return self._read_confirmation()

    def set_logic(self, channel=None, level=None):
        """Set Arduino digital logic level on an output channel (model 2, opcode 86).

        :param channel: 0-indexed output channel
        :param level: logic level (0 or 1)
        """
        message = [
            self.encoded_opcode,
            encode_message(SendMessageHeader.LOGIC_SET, encoding=ENCODING_UINT8),
            encode_message(channel + 1, encoding=ENCODING_UINT8),
            encode_message(level, encoding=ENCODING_UINT8),
        ]
        self._arcom.write_array(b"".join(message))
        return self._read_confirmation()

    def get_logic(self, channel=None):
        """Read current Arduino digital logic level on an output channel (opcode 87).

        :param channel: 0-indexed output channel
        :return: logic level (0 or 1)
        """
        message = [
            self.encoded_opcode,
            encode_message(SendMessageHeader.LOGIC_GET, encoding=ENCODING_UINT8),
            encode_message(channel + 1, encoding=ENCODING_UINT8),
        ]
        self._arcom.write_array(b"".join(message))
        return self._arcom.read_uint8()

    def trigger_selected_channels(
        self,
        channel_1=False,
        channel_2=False,
        channel_3=False,
        channel_4=False,
    ):
        """Trigger specific channels

        :param channel_1:
        :param channel_2:
        :param channel_3:
        :param channel_4:
        :return:
        """
        combination_byte = (
            (1 * channel_1) + (2 * channel_2) + (4 * channel_3) + (8 * channel_4)
        )
        message = [
            self.encoded_opcode,
            encode_message(SendMessageHeader.SOFT_TRIGGER, encoding=ENCODING_UINT8),
            encode_message(combination_byte, encoding=ENCODING_UINT8),
        ]
        self._arcom.write_array(b"".join(message))

    def trigger_all_channels(self):
        return self.trigger_selected_channels(
            channel_1=True, channel_2=True, channel_3=True, channel_4=True
        )

    def stop_all_outputs(self):
        """"""
        message = [
            self.encoded_opcode,
            encode_message(SendMessageHeader.ABORT_ALL, encoding=ENCODING_UINT8),
        ]
        self._arcom.write_array(b"".join(message))
        return self._read_confirmation()

    def save_settings(self):
        """"""
        if self._arcom is None:
            return False
        message = [
            self.encoded_opcode,
            encode_message(SendMessageHeader.DISCONNECT, encoding=ENCODING_UINT8),
        ]
        self._arcom.write_array(b"".join(message))
        return self._read_confirmation()  # fixme: returns False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_settings()
        if self._arcom is not None:
            self._arcom.close()

    def __del__(self):
        self.save_settings()
        if self._arcom is not None:
            self._arcom.close()
