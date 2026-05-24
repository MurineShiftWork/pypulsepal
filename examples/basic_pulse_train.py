"""Basic pulse train: set parameters on channel 1 and trigger it."""

import time

from pypulsepal import PulsePal

SERIAL_PORT = "/dev/ttyACM0"

with PulsePal(serial_port=SERIAL_PORT) as pp:
    ch = pp.channel_configs[0]
    ch.phase1Voltage = 5.0
    ch.phase1Duration = 0.002  # 2 ms pulse
    ch.interPulseInterval = 0.048  # 48 ms gap → 20 Hz
    ch.pulseTrainDuration = 1.0  # 1 second train

    pp.sync_all_params()
    pp.trigger_selected_channels(channel_1=True)
    time.sleep(1.0)
    pp.stop_all_outputs()
