import contextlib
import logging
import struct
import time
from collections.abc import Sequence
from typing import Any

from pypulsepal._arcom import ArCOM
from pypulsepal.definitions import (
    CLIENT_NAME,
    CUSTOM_PULSE_TRAIN_OPCODES,
    DAC_MAX,
    MODEL_2_MIN_FIRMWARE,
    PARAM_DTYPES,
    PARAM_SCALING,
    PULSEPAL_CYCLE_FREQUENCY,
    SD_SAVE,
    TIME_PARAMS,
    TRIGGER_MODE_NAMES,
    VOLTAGE_PARAM_NAMES,
    VOLTAGE_PARAMS,
    ReceiveMessageHeader,
    SendMessageHeader,
    resolve_param_name_code_pair,
)
from pypulsepal.models import ChannelConfig, PulsePalConfig, TriggerConfig
from pypulsepal.utils import V_MIN, V_SPAN, encode_message, volts_to_dac

log = logging.getLogger(__name__)


def _u8(value) -> bytes:
    return encode_message(value, encoding="uint8")


def _u16(value) -> bytes:
    return encode_message(value, encoding="uint16")


def _u32(value) -> bytes:
    return encode_message(value, encoding="uint32")


class PulsePalError(Exception):
    """Raised when a PulsePal does not answer the handshake."""


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

    # serial link
    _arcom: Any = None
    serial_port: str | None = None
    baudrate: int = 115200

    # filled in by the handshake
    firmware_version: int | None = None
    model: int | None = None
    dac_max: int | None = None
    param_dtype_lookup: Any = None

    # device layout and framing
    cycle_frequency: int = PULSEPAL_CYCLE_FREQUENCY
    nr_output_channels: int = 4
    nr_trigger_channels: int = 2
    opcode: int = 213

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
            opcode: Prefix byte that starts every message.
            **kwargs: Overrides for other existing attributes; unknown names are ignored.
        """
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.cycle_frequency = cycle_frequency
        self.nr_output_channels = nr_output_channels
        self.nr_trigger_channels = nr_trigger_channels
        self.opcode = opcode

        self.channel_configs = [ChannelConfig() for _ in range(nr_output_channels)]
        self.trigger_configs = [TriggerConfig() for _ in range(nr_trigger_channels)]

        for name, value in kwargs.items():
            if hasattr(self, name):
                setattr(self, name, value)

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

    # ------------------------------------------------------------------
    # framing
    # ------------------------------------------------------------------

    @property
    def encoded_opcode(self) -> bytes:
        """The prefix byte that starts every message, packed for the wire."""
        return _u8(self.opcode)

    @encoded_opcode.setter
    def encoded_opcode(self, value=None):
        self.opcode = value

    @property
    def _voltage_dtype(self) -> str:
        return "uint8" if self.model == 1 else "uint16"

    def _frame(self, opcode: int, *fields: bytes) -> bytes:
        """Prefix byte, opcode byte, then the already packed fields."""
        return self.encoded_opcode + _u8(opcode) + b"".join(fields)

    def _send(self, opcode: int, *fields: bytes) -> None:
        self._arcom.write_array(self._frame(opcode, *fields))

    def _send_and_confirm(self, opcode: int, *fields: bytes) -> bool:
        self._send(opcode, *fields)
        return self._read_confirmation()

    def _clear_read_queue(self) -> bytes:
        """Read and discard whatever is waiting in the serial input buffer."""
        port = self._arcom.serial_object
        return port.read(port.inWaiting())

    def _read_confirmation(self) -> bool:
        """Read one reply byte; True if it is the acknowledge value."""
        return self._arcom.read_uint8() == ReceiveMessageHeader.ACK

    # ------------------------------------------------------------------
    # connection
    # ------------------------------------------------------------------

    def _pulsepal_handshake(self) -> bool:
        """Handshake, detect the hardware model from the firmware build, send the client name.

        Returns:
            True if the device answered with the handshake acknowledge.
        """
        self._arcom.serial_object.write(
            self.encoded_opcode + SendMessageHeader.HANDSHAKE.encode("ascii")
        )
        reply = self._arcom.read_char()
        firmware_version = self._arcom.read_uint32()
        self._clear_read_queue()
        if reply != ReceiveMessageHeader.HANDSHAKE_OK:
            return False

        self.firmware_version = firmware_version
        self.model = 2 if firmware_version >= MODEL_2_MIN_FIRMWARE else 1
        self.dac_max = DAC_MAX[self.model]
        self.param_dtype_lookup = PARAM_DTYPES[self.model]
        self._send(SendMessageHeader.CLIENT_ID, CLIENT_NAME)
        return True

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
        if not self._pulsepal_handshake():
            raise PulsePalError(
                f"No handshake from a PulsePal at '{serial_port}' (baudrate {baudrate})"
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

        self._send(SendMessageHeader.DISPLAY, _row(row1), _row(row2))

    # ------------------------------------------------------------------
    # parameters
    # ------------------------------------------------------------------

    def _update_param(self, channel, param_name, param_value):
        """Write a confirmed hardware value back into the in-memory config objects."""
        if param_name in ChannelConfig.model_fields:
            setattr(self.channel_configs[channel], param_name, param_value)
        elif param_name in TriggerConfig.model_fields:
            setattr(self.trigger_configs[channel], param_name, param_value)

    def _dac(self, volts: float) -> int:
        if self.dac_max is None:
            raise PulsePalError("DAC range unknown: connect to a PulsePal first")
        return volts_to_dac(volts, self.dac_max)

    def _to_wire(self, param_name: str, value):
        if param_name in VOLTAGE_PARAM_NAMES:
            return self._dac(value)
        return value * PARAM_SCALING[param_name]

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
        name, code = resolve_param_name_code_pair(param_name_or_code=param_name)
        value = encode_message(
            self._to_wire(name, param_value), encoding=self.param_dtype_lookup[name]
        )
        ok = self._send_and_confirm(
            SendMessageHeader.PROGRAM_ONE, _u8(code), _u8(channel + 1), value
        )
        if ok:
            self._update_param(
                channel=channel, param_name=name, param_value=param_value
            )
        return ok

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
            if trigger_mode not in TRIGGER_MODE_NAMES:
                raise ValueError(
                    f"Unknown trigger mode {trigger_mode!r}; valid: {list(TRIGGER_MODE_NAMES)}"
                )
            trigger_mode = TRIGGER_MODE_NAMES[trigger_mode]
        return self.program_one_param(
            channel=trigger_channel,
            param_name="triggerMode",
            param_value=int(trigger_mode),
        )

    def upload_all(self):
        """Program all channel and trigger parameters via individual serial writes.

        Prefer sync_all_params() for faster bulk upload.

        Raises:
            ValueError: if the device does not acknowledge a write.
        """
        writes = [
            (channel, name, getattr(self.channel_configs[channel], name))
            for name in ChannelConfig.model_fields
            for channel in range(self.nr_output_channels)
        ]
        writes += [
            (channel, "triggerMode", self.trigger_configs[channel].triggerMode)
            for channel in range(self.nr_trigger_channels)
        ]
        for channel, name, value in writes:
            ok = self.program_one_param(
                channel=channel, param_name=name, param_value=value
            )
            log.debug("program %s on channel %d = %r: ok=%s", name, channel, value, ok)
            if not ok:
                raise ValueError(
                    f"PulsePal did not acknowledge {name} on channel {channel}"
                )

    def sync_all_params(self):
        """Upload all parameters in a single bulk serial write (opcode 73).

        Faster than upload_all() which does one serial round trip per parameter.
        Byte layout differs between model 1 and model 2.
        """
        channels = [self.channel_configs[i] for i in range(self.nr_output_channels)]
        triggers = [self.trigger_configs[i] for i in range(self.nr_trigger_channels)]

        cycles = [
            int(getattr(cfg, name) * self.cycle_frequency)
            for cfg in channels
            for name in TIME_PARAMS
        ]
        if self.model == 2:
            voltages = _u16(
                [
                    self._dac(getattr(cfg, name))
                    for cfg in channels
                    for name in VOLTAGE_PARAMS
                ]
            )
            per_channel = [
                (
                    cfg.isBiphasic,
                    cfg.customTrainID,
                    cfg.customTrainTarget,
                    cfg.customTrainLoop,
                )
                for cfg in channels
            ]
        else:
            # model 1 carries its 8-bit voltages inside the per-channel byte group
            voltages = b""
            per_channel = [
                (
                    cfg.isBiphasic,
                    self._dac(cfg.phase1Voltage),
                    self._dac(cfg.phase2Voltage),
                    cfg.customTrainID,
                    cfg.customTrainTarget,
                    cfg.customTrainLoop,
                    self._dac(cfg.restingVoltage),
                )
                for cfg in channels
            ]
        channel_bytes = [int(value) for group in per_channel for value in group]
        links = [int(cfg.linkTriggerChannel1) for cfg in channels]
        links += [int(cfg.linkTriggerChannel2) for cfg in channels]
        modes = [int(trigger.triggerMode) for trigger in triggers]

        return self._send_and_confirm(
            SendMessageHeader.PROGRAM_ALL,
            _u32(cycles),
            voltages,
            _u8(channel_bytes + links + modes),
        )

    def set_resting_voltage(self, channel: int, voltage: float) -> bool:
        """Set the resting (idle) voltage on one output channel.

        Args:
            channel: 0-indexed output channel.
            voltage: Resting voltage in volts.

        Returns:
            True if hardware acknowledged the write.
        """
        return self.program_one_param(
            channel=channel, param_name="restingVoltage", param_value=voltage
        )

    def set_fixed_voltage(self, channel: int, voltage: float) -> bool:
        """Set a channel to a fixed DC voltage immediately, outside of any pulse train.

        Args:
            channel: 0-indexed output channel.
            voltage: Target voltage in volts (range: -10 to +10 V).

        Returns:
            True if hardware acknowledged the write.
        """
        level = encode_message(self._dac(voltage), encoding=self._voltage_dtype)
        return self._send_and_confirm(
            SendMessageHeader.PROGRAM_VOLT, _u8(channel + 1), level
        )

    # ------------------------------------------------------------------
    # custom trains
    # ------------------------------------------------------------------

    def upload_custom_pulse_train(
        self,
        pulse_train_id: int,
        pulse_times: Sequence[float],
        pulse_voltages: Sequence[float],
    ) -> bool:
        """Upload a custom pulse train to hardware slot 0 or 1.

        Args:
            pulse_train_id: Slot index, 0 or 1.
            pulse_times: Pulse onset times in seconds.
            pulse_voltages: Output voltages in volts for each pulse.

        Returns:
            True if hardware acknowledged the upload.
        """
        if pulse_train_id not in CUSTOM_PULSE_TRAIN_OPCODES:
            raise ValueError(f"pulse_train_id must be 0 or 1, got {pulse_train_id}")
        if len(pulse_times) != len(pulse_voltages):
            raise ValueError("pulse_times and pulse_voltages must have the same length")

        onsets = [t * self.cycle_frequency for t in pulse_times]
        levels = [self._dac(v) for v in pulse_voltages]
        # model 1 firmware reads one spare byte before the pulse count
        spare = _u8(0) if self.model == 1 else b""
        return self._send_and_confirm(
            CUSTOM_PULSE_TRAIN_OPCODES[pulse_train_id],
            spare,
            _u32(len(onsets)),
            _u32(onsets),
            encode_message(levels, encoding=self._voltage_dtype),
        )

    def upload_custom_waveform(
        self,
        pulse_train_id: int,
        pulse_width: float,
        pulse_voltages: Sequence[float],
    ) -> bool:
        """Upload an evenly-spaced waveform to hardware slot 0 or 1.

        Sample ``i`` starts at ``i * pulse_width``; the upload is a custom pulse train.

        Args:
            pulse_train_id: Slot index, 0 or 1.
            pulse_width: Inter-sample interval in seconds.
            pulse_voltages: Output voltages in volts for each sample.

        Returns:
            True if hardware acknowledged the upload.
        """
        voltages = list(pulse_voltages)
        onsets = [i * pulse_width for i in range(len(voltages))]
        return self.upload_custom_pulse_train(pulse_train_id, onsets, voltages)

    # ------------------------------------------------------------------
    # output control
    # ------------------------------------------------------------------

    def set_continuous(self, channel: int, state: int) -> bool:
        """Enable or disable continuous output mode on one channel.

        Args:
            channel: 0-indexed output channel.
            state: 1 to enable continuous output, 0 to disable.

        Returns:
            True if hardware acknowledged the write.
        """
        return self._send_and_confirm(
            SendMessageHeader.CONTINUOUS, _u8(channel + 1), _u8(state)
        )

    def set_logic(self, channel: int, level: int) -> bool:
        """Set Arduino digital logic level on an output channel (model 2, opcode 86).

        Args:
            channel: 0-indexed output channel.
            level: Logic level: 0 or 1.
        """
        return self._send_and_confirm(
            SendMessageHeader.LOGIC_SET, _u8(channel + 1), _u8(level)
        )

    def get_logic(self, channel: int) -> int:
        """Read current Arduino digital logic level on an output channel (opcode 87).

        Args:
            channel: 0-indexed output channel.

        Returns:
            Logic level: 0 or 1.
        """
        self._send(SendMessageHeader.LOGIC_GET, _u8(channel + 1))
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
        selected = (channel_1, channel_2, channel_3, channel_4)
        mask = 0
        for bit, on in enumerate(selected):
            if on:
                mask |= 1 << bit
        self._send(SendMessageHeader.SOFT_TRIGGER, _u8(mask))

    def trigger_all_channels(self):
        """Software-trigger all four output channels simultaneously."""
        return self.trigger_selected_channels(True, True, True, True)

    def stop_all_outputs(self):
        """Abort all currently running pulse train outputs."""
        self._send(SendMessageHeader.ABORT_ALL)

    # ------------------------------------------------------------------
    # storage
    # ------------------------------------------------------------------

    def save_settings(self) -> bool:
        """Send disconnect opcode (81) to save current params on device.

        Firmware sends no ack byte for this opcode: confirmed on model 2 fw21.
        Returns False if not connected or port is closed.
        """
        if self._arcom is None:
            return False
        try:
            if not self._arcom.serial_object.isOpen():
                return False
        except Exception:
            return False
        self._send(SendMessageHeader.DISCONNECT)
        return True

    def save_to_sd(self, filename: str = "default.pps") -> None:
        """Save current RAM params to SD card (opcode 90, op 1).

        Firmware sends no ack byte: do not read confirmation.
        A 100ms sleep is inserted to allow SD write to complete.
        """
        if self._arcom is None:
            return
        name_bytes = filename.encode("ascii")
        self._arcom.serial_object.write(
            self._frame(
                SendMessageHeader.SETTINGS,
                _u8(SD_SAVE),
                _u8(len(name_bytes)),
                name_bytes,
            )
        )
        time.sleep(0.1)

    def read_sd_params(self) -> dict | None:
        """Read 178-byte SD parameter file via opcode 85 and parse to a dict.

        Returns None if the firmware returns an unexpected byte count.
        Keys match ChannelConfig field names; 'triggerAddress' is firmware-only
        (4-element list of output channel link flags per trigger channel).

        SD byte layout: per output channel ×4 (42 bytes each):
          8× uint32  phase1Duration, interPhaseInterval, phase2Duration,
                     interPulseInterval, burstDuration, interBurstInterval,
                     pulseTrainDuration, pulseTrainDelay  (firmware cycles ÷ 20000 = s)
          1× uint8   isBiphasic
          3× uint16  phase1Voltage, phase2Voltage, restingVoltage  (0-65535 → ±10V)
          3× uint8   customTrainID, customTrainTarget, customTrainLoop
        Per trigger channel ×2 (5 bytes each):
          1× uint8   triggerMode
          4× uint8   triggerAddress[0..3]
        Total: 4×42 + 2×5 = 178 bytes
        """
        if self._arcom is None:
            return None
        self._arcom.serial_object.write(self._frame(SendMessageHeader.READ_SD))
        time.sleep(0.1)
        raw = self._arcom.serial_object.read(178)

        if len(raw) != 178:
            return None

        byte_names = (
            "isBiphasic",
            "customTrainID",
            "customTrainTarget",
            "customTrainLoop",
        )
        result: dict = {
            name: [] for name in (*TIME_PARAMS, *VOLTAGE_PARAMS, *byte_names)
        }
        result["triggerMode"] = []
        result["triggerAddress"] = []

        offset = 0
        for _ in range(4):
            for name in TIME_PARAMS:
                (cycles,) = struct.unpack_from("<I", raw, offset)
                result[name].append(cycles / PULSEPAL_CYCLE_FREQUENCY)
                offset += 4
            result["isBiphasic"].append(raw[offset])
            offset += 1
            for name in VOLTAGE_PARAMS:
                (code,) = struct.unpack_from("<H", raw, offset)
                result[name].append(round((code / 65535.0) * V_SPAN + V_MIN, 4))
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
