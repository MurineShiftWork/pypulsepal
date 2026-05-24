# Usage

## Uploading parameters to the device

Two methods upload the current in-memory channel and trigger configs to the device.

### `sync_all_params()` — bulk upload (preferred)

Sends all parameters in a single serial write. Faster and less error-prone than iterating parameter by parameter.

```python
pp.channel_configs[0].phase1Voltage = 5.0
pp.channel_configs[0].phase1Duration = 0.002
pp.sync_all_params()
```

### `upload_all()` — per-parameter upload

Sends one serial round-trip per parameter. Use when you need to confirm each parameter individually, or for compatibility with older firmware.

```python
pp.upload_all()
```

### `program_one_param()` — single parameter update

Updates a single parameter on a single channel without uploading everything.

```python
pp.program_one_param(channel=0, param_name="phase1Voltage", param_value=3.0)
```

### `set_resting_voltage()` — convenience wrapper

```python
pp.set_resting_voltage(channel=0, voltage=0.0)
```

### `set_fixed_voltage()` — immediate DC output

Sets a channel to a fixed DC voltage immediately, outside of any pulse train sequence.

```python
pp.set_fixed_voltage(channel=0, voltage=3.3)
```

## Triggering channels

### Software trigger — selected channels

```python
pp.trigger_selected_channels(channel_1=True, channel_3=True)
```

### Software trigger — all channels

```python
pp.trigger_all_channels()
```

### Stopping output

```python
pp.stop_all_outputs()
```

### Continuous output mode

Keep a channel running continuously until stopped:

```python
pp.set_continuous(channel=0, state=1)   # start
pp.set_continuous(channel=0, state=0)   # stop
```

## Trigger channel configuration

Set the trigger mode for a trigger channel (0 or 1):

```python
pp.program_trigger_channel(trigger_channel=0, trigger_mode=1)  # toggle mode
```

Trigger modes: `0` = normal, `1` = toggle, `2` = pulse-gated.

## Config file I/O

### Save current config

```python
pp.save_config("params.json")    # JSON
pp.save_config("params.yaml")    # YAML (requires pypulsepal[yaml])
```

### Load config from file and apply

```python
pp.load_config("params.json")
pp.sync_all_params()
```

### Load config without a device connection

```python
from pypulsepal.config_io import load_config
from pypulsepal import PulsePal

cfg = load_config("params.json")
pp = PulsePal.from_config(cfg, serial_port="/dev/ttyACM0")
```

`from_config` connects, applies the config, and calls `sync_all_params()` in one step.

## Reset to defaults

Resets all channel and trigger configs to factory defaults and syncs to the device.

```python
pp.reset_to_defaults()
```

## Saving device state

`save_settings()` sends the disconnect opcode (81), which instructs the firmware to save current RAM parameters. The context manager calls this automatically on exit.

```python
pp.save_settings()
```
