"""Biphasic (charge-balanced) stimulation on channel 1."""

import time

from pypulsepal import PulsePal

SERIAL_PORT = "/dev/ttyACM0"

with PulsePal(serial_port=SERIAL_PORT) as pp:
    ch = pp.channel_configs[0]
    ch.isBiphasic = True
    ch.phase1Voltage = 3.0
    ch.phase1Duration = 0.001  # 1 ms positive phase
    ch.interPhaseInterval = 0.0  # no gap between phases
    ch.phase2Voltage = -3.0
    ch.phase2Duration = 0.001  # 1 ms negative phase
    ch.interPulseInterval = 0.018  # 18 ms → ~50 Hz
    ch.pulseTrainDuration = 0.5

    pp.sync_all_params()
    pp.trigger_selected_channels(channel_1=True)
    time.sleep(0.5)
