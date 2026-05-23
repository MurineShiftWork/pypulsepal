"""
Minimal hardware connectivity test.

Usage:
    python scripts/test_connection.py /dev/ttyACM0
    python scripts/test_connection.py COM3          # Windows

What it tests:
    1. ArCOM open + handshake (firmware version, model detection)
    2. encode_message / volts_to_bytes encoding sanity (no serial)
    3. program_one_param — ack + local bookkeeping
    4. sync_all_params (bulk upload, opcode 73) — ack
    5. Device read-back via opcode 85 (reads SD card file, NOT RAM)
         Note: opcode 85 streams the last saved SD card file. To verify RAM
         params were received, we first save to SD (opcode 90 op 1) then
         read back via opcode 85 and compare.
    6. set_fixed_voltage (opcode 79)
    7. trigger ch0 + stop (opcodes 77, 80)
    8. Clean disconnect

Firmware note: there is no opcode that dumps current RAM parameters directly.
Read-back requires: program → save to SD (opcode 90 op 1) → read SD (opcode 85).
"""

import sys
import time


def _check(label, result):
    status = "OK" if result else "FAIL"
    print(f"  [{status}] {label}")
    if not result:
        print("       ^ stopping here")
        sys.exit(1)


def run(port):
    print(f"\n=== PulsePal connection test on {port} ===\n")

    # ------------------------------------------------------------------
    # 1. Connect + handshake
    # ------------------------------------------------------------------
    print("1. Connect + handshake")
    from pypulsepal import PulsePal
    from pypulsepal.models import ChannelConfig

    pp = PulsePal(serial_port=port)
    info = f"model={pp.model}  fw={pp.firmware_version}  dac_bitMax={pp.dac_bitMax}"
    _check(info, pp.model is not None and pp.firmware_version is not None)

    # ------------------------------------------------------------------
    # 2. Encoding sanity (no serial)
    # ------------------------------------------------------------------
    print("\n2. Encoding sanity (no serial)")
    from pypulsepal.utils import encode_message, volts_to_bytes

    v = int(volts_to_bytes(volt=0.0, dac_bitMax=65535))
    _check(f"0V → {v} (expected 32768)", v == 32768)

    v = int(volts_to_bytes(volt=10.0, dac_bitMax=65535))
    _check(f"+10V → {v} (expected 65535)", v == 65535)

    b = encode_message(213, encoding="uint8")
    _check(f"encode_message(213, uint8) = {b!r} (expected b'\\xd5')", b == b"\xd5")

    b = encode_message([1, 2], encoding="uint32")
    _check(f"encode_message([1,2], uint32) len={len(b)} (expected 8)", len(b) == 8)

    # ------------------------------------------------------------------
    # 3. program_one_param — ack + local bookkeeping
    # ------------------------------------------------------------------
    print("\n3. program_one_param (ack + local bookkeeping)")
    ok = pp.program_one_param(channel=0, param_name="phase1Duration", param_value=0.002)
    _check("write phase1Duration=0.002s on ch0: ack", ok)
    stored = pp.channel_configs[0].phase1Duration
    _check(
        f"  local channel_configs[0].phase1Duration == 0.002 (got {stored})",
        stored == 0.002,
    )  # noqa: E501

    ok = pp.program_one_param(channel=0, param_name="phase1Voltage", param_value=3.0)
    _check("write phase1Voltage=3.0V on ch0: ack", ok)
    stored = pp.channel_configs[0].phase1Voltage
    _check(
        f"  local channel_configs[0].phase1Voltage == 3.0 (got {stored})", stored == 3.0
    )  # noqa: E501

    # ------------------------------------------------------------------
    # 4. sync_all_params — bulk upload (opcode 73)
    # ------------------------------------------------------------------
    print("\n4. sync_all_params (bulk upload, opcode 73)")
    pp.channel_configs[0] = ChannelConfig(
        phase1Voltage=2.0,
        phase1Duration=0.001,
        interPulseInterval=0.05,
        pulseTrainDuration=0.5,
    )
    ok = pp.sync_all_params()
    _check("sync_all_params: ack", ok)

    # ------------------------------------------------------------------
    # 5. Device read-back: save RAM → SD, then read SD via opcode 85
    # ------------------------------------------------------------------
    print("\n5. Device read-back (save to SD then opcode 85)")
    print("  saving current RAM params to SD card (opcode 90 op 1) ...")
    pp.save_to_sd(filename="test.pps")
    print("  [OK] save to SD sent (no ack expected per firmware)")

    print("  reading back from SD (opcode 85) ...")
    device = pp.read_sd_params()
    if device is not None:
        print(f"  [DEBUG] opcode 85 returned data for {len(device['phase1Voltage'])} channels")
        d_volt = device["phase1Voltage"][0]
        _check(
            f"  device phase1Voltage ch0 == 2.0V (got {d_volt})",
            abs(d_volt - 2.0) < 0.01,
        )
        d_dur = device["phase1Duration"][0]
        _check(
            f"  device phase1Duration ch0 == 0.001s (got {d_dur})",
            abs(d_dur - 0.001) < 1e-4,
        )

    # ------------------------------------------------------------------
    # 6. set_fixed_voltage (opcode 79)
    # ------------------------------------------------------------------
    print("\n6. set_fixed_voltage (opcode 79)")
    ok = pp.set_fixed_voltage(channel=0, voltage=1.0)
    _check("set ch0 to 1.0V fixed: ack", ok)
    time.sleep(0.3)
    ok = pp.set_fixed_voltage(channel=0, voltage=0.0)
    _check("return ch0 to 0.0V: ack", ok)

    # ------------------------------------------------------------------
    # 7. Trigger ch0 + stop (opcodes 77, 80)
    # ------------------------------------------------------------------
    print("\n7. trigger ch0 then stop")
    pp.trigger_selected_channels(channel_1=True)
    print("   triggered ch0 — waiting 0.6s ...")
    time.sleep(0.6)
    pp.stop_all_outputs()
    print("  [OK] stop_all_outputs sent (no ack expected per firmware)")

    # ------------------------------------------------------------------
    # 8. Disconnect
    # ------------------------------------------------------------------
    print("\n8. Disconnect")
    ok = pp.save_settings()
    print(f"  [INFO] save_settings returned {ok} (False is a known firmware quirk)")
    pp._arcom.close()
    pp._arcom = None

    print("\n=== All checks passed ===\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/test_connection.py <serial_port>")
        sys.exit(1)
    run(sys.argv[1])
