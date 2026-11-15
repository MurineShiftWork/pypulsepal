# PyPulsePal

[![PyPI](https://img.shields.io/pypi/v/pypulsepal.svg)](https://pypi.org/project/pypulsepal)

Python API for the PulsePal open-source pulse train generator.

**[→ Full documentation](https://murineshiftwork.github.io/pypulsepal)**

## Example usage

Load and apply a saved config file:

```python
from pypulsepal import PulsePal
from pypulsepal.config_io import load_config

cfg = load_config("my_params.json")   # or .yaml
with PulsePal.from_config(cfg, serial_port="/dev/ttyACM0") as pp:
    pp.trigger_selected_channels(channel_1=True)
```

Standard instantiation:

```python
import time
from pypulsepal import PulsePal

pp = PulsePal(serial_port="/dev/ttyACM0")
pp.channel_configs[0].phase1Voltage = 5.0
pp.channel_configs[0].pulseTrainDuration = 1.0
pp.sync_all_params()
pp.trigger_selected_channels(channel_1=True)
time.sleep(1)
pp.stop_all_outputs()
pp.close()
```

As a context manager (saves settings and closes on exit automatically):

```python
import time
from pypulsepal import PulsePal

with PulsePal(serial_port="/dev/ttyACM0") as pp:
    pp.channel_configs[0].phase1Voltage = 5.0
    pp.channel_configs[0].pulseTrainDuration = 1.0
    pp.sync_all_params()
    pp.trigger_selected_channels(channel_1=True)
    time.sleep(1)
    pp.stop_all_outputs()
```

## Installation

```shell
pip install pypulsepal
```

With YAML config file support:

```shell
pip install "pypulsepal[yaml]"
```

From source:

```shell
git clone https://github.com/murineshiftwork/pypulsepal.git
cd pypulsepal
pip install -e ".[yaml]"
```

## Citation

To cite PyPulsePal, reference the GitHub repository:

> Rollik, Lars B. PyPulsePal: Python API for the PulsePal open-source pulse train generator. https://github.com/murineshiftwork/pypulsepal

Please also cite the original [PulsePal](https://github.com/sanworks/PulsePal) hardware and [PyBpod](https://github.com/pybpod/pybpod) publications that this package builds on.

## License & sources

This software is licensed under the **[BSD 3-Clause License](LICENSE)**.

It implements the PulsePal USB serial protocol as documented on the PulsePal wiki: [USB interface v2.x](https://sites.google.com/site/pulsepalwiki/usb-serial-interface/usb-interface-v2-x), [USB interface v1.x](https://sites.google.com/site/pulsepalwiki/usb-serial-interface/usb-interface-v1-x) and the [parameter guide](https://sites.google.com/site/pulsepalwiki/parameter-guide).

Releases before 0.4.4 were published under the GNU GPL v3.0 and remain under that licence.

`src/pypulsepal/_arcom.py` is vendored from [pybpod-api](https://github.com/pybpod/pybpod-api) 1.8.2 (MIT, Copyright © 2016 Champalimaud Foundation) with minor adaptations.

## Useful references

- [PulsePal USB v2 serial interface](https://sites.google.com/site/pulsepalwiki/usb-serial-interface/usb-interface-v2-x)
- [PulsePal parameter guide](https://sites.google.com/site/pulsepalwiki/parameter-guide)
- [PyBpod ArCOM](https://github.com/pybpod/pybpod-api/blob/master/pybpodapi/com/arcom.py)
