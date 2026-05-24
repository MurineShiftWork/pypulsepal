"""Hold a channel at a fixed DC voltage, then return it to resting."""

import time

from pypulsepal import PulsePal

SERIAL_PORT = "/dev/ttyACM0"

with PulsePal(serial_port=SERIAL_PORT) as pp:
    pp.set_fixed_voltage(channel=0, voltage=3.3)
    time.sleep(2.0)
    pp.set_fixed_voltage(channel=0, voltage=0.0)
