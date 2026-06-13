import contextlib
import logging
import struct
import time
from typing import Any

from pypulsepal._arcom import ArCOM
from pypulsepal.definitions import (
    CUSTOM_PULSE_TRAIN_OPCODES,
    PARAM_DTYPE_MODEL_1,
    PARAM_DTYPE_MODEL_2,
    PARAM_SCALING,
    PULSEPAL_CYCLE_FREQUENCY,
    TRIGGER_MODE_NAMES,
    VOLTAGE_PARAM_NAMES,
    ReceiveMessageHeader,
    SendMessageHeader,
    resolve_param_name_code_pair,
)
from pypulsepal.models import ChannelConfig, PulsePalConfig, TriggerConfig
from pypulsepal.utils import encode_message, volts_to_bytes

ENCODING_UINT8 = "uint8"


class PulsePalError(Exception):
    """Convenience error object for PulsePal"""

    pass


class PulsePal:
    """Python interface for the PulsePal open-source pulse train generator.

    Connects to PulsePal hardware over serial and provides methods for
    configuring output channels, uploading pulse trains, and triggering outputs.

    Example:
        >>> pp = PulsePal("/dev/ttyACM0")
        >>> pp.channel_configs[0].phase1_duration = 0.001
        >>> pp.sync_all_params()
        >>> pp.trigger_all_channels()
        >>> pp.save_settings()
    """

    # communication
    _arcom: Any = None
    serial_port: str | None = None
    baudrate: int = 115200

    # hardware attributes
    firmware_version: int | None = None
    model: int | None = None
    dac_bitMax: int | None = None
    cycle_frequency: int = 20000
    nr_output_channels: int = 4
    nr_trigger_channels: int = 2
    opcode: int = 213
    param_dtype_lookup: Any = None

    def __init__(
        self,
        serial_port: str | None = None,
        baudrate: int = 115200,
        cycle_frequency: int = PULSEPAL_CYCLE_FREQUENCY,
        nr_output_channels: int = 4,
        nr_trigger_channels: int = 2,
        opcode: int = 213,
        **kwargs: Any,
    ):
        """Connect to PulsePal hardware over serial.

        Args:
            serial_port: Serial port path (e.g. ``/dev/ttyACM0``, ``COM3``).
                If ``None``, the object is constructed but not connected.
            baudrate: Serial baud rate.
            cycle_frequency: Hardware cycle frequency in Hz.
            nr_output_channels: Number of output channels.
            nr_trigger_channels: Number of trigger channels.
            **kwargs: Additional keyword arguments (ignored).
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

        if serial_port is not None:
            self.connect(serial_port=serial_port, baudrate=baudrate)

    @property
    def config(self) -> PulsePalConfig:
        """Current channel and trigger configs as a PulsePalConfig snapshot."""
        return PulsePalConfig(
            channels={i + 1: ch for i, ch in enumerate(self.channel_configs)},
            triggers={i + 1: tr for i, tr in enumerate(self.trigger_configs)},
        )

    @classmethod
    def from_config(
        cls, config: PulsePalConfig, serial_port: str, **kwargs
    ) -> "PulsePal":
        """Construct a connected PulsePal with the given config pre-loaded and synced.

        Args:
            config: Device configuration to apply immediately after connecting.
            serial_port: Serial port path (e.g. ``/dev/ttyACM0``, ``COM3``).
            **kwargs: Forwarded to the constructor.

        Returns:
            Connected PulsePal instance with all parameters synced to hardware.
        """
        instance = cls(serial_port=serial_port, **kwargs)
        instance.channel_configs = [
            config.channels.get(i + 1, ChannelConfig()).model_copy()
            for i in range(instance.nr_output_channels)
        ]
        instance.trigger_configs = [
            config.triggers.get(i + 1, TriggerConfig()).model_copy()
            for i in range(instance.nr_trigger_channels)
        ]
        instance.sync_all_params()
        return instance

    def load_config(self, path) -> None:
        """Load channel/trigger configs from a JSON or YAML file and apply in memory."""
        from pypulsepal.config_io import load_config

        cfg = load_config(path)
        self.channel_configs = [
            cfg.channels.get(i + 1, ChannelConfig()).model_copy()
            for i in range(self.nr_output_channels)
        ]
        self.trigger_configs = [
            cfg.triggers.get(i + 1, TriggerConfig()).model_copy()
            for i in range(self.nr_trigger_channels)
        ]

    def save_config(self, path) -> None:
        """Save current channel/trigger configs to a JSON or YAML file."""
        from pypulsepal.config_io import save_config

        save_config(self.config, path)

    def reset_to_defaults(self) -> None:
        """Reset all channel and trigger configs to factory defaults and sync to hardware."""
        self.channel_configs = [ChannelConfig() for _ in range(self.nr_output_channels)]
        self.trigger_configs = [
            TriggerConfig() for _ in range(self.nr_trigger_channels)
        ]
        self.sync_all_params()

    @property
    def encoded_opcode(self):
        """The handshake opcode byte encoded for serial transmission."""
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

        Returns:
            True if handshake succeeded.
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

    def connect(
        self, serial_port: str, baudrate: int = 115200, timeout: float = 1
    ) -> "PulsePal":
        """Connect to hardware and perform handshake.

        Args:
            serial_port: Serial port path (e.g. ``/dev/ttyACM0``, ``COM3``).
            baudrate: Serial baud rate.
            timeout: Serial read timeout in seconds.

        Returns:
            Self, for method chaining.
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
        self._pulsepal_set_display(
            row1="PulsePal", row2=f"Python fw{self.firmware_version}"
        )
        return self

    def _pulsepal_set_display(self, row1: str = "", row2: str = "") -> None:
        """Set PulsePal LCD display text (opcode 78). Each row is max 16 chars."""
        if self._arcom is None:
            return

        def _row(s: str) -> bytes:
            b = s[:16].encode("ascii")
            return bytes([len(b)]) + b + b" " * (16 - len(b))

        msg = (
            self.encoded_opcode
            + encode_message(SendMessageHeader.DISPLAY, encoding=ENCODING_UINT8)
            + _row(row1)
            + _row(row2)
        )
        self._arcom.write_array(msg)

    def _update_param(self, channel, param_name, param_value):
        """Write a confirmed hardware value back into the in-memory config objects."""
        if param_name in ChannelConfig.model_fields:
            setattr(self.channel_configs[channel], param_name, param_value)
        elif param_name in TriggerConfig.model_fields:
            setattr(self.trigger_configs[channel], param_name, param_value)

    def program_one_param(self, channel=None, param_name=None, param_value=None):
        """Send a single parameter update to hardware and mirror it in the in-memory config.

        Args:
            channel: 0-indexed channel number.
            param_name: Parameter name string (e.g. ``"phase1Voltage"``) or integer code.
            param_value: Value in natural units (volts or seconds); scaling to wire format
                is applied internally.

        Returns:
            True if hardware acknowledged the write.
        """
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
        """Set the trigger mode for one trigger input channel.

        Args:
            trigger_channel: 0-indexed trigger channel number.
            trigger_mode: Mode as an integer (0 normal, 1 toggle, 2 gated) or the
                equivalent string (``"normal"``, ``"toggle"``, ``"gated"``).

        Returns:
            True if hardware acknowledged the write.
        """
        if isinstance(trigger_mode, str):
            mode_value = TRIGGER_MODE_NAMES.get(trigger_mode)
            if mode_value is None:
                raise ValueError(
                    f"Unknown trigger mode {trigger_mode!r}; valid: {list(TRIGGER_MODE_NAMES)}"
                )
        else:
            mode_value = int(trigger_mode)
        write_ok = self.program_one_param(
            channel=trigger_channel,
            param_name="triggerMode",
            param_value=mode_value,
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

            def v2b(v: float) -> int:
                return int(volts_to_bytes(volt=v, dac_bitMax=self.dac_bitMax))

            for channel in range(self.nr_output_channels):
                cfg = self.channel_configs[channel]
                program_values_8.append(int(cfg.isBiphasic))
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

    def set_resting_voltage(self, channel: int, voltage: float) -> bool:
        """Set the resting (idle) voltage on one output channel.

        Args:
            channel: 0-indexed output channel.
            voltage: Resting voltage in volts.

        Returns:
            True if hardware acknowledged the write.
        """
        return self.program_one_param(
            channel=channel,
            param_name="restingVoltage",
            param_value=voltage,
        )

    def set_fixed_voltage(self, channel: int, voltage: float) -> bool:
        """Set a channel to a fixed DC voltage immediately, outside of any pulse train.

        Args:
            channel: 0-indexed output channel.
            voltage: Target voltage in volts (range: -10 to +10 V).

        Returns:
            True if hardware acknowledged the write.
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
        self,
        pulse_train_id: int,
        pulse_times: list[float],
        pulse_voltages: list[float],
    ) -> bool:
        """Upload a custom pulse train to hardware slot 0 or 1.

        Args:
            pulse_train_id: Slot index, 0 or 1.
            pulse_times: Pulse onset times in seconds.
            pulse_voltages: Output voltages in volts for each pulse.

        Returns:
            True if hardware acknowledged the upload.
        """
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
        self,
        pulse_train_id: int,
        pulse_width: float,
        pulse_voltages: list[float],
    ) -> bool:
        """Upload an evenly-spaced waveform to hardware slot 0 or 1.

        Args:
            pulse_train_id: Slot index, 0 or 1.
            pulse_width: Inter-sample interval in seconds.
            pulse_voltages: Output voltages in volts for each sample.

        Returns:
            True if hardware acknowledged the upload.
        """
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

    def set_continuous(self, channel: int, state: int) -> bool:
        """Enable or disable continuous output mode on one channel.

        Args:
            channel: 0-indexed output channel.
            state: 1 to enable continuous output, 0 to disable.

        Returns:
            True if hardware acknowledged the write.
        """
        message = [
            self.encoded_opcode,
            encode_message(SendMessageHeader.CONTINUOUS, encoding=ENCODING_UINT8),
            encode_message(channel + 1, encoding=ENCODING_UINT8),
            encode_message(state, encoding=ENCODING_UINT8),
        ]
        self._arcom.write_array(b"".join(message))
        return self._read_confirmation()

    def set_logic(self, channel: int, level: int) -> bool:
        """Set Arduino digital logic level on an output channel (model 2, opcode 86).

        Args:
            channel: 0-indexed output channel.
            level: Logic level — 0 or 1.
        """
        message = [
            self.encoded_opcode,
            encode_message(SendMessageHeader.LOGIC_SET, encoding=ENCODING_UINT8),
            encode_message(channel + 1, encoding=ENCODING_UINT8),
            encode_message(level, encoding=ENCODING_UINT8),
        ]
        self._arcom.write_array(b"".join(message))
        return self._read_confirmation()

    def get_logic(self, channel: int) -> int:
        """Read current Arduino digital logic level on an output channel (opcode 87).

        Args:
            channel: 0-indexed output channel.

        Returns:
            Logic level — 0 or 1.
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
        channel_1: bool = False,
        channel_2: bool = False,
        channel_3: bool = False,
        channel_4: bool = False,
    ) -> None:
        """Software-trigger specific output channels.

        Args:
            channel_1: Trigger channel 1.
            channel_2: Trigger channel 2.
            channel_3: Trigger channel 3.
            channel_4: Trigger channel 4.
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
        """Software-trigger all four output channels simultaneously."""
        return self.trigger_selected_channels(
            channel_1=True, channel_2=True, channel_3=True, channel_4=True
        )

    def stop_all_outputs(self):
        """Abort all currently running pulse train outputs."""
        message = [
            self.encoded_opcode,
            encode_message(SendMessageHeader.ABORT_ALL, encoding=ENCODING_UINT8),
        ]
        self._arcom.write_array(b"".join(message))

    def save_settings(self) -> bool:
        """Send disconnect opcode (81) to save current params on device.

        Firmware sends no ack byte for this opcode — confirmed on model 2 fw21.
        Returns False if not connected or port is closed.
        """
        if self._arcom is None:
            return False
        try:
            if not self._arcom.serial_object.isOpen():
                return False
        except Exception:
            return False
        message = [
            self.encoded_opcode,
            encode_message(SendMessageHeader.DISCONNECT, encoding=ENCODING_UINT8),
        ]
        self._arcom.write_array(b"".join(message))
        return True

    def save_to_sd(self, filename: str = "default.pps") -> None:
        """Save current RAM params to SD card (opcode 90, op 1).

        Firmware sends no ack byte — do not read confirmation.
        A 100ms sleep is inserted to allow SD write to complete.
        """
        if self._arcom is None:
            return
        name_bytes = filename.encode("ascii")
        msg = (
            self.encoded_opcode
            + encode_message(SendMessageHeader.SETTINGS, encoding=ENCODING_UINT8)
            + encode_message(1, encoding=ENCODING_UINT8)
            + encode_message(len(name_bytes), encoding=ENCODING_UINT8)
            + name_bytes
        )
        self._arcom.serial_object.write(msg)
        time.sleep(0.1)

    def read_sd_params(self) -> dict | None:
        """Read 178-byte SD parameter file via opcode 85 and parse to a dict.

        Returns None if the firmware returns an unexpected byte count.
        Keys match ChannelConfig field names; 'triggerAddress' is firmware-only
        (4-element list of output channel link flags per trigger channel).

        SD byte layout — per output channel ×4 (42 bytes each):
          8× uint32  phase1Duration, interPhaseInterval, phase2Duration,
                     interPulseInterval, burstDuration, interBurstInterval,
                     pulseTrainDuration, pulseTrainDelay  (firmware cycles ÷ 20000 = s)
          1× uint8   isBiphasic
          3× uint16  phase1Voltage, phase2Voltage, restingVoltage  (0–65535 → ±10V)
          3× uint8   customTrainID, customTrainTarget, customTrainLoop
        Per trigger channel ×2 (5 bytes each):
          1× uint8   triggerMode
          4× uint8   triggerAddress[0..3]
        Total: 4×42 + 2×5 = 178 bytes
        """
        if self._arcom is None:
            return None
        msg = self.encoded_opcode + encode_message(
            SendMessageHeader.READ_SD, encoding=ENCODING_UINT8
        )
        self._arcom.serial_object.write(msg)
        time.sleep(0.1)
        raw = self._arcom.serial_object.read(178)

        if len(raw) != 178:
            return None

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
        result: dict = {n: [] for n in time_names}
        for n in ("phase1Voltage", "phase2Voltage", "restingVoltage"):
            result[n] = []
        for n in (
            "isBiphasic",
            "customTrainID",
            "customTrainTarget",
            "customTrainLoop",
        ):
            result[n] = []
        result["triggerMode"] = []
        result["triggerAddress"] = []

        offset = 0
        for _ in range(4):
            for name in time_names:
                (cycles,) = struct.unpack_from("<I", raw, offset)
                result[name].append(cycles / PULSEPAL_CYCLE_FREQUENCY)
                offset += 4
            result["isBiphasic"].append(raw[offset])
            offset += 1
            for name in ("phase1Voltage", "phase2Voltage", "restingVoltage"):
                (bits,) = struct.unpack_from("<H", raw, offset)
                result[name].append(round((bits / 65535.0) * 20.0 - 10.0, 4))
                offset += 2
            result["customTrainID"].append(raw[offset])
            result["customTrainTarget"].append(raw[offset + 1])
            result["customTrainLoop"].append(raw[offset + 2])
            offset += 3

        for _ in range(2):
            result["triggerMode"].append(raw[offset])
            result["triggerAddress"].append(list(raw[offset + 1 : offset + 5]))
            offset += 5

        return result

    def close(self) -> None:
        """Save settings to device and close the serial connection."""
        self.save_settings()
        if self._arcom is not None:
            self._arcom.close()
            self._arcom = None

    def __enter__(self):
        """Return self to support use as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Save settings and close the serial connection on context exit."""
        self.close()

    def __del__(self):
        with contextlib.suppress(Exception):
            self.close()
