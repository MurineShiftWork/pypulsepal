[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.6379627.svg)](https://doi.org/10.5281/zenodo.6379627)
[![Website](https://img.shields.io/website?up_message=online&url=https%3A%2F%2Fgithub.com/larsrollik/pypulsepal)](https://github.com/larsrollik/pypulsepal)
[![PyPI](https://img.shields.io/pypi/v/pypulsepal.svg)](https://pypi.org/project/pypulsepal)
[![Wheel](https://img.shields.io/pypi/wheel/pypulsepal.svg)](https://pypi.org/project/pypulsepal)
[![Contributions](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg)](https://github.com/larsrollik/pypulsepal/blob/main/CONTRIBUTING.md)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)


# PyPulsePal
Python API for the PulsePal open-source pulse train generator

---

This package provides an API to the [PulsePal] hardware.
Parameters are represented as validated Pydantic v2 models and can be saved/loaded as JSON or YAML files.
The ArCOM serial communication layer is vendored from [pybpod-api].

## Example usage

#### Basic usage
```python
import time
from pypulsepal import PulsePal

pp = PulsePal(serial_port="/dev/ttyACM0")

# Set a parameter on one channel
pp.program_one_param(channel=2, param_name="phase1Duration", param_value=0.002)

# Or set via convenience method
pp.set_resting_voltage(channel=2, voltage=4.2)

# Upload all channel configs to device
pp.upload_all()

# Trigger selected channels
pp.trigger_selected_channels(channel_2=True, channel_4=True)
time.sleep(1)

pp.stop_all_outputs()
pp.save_settings()
```

#### Context manager
```python
import time
from pypulsepal import PulsePal

with PulsePal(serial_port="/dev/ttyACM0") as pp:
    pp.upload_all()
    time.sleep(2)
```

#### Pydantic config models
```python
from pypulsepal.models import ChannelConfig, PulsePalConfig

# Build a config
cfg = PulsePalConfig()
cfg.channels[0].phase1Duration = 0.002
cfg.channels[0].phase1Voltage = 5.0

# Validation is enforced
cfg.channels[0].phase1Voltage = 15.0  # raises ValidationError (> 10 V)
```

#### JSON / YAML config files
```python
from pypulsepal import PulsePal

pp = PulsePal(serial_port="/dev/ttyACM0")

# Save current config
pp.save_config("my_params.json")   # or .yaml / .yml

# Load config and upload
pp.load_config("my_params.json")
pp.sync_all_params()
```

#### Load config without connecting
```python
from pypulsepal import PulsePal
from pypulsepal.config_io import load_config

cfg = load_config("my_params.json")
pp = PulsePal.from_config(cfg, serial_port="/dev/ttyACM0")
```

#### Reset device to defaults
```python
pp.reset_to_defaults()   # resets all channel and trigger configs and syncs to device
```

## Installation

```shell
pip install pypulsepal
```

With YAML support:
```shell
pip install "pypulsepal[yaml]"
```

From source:
```shell
git clone https://github.com/larsrollik/pypulsepal.git
cd pypulsepal/
pip install -e ".[yaml]"
```

## Problems & issues
Please open [issues](https://github.com/larsrollik/pypulsepal/issues) or [pull-requests](https://github.com/larsrollik/pypulsepal/pulls) in this repository.

## Citation
Please cite the original [PulsePal] and [PyBpod] code and publications that this package is based on.

To cite `PyPulsePal` with a reference to the current version (as publicly documented on Zenodo), please use:
> Rollik, Lars B. (2021). PyPulsePal: Python API for the PulsePal open-source pulse train generator. doi: [10.5281/zenodo.6379627](https://doi.org/10.5281/zenodo.6379627).

**BibTeX**
```BibTeX
@misc{rollik2022pypulsepal,
    author       = {Lars B. Rollik},
    title        = {{PyPulsePal: Python API for the PulsePal open-source pulse train generator}},
    year         = {2022},
    month        = mar,
    publisher    = {Zenodo},
    url          = {https://doi.org/10.5281/zenodo.6379627},
    doi          = {10.5281/zenodo.6379627},
  }
```

## License & sources
This software is released under the **[GNU GPL v3.0](https://github.com/larsrollik/pypulsepal/blob/main/LICENSE)**.

This work is derived from the [Sanworks PulsePal Python API](https://github.com/sanworks/PulsePal/tree/develop) ([commit: 5bb189f](https://github.com/sanworks/PulsePal/commit/5bb189fec8d7435433b8c23f7bae520f92e271af)).

The serial communication layer (`_arcom.py`) is vendored from [pybpod-api] 1.8.2 (MIT, Copyright © 2016 Champalimaud Foundation) with minor adaptations.

For changes from the original implementation, see the git history since [commit 972bc1e](https://github.com/larsrollik/pypulsepal/commit/972bc1ed3d07b6809e6cbcd05373be3b76ae5b5b).

## Useful code references
- [PyBpod com ArCOM]
- [PyBpod com protocol]
- [PyBpod message headers]
- [PulsePal Python 3 API]
- [PulsePal .ino file]
- [PulsePal param definitions]


[//]: # (links)
[Pulsepal]: https://github.com/sanworks/PulsePal
[PyBpod]: https://github.com/pybpod/pybpod
[pybpod-api]: https://github.com/pybpod/pybpod-api
[PyBpod com ArCOM]: https://github.com/pybpod/pybpod-api/blob/master/pybpodapi/com/arcom.py
[PyBpod com protocol]: https://github.com/pybpod/pybpod-api/blob/master/pybpodapi/bpod/bpod_com_protocol.py
[PyBpod message headers]: https://github.com/pybpod/pybpod-api/blob/master/pybpodapi/com/protocol/send_msg_headers.py
[PulsePal Python 3 API]: https://github.com/sanworks/PulsePal/blob/develop/Python/Python3/PulsePal.py
[PulsePal .ino file]: https://github.com/sanworks/PulsePal/blob/develop/Firmware/PulsePal_2_0_1/PulsePal_2_0_1.ino
[PulsePal param definitions]: https://sites.google.com/site/pulsepalwiki/matlab-gnu-octave/functions/programpulsepalparam
[PulsePal USB v2 opcode list]: https://sites.google.com/site/pulsepalwiki/usb-serial-interface/usb-interface-v2-x
