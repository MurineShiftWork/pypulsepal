# Advanced

## Custom pulse trains

Upload a custom sequence of pulse times and voltages to one of the two custom train slots (IDs 0 or 1). Once uploaded, assign it to a channel via `ChannelConfig.customTrainID`.

```python
import numpy as np

pulse_times    = list(np.arange(0, 1.0, 0.05))   # 20 pulses, 50 ms apart
pulse_voltages = [5.0 if i % 2 == 0 else 3.0 for i in range(len(pulse_times))]

pp.upload_custom_pulse_train(
    pulse_train_id=0,
    pulse_times=pulse_times,
    pulse_voltages=pulse_voltages,
)

# Assign to channel 0
pp.channel_configs[0].customTrainID = 0
pp.channel_configs[0].customTrainTarget = 0   # 0 = pulse times, 1 = burst times
pp.channel_configs[0].customTrainLoop = 0     # 0 = once, 1 = loop
pp.sync_all_params()
```

## Custom waveforms

Upload an evenly-spaced waveform by specifying a fixed time step (`pulse_width`) and a voltage array. Useful for arbitrary analog output shapes.

```python
import numpy as np

t = np.linspace(0, 2 * np.pi, 100)
voltages = list(5.0 * np.sin(t))

pp.upload_custom_waveform(
    pulse_train_id=1,
    pulse_width=0.001,   # 1 ms per sample
    pulse_voltages=voltages,
)

pp.channel_configs[1].customTrainID = 1
pp.sync_all_params()
```

## SD card (model 2 only)

### Save current RAM parameters to SD card

```python
pp.save_to_sd("my_params.pps")
```

A 100 ms sleep is inserted internally to allow the SD write to complete. The firmware sends no acknowledgement for this command.

### Read parameters from SD card

Returns a dict keyed by `ChannelConfig` field names, with lists of per-channel values, plus `triggerMode` and `triggerAddress` lists.

```python
params = pp.read_sd_params()
if params:
    print(params["phase1Voltage"])   # [v_ch0, v_ch1, v_ch2, v_ch3]
    print(params["triggerMode"])     # [mode_t0, mode_t1]
```

Returns `None` if the firmware response is an unexpected byte count.

## Digital logic output (model 2 only)

Set or read the Arduino digital logic level on an output channel.

```python
pp.set_logic(channel=0, level=1)   # set high
pp.set_logic(channel=0, level=0)   # set low

state = pp.get_logic(channel=0)    # returns 0 or 1
```
