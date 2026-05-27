# PyPulsePal

[![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.6379627.svg)](https://doi.org/10.5281/zenodo.6379627)
[![PyPI](https://img.shields.io/pypi/v/pypulsepal.svg)](https://pypi.org/project/pypulsepal)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Python API for the [PulsePal](https://github.com/sanworks/PulsePal) open-source pulse train generator.

## Key features

- Validated Pydantic v2 models for channel and trigger configuration
- Single-call bulk upload (`sync_all_params`) and per-parameter programming (`program_one_param`)
- JSON and YAML config file I/O
- Custom pulse trains and arbitrary waveforms
- SD card persistence (model 2)
- Digital logic output (model 2)
- Context manager with automatic save-on-exit

## Quick start

```python
from pypulsepal import PulsePal

with PulsePal(serial_port="/dev/ttyACM0") as pp:
    pp.channel_configs[0].phase1Voltage = 5.0
    pp.channel_configs[0].pulseTrainDuration = 1.0
    pp.sync_all_params()
    pp.trigger_selected_channels(channel_1=True)
```

→ [Getting Started](getting_started.md) for installation and a step-by-step walkthrough.
