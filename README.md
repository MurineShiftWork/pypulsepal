# PyPulsePal

[![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.6379627.svg)](https://doi.org/10.5281/zenodo.6379627)
[![PyPI](https://img.shields.io/pypi/v/pypulsepal.svg)](https://pypi.org/project/pypulsepal)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Python API for the PulsePal open-source pulse train generator.

**[→ Full documentation](https://larsrollik.github.io/pypulsepal)**

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
git clone https://github.com/larsrollik/pypulsepal.git
cd pypulsepal
pip install -e ".[yaml]"
```

## Citation

To cite PyPulsePal:

> Rollik, Lars B. (2022). PyPulsePal: Python API for the PulsePal open-source pulse train generator. doi: [10.5281/zenodo.6379627](https://doi.org/10.5281/zenodo.6379627).

```bibtex
@misc{rollik2022pypulsepal,
    author    = {Lars B. Rollik},
    title     = {{PyPulsePal: Python API for the PulsePal open-source pulse train generator}},
    year      = {2022},
    publisher = {Zenodo},
    url       = {https://doi.org/10.5281/zenodo.6379627},
    doi       = {10.5281/zenodo.6379627},
}
```

Please also cite the original [PulsePal](https://github.com/sanworks/PulsePal) hardware and [PyBpod](https://github.com/pybpod/pybpod) publications that this package builds on.

## License & sources

This software is released under the **[GNU GPL v3.0](LICENSE)**.

This work is derived from the [Sanworks PulsePal Python API](https://github.com/sanworks/PulsePal/tree/develop) ([commit: 5bb189f](https://github.com/sanworks/PulsePal/commit/5bb189fec8d7435433b8c23f7bae520f92e271af)).

`src/pypulsepal/_arcom.py` is vendored from [pybpod-api](https://github.com/pybpod/pybpod-api) 1.8.2 (MIT, Copyright © 2016 Champalimaud Foundation) with minor adaptations.

## Useful references

- [PulsePal Python 3 API](https://github.com/sanworks/PulsePal/blob/develop/Python/Python3/PulsePal.py)
- [PulsePal USB v2 serial interface](https://sites.google.com/site/pulsepalwiki/usb-serial-interface/usb-interface-v2-x)
- [PulsePal parameter definitions](https://sites.google.com/site/pulsepalwiki/matlab-gnu-octave/functions/programpulsepalparam)
- [PyBpod ArCOM](https://github.com/pybpod/pybpod-api/blob/master/pybpodapi/com/arcom.py)
