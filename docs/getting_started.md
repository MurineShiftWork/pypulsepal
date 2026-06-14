# Getting Started

## Installation

```shell
pip install pypulsepal
```

For YAML config file support:

```shell
pip install "pypulsepal[yaml]"
```

From source (development):

```shell
git clone https://github.com/larsrollik/pypulsepal.git
cd pypulsepal
pip install -e ".[yaml]"
```

## Connecting to the device

Pass the serial port of the PulsePal device. On Linux this is typically `/dev/ttyACM0`; on Windows `COM3` or similar.

```python
from pypulsepal import PulsePal

pp = PulsePal(serial_port="/dev/ttyACM0")
```

On connection, `PulsePal` performs a handshake, reads the firmware version to determine the hardware model (1 or 2), and sets the LCD display to "PyPulsePal".

## Basic pulse train

Channels are **0-indexed** in the Python API (channels 0-3, triggers 0-1).

```python
import time
from pypulsepal import PulsePal

pp = PulsePal(serial_port="/dev/ttyACM0")

# Configure channel 0
pp.channel_configs[0].phase1Voltage = 5.0       # volts
pp.channel_configs[0].phase1Duration = 0.002    # seconds
pp.channel_configs[0].interPulseInterval = 0.1  # seconds
pp.channel_configs[0].pulseTrainDuration = 1.0  # seconds

# Upload all parameters to device
pp.sync_all_params()

# Software-trigger channel 0
pp.trigger_selected_channels(channel_1=True)
time.sleep(1)

pp.stop_all_outputs()
pp.save_settings()  # persists params to device RAM
```

## Context manager

The context manager calls `save_settings()` and closes the serial port automatically on exit.

```python
import time
from pypulsepal import PulsePal

with PulsePal(serial_port="/dev/ttyACM0") as pp:
    pp.channel_configs[0].phase1Voltage = 3.0
    pp.sync_all_params()
    pp.trigger_all_channels()
    time.sleep(2)
```
