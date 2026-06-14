# API Reference

## PulsePal

```python
from pypulsepal import PulsePal
```

### Constructor

| Parameter | Type | Default | Description |
|---|---|---|---|
| `serial_port` | str | `None` | Serial port path (e.g. `/dev/ttyACM0`, `COM3`) |
| `baudrate` | int | `115200` | Serial baud rate |
| `cycle_frequency` | int | `20000` | Hardware cycle frequency in Hz |
| `nr_output_channels` | int | `4` | Number of output channels |
| `nr_trigger_channels` | int | `2` | Number of trigger channels |

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `channel_configs` | `list[ChannelConfig]` | Per-channel configuration (0-indexed) |
| `trigger_configs` | `list[TriggerConfig]` | Per-trigger configuration (0-indexed) |
| `config` | `PulsePalConfig` | Snapshot of current in-memory state (property) |
| `firmware_version` | int | Detected firmware version |
| `model` | int | Hardware model: 1 or 2 |

### Upload methods

| Method | Description |
|---|---|
| `sync_all_params()` | Bulk upload all params in one serial write (preferred) |
| `upload_all()` | Per-parameter upload with per-write confirmation |
| `program_one_param(channel, param_name, param_value)` | Update a single parameter on one channel |
| `program_trigger_channel(trigger_channel, trigger_mode)` | Set trigger mode on a trigger channel |

### Voltage and output

| Method | Description |
|---|---|
| `set_resting_voltage(channel, voltage)` | Set `restingVoltage` on one channel |
| `set_fixed_voltage(channel, voltage)` | Set immediate DC voltage outside pulse train |
| `set_continuous(channel, state)` | Start (1) or stop (0) continuous output on a channel |
| `set_logic(channel, level)` | Set digital logic level: model 2 only |
| `get_logic(channel)` | Read digital logic level: model 2 only |

### Triggering

| Method | Description |
|---|---|
| `trigger_selected_channels(**kwargs)` | Software-trigger specific channels (`channel_1=True`, …) |
| `trigger_all_channels()` | Software-trigger all four channels |
| `stop_all_outputs()` | Abort all running outputs |

### Custom trains

| Method | Description |
|---|---|
| `upload_custom_pulse_train(pulse_train_id, pulse_times, pulse_voltages)` | Upload custom timing+voltage sequence to slot 0 or 1 |
| `upload_custom_waveform(pulse_train_id, pulse_width, pulse_voltages)` | Upload evenly-spaced waveform to slot 0 or 1 |

### Config persistence

| Method | Description |
|---|---|
| `save_config(path)` | Save in-memory config to JSON or YAML |
| `load_config(path)` | Load config from JSON or YAML and apply in memory |
| `from_config(config, serial_port)` | Class method: connect and apply a `PulsePalConfig` |
| `save_settings()` | Send disconnect opcode to persist params on device |
| `save_to_sd(filename)` | Save RAM params to SD card: model 2 only |
| `read_sd_params()` | Read SD card params as dict: model 2 only |
| `reset_to_defaults()` | Reset all configs to defaults and sync to device |

---

## Models

```python
from pypulsepal.models import ChannelConfig, TriggerConfig, PulsePalConfig
```

`PulsePalConfig` uses **1-indexed integer keys** for channels and triggers: `channels[1]` through `channels[4]`, `triggers[1]` through `triggers[2]`. String keys from JSON (`"1"`, `"2"`, …) are coerced to integers automatically.

See [Concepts](concepts.md) for field-level documentation.

---

## config_io

```python
from pypulsepal.config_io import load_config, save_config
```

| Function | Description |
|---|---|
| `load_config(path)` | Load `PulsePalConfig` from a JSON or YAML file |
| `save_config(config, path)` | Save `PulsePalConfig` to a JSON or YAML file |

---

## Auto-generated reference

::: pypulsepal.PulsePal

::: pypulsepal.pulsepal.PulsePalError
