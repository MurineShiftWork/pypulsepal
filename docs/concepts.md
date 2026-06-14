# Concepts

## Hardware models

PyPulsePal supports both PulsePal hardware generations. The model is detected automatically from the firmware version on connection.

| | Model 1 | Model 2 |
|---|---|---|
| Firmware version | < 20 | ≥ 20 |
| DAC resolution | 8-bit (uint8) | 16-bit (uint16) |
| Voltage range | ±10 V | ±10 V |
| SD card | No | Yes (opcode 90) |
| Digital logic | No | Yes (opcodes 86/87) |

!!! warning "Firmware v20 bug"
    Firmware version exactly 20 has a known bug in Pulse Gated trigger mode when used with multiple inputs. Update firmware if possible. PyPulsePal logs a warning on connection.

## Channel configuration

Each of the 4 output channels is described by a `ChannelConfig` Pydantic model. All fields are validated on assignment.

```python
from pypulsepal.models import ChannelConfig

cfg = ChannelConfig()          # all defaults
cfg.phase1Voltage = 5.0        # validated: must be in [-10, 10]
cfg.phase1Voltage = 15.0       # raises ValidationError
```

### ChannelConfig fields

| Field | Type | Default | Unit | Notes |
|---|---|---|---|---|
| `isBiphasic` | bool | `False` |: | Biphasic pulse mode |
| `phase1Voltage` | float | `5.0` | V | Range −10 to +10 |
| `phase2Voltage` | float | `−5.0` | V | Range −10 to +10 |
| `restingVoltage` | float | `0.0` | V | Range −10 to +10 |
| `phase1Duration` | float | `0.001` | s | Must be ≥ 0 |
| `interPhaseInterval` | float | `0.001` | s | Must be ≥ 0 |
| `phase2Duration` | float | `0.001` | s | Must be ≥ 0 |
| `interPulseInterval` | float | `0.01` | s | Must be ≥ 0 |
| `burstDuration` | float | `0.0` | s | 0 = bursts disabled |
| `interBurstInterval` | float | `0.0` | s | 0 = bursts disabled |
| `pulseTrainDuration` | float | `1.0` | s | Must be ≥ 0 |
| `pulseTrainDelay` | float | `0.0` | s | Must be ≥ 0 |
| `linkTriggerChannel1` | int | `1` |: | 0 or 1 |
| `linkTriggerChannel2` | int | `0` |: | 0 or 1 |
| `customTrainID` | int | `0` |: | 0 = train 1, 1 = train 2 |
| `customTrainTarget` | int | `0` |: | 0 = pulse times, 1 = burst times |
| `customTrainLoop` | int | `0` |: | 0 = once, 1 = loop |

## Trigger configuration

Each of the 2 trigger channels is described by a `TriggerConfig` model.

| Field | Type | Default | Notes |
|---|---|---|---|
| `triggerMode` | int | `0` | 0 = normal, 1 = toggle, 2 = pulse-gated |

- **Normal (0)**: trigger starts the pulse train; a second trigger while running has no effect.
- **Toggle (1)**: first trigger starts, second trigger stops.
- **Pulse-gated (2)**: pulse train runs only while trigger input is high.

## PulsePalConfig

`PulsePalConfig` holds the full device state: 4 channel configs and 2 trigger configs.
Channels and triggers are keyed by their **1-indexed hardware number** (1-4 for channels, 1-2 for triggers), so there is never any ambiguity from list ordering.

```python
from pypulsepal.models import PulsePalConfig, ChannelConfig, TriggerConfig

cfg = PulsePalConfig()
cfg.channels[1].phase1Voltage = 5.0   # channel 1
cfg.channels[2].phase1Voltage = 3.0   # channel 2
cfg.triggers[1].triggerMode = 1       # trigger 1
```

Serialised to JSON/YAML the structure is:

```json
{
  "channels": {
    "1": {"phase1Voltage": 5.0, ...},
    "2": {"phase1Voltage": 3.0, ...},
    "3": {...},
    "4": {...}
  },
  "triggers": {
    "1": {"triggerMode": 1},
    "2": {"triggerMode": 0}
  }
}
```

String keys in JSON (`"1"`, `"2"`, …) are coerced to integers automatically on load. YAML files use native integer keys.

The `pp.config` property on a connected `PulsePal` instance returns a `PulsePalConfig` snapshot of the current in-memory state.

```python
snapshot = pp.config   # PulsePalConfig keyed by 1-indexed channel/trigger number
```

## Pydantic validation

All config models use `validate_assignment=True`, so field constraints are enforced on every assignment, not just on construction. This means out-of-range values raise `ValidationError` immediately rather than silently corrupting the device state.
