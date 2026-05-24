"""Load parameters from a saved config file and trigger channel 1."""

from pypulsepal import PulsePal
from pypulsepal.config_io import load_config

SERIAL_PORT = "/dev/ttyACM0"
CONFIG_PATH = "my_params.json"  # or .yaml

cfg = load_config(CONFIG_PATH)
with PulsePal.from_config(cfg, serial_port=SERIAL_PORT) as pp:
    pp.trigger_selected_channels(channel_1=True)
