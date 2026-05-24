"""Two ways to open a PulsePal connection.

Context manager (recommended)
------------------------------
Calls save_settings() + closes the port automatically on exit,
even if an exception is raised mid-session.

Manual open/close
-----------------
Useful when the PulsePal must stay open across multiple scopes
(e.g. inside a long-running experiment loop managed by other code).
Call save_settings() and close() explicitly when done.
"""

import time

from pypulsepal import PulsePal

SERIAL_PORT = "/dev/ttyACM0"

# --- context manager (preferred) -------------------------------------------
with PulsePal(serial_port=SERIAL_PORT) as pp:
    pp.channel_configs[0].phase1Voltage = 5.0
    pp.channel_configs[0].pulseTrainDuration = 0.5
    pp.sync_all_params()
    pp.trigger_selected_channels(channel_1=True)
    time.sleep(0.5)
# save_settings() + close() called automatically here


# --- manual open / close ----------------------------------------------------
pp = PulsePal(serial_port=SERIAL_PORT)
try:
    pp.channel_configs[0].phase1Voltage = 3.0
    pp.channel_configs[0].pulseTrainDuration = 0.5
    pp.sync_all_params()
    pp.trigger_selected_channels(channel_1=True)
    time.sleep(0.5)
finally:
    pp.close()
