"""Upload a custom pulse train with arbitrary timing and voltages."""

import time

from pypulsepal import PulsePal

SERIAL_PORT = "/dev/ttyACM0"

# Irregular inter-pulse intervals (seconds from t=0)
pulse_times = [0.0, 0.050, 0.080, 0.150, 0.200]
pulse_voltages = [5.0, 3.0, 5.0, 3.0, 5.0]

with PulsePal(serial_port=SERIAL_PORT) as pp:
    pp.upload_custom_pulse_train(
        pulse_train_id=0,
        pulse_times=pulse_times,
        pulse_voltages=pulse_voltages,
    )

    ch = pp.channel_configs[0]
    ch.customTrainID = 1  # use custom train slot 0 (1-indexed in firmware)
    ch.customTrainTarget = 0  # output pulses (not burst timing)
    ch.customTrainLoop = 0  # play once
    ch.phase1Duration = 0.001
    ch.pulseTrainDuration = 0.3

    pp.sync_all_params()
    pp.trigger_selected_channels(channel_1=True)
    time.sleep(0.3)
