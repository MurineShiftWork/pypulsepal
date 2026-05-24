"""Load a config file, inspect or modify it, and save to a new file.

The example configs in examples/config/ are not overwritten — the output
is written to a path you choose (here a sibling file next to the script).
"""

from pathlib import Path

from pypulsepal.config_io import load_config, save_config

HERE = Path(__file__).parent

# --- load from JSON ---
cfg_json = load_config(HERE / "config/example_config.json")
print(f"[json] channel 1 voltage : {cfg_json.channels[1].phase1Voltage} V")
print(f"[json] trigger 1 mode   : {cfg_json.triggers[1].triggerMode}")

# Modify and save to a separate file
cfg_json.channels[1].phase1Voltage = 4.0
cfg_json.channels[1].pulseTrainDuration = 2.0
out_json = HERE / "my_config.json"
save_config(cfg_json, out_json)
print(f"Saved → {out_json}")

# --- load from YAML ---
cfg_yaml = load_config(HERE / "config/example_config.yaml")
print(f"[yaml] channel 2 biphasic: {cfg_yaml.channels[2].isBiphasic}")
print(f"[yaml] channel 2 voltage : {cfg_yaml.channels[2].phase1Voltage} V")

# Modify and save to a separate file
cfg_yaml.channels[2].phase1Voltage = 2.5
out_yaml = HERE / "my_config.yaml"
save_config(cfg_yaml, out_yaml)
print(f"Saved → {out_yaml}")

# --- verify round-trip ---
reloaded = load_config(out_json)
assert reloaded.channels[1].phase1Voltage == 4.0
reloaded_yaml = load_config(out_yaml)
assert reloaded_yaml.channels[2].phase1Voltage == 2.5
print("Round-trip verified.")
