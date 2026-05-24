"""Upload a custom waveform (evenly-spaced voltage samples)."""

import time

import numpy as np

from pypulsepal import PulsePal

SERIAL_PORT = "/dev/ttyACM0"

# 1 kHz sine wave sampled at 10 kHz, duration 10 ms
sample_rate = 10_000  # Hz
duration = 0.010  # seconds
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
voltages = (5.0 * np.sin(2 * np.pi * 1000 * t)).tolist()
pulse_width = 1.0 / sample_rate  # seconds per sample

with PulsePal(serial_port=SERIAL_PORT) as pp:
    pp.upload_custom_waveform(
        pulse_train_id=0,
        pulse_width=pulse_width,
        pulse_voltages=voltages,
    )

    ch = pp.channel_configs[0]
    ch.customTrainID = 1
    ch.customTrainTarget = 0
    ch.customTrainLoop = 0
    ch.phase1Duration = pulse_width
    ch.pulseTrainDuration = duration

    pp.sync_all_params()
    pp.trigger_selected_channels(channel_1=True)
    time.sleep(duration + 0.05)
