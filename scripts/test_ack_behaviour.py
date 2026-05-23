"""
Hardware test: verify ack byte behaviour for suspect opcodes.

pypulsepal calls _read_confirmation() after opcodes 81 and 82. The official
Sanworks Python3 API does NOT read an ack for either. This script sends each
opcode directly and checks whether the firmware actually returns a byte.

Opcodes tested:
  81  save_settings / disconnect — pypulsepal reads ack; currently returns False
  82  set_continuous             — pypulsepal reads ack; Sanworks API skips ack read
  90/1  save_to_sd               — confirmed no ack in firmware source; re-verified here

Usage:
    python scripts/test_ack_behaviour.py /dev/ttyACM1
    python scripts/test_ack_behaviour.py COM3           # Windows

Results are printed per opcode. Update PLAN_pypulsepal.md Priority 0b table with findings.
Run against model 1 and model 2 hardware if both are available.
"""

import sys
import time

ACK_WAIT = 0.3  # seconds to wait before checking the read buffer


def _drain(pp):
    n = pp._arcom.serial_object.inWaiting()
    if n:
        pp._arcom.serial_object.read(n)


def _probe_ack(pp, label):
    """Wait briefly then report how many bytes (if any) arrived."""
    time.sleep(ACK_WAIT)
    n = pp._arcom.serial_object.inWaiting()
    if n == 0:
        print(f"  [{label}]  NO ACK  (0 bytes in buffer after {ACK_WAIT}s)")
        return None
    raw = pp._arcom.serial_object.read(n)
    val = raw[0]
    tag = "ACK OK (1)" if val == 1 else f"BYTE={val:#04x}"
    print(f"  [{label}]  {tag}  — raw={raw!r}")
    return val


def test_opcode_81(pp):
    """Opcode 81: save_settings / disconnect.

    Current pypulsepal behaviour: calls _read_confirmation() → returns False.
    Hypothesis: firmware never actually sends the ack byte for this opcode.
    Note: after sending 81 the firmware closes the session; reconnect before next test.
    """
    from pypulsepal.utils import encode_message

    print("\n--- Opcode 81 (save_settings / disconnect) ---")
    msg = pp.encoded_opcode + encode_message(81, encoding="uint8")
    pp._arcom.serial_object.write(msg)
    result = _probe_ack(pp, "opcode 81")
    if result is None:
        print("  => No ack received. pypulsepal should NOT call _read_confirmation() here.")
    else:
        print(f"  => Firmware sent byte {result}. Ack IS present.")
    return result


def test_opcode_82(pp):
    """Opcode 82: set_continuous (channel, state).

    Current pypulsepal behaviour: calls _read_confirmation().
    Sanworks Python3 API: does NOT read an ack after setContinuousLoop.
    """
    from pypulsepal.utils import encode_message

    print("\n--- Opcode 82 (set_continuous, ch=0, state=0) ---")
    msg = (
        pp.encoded_opcode
        + encode_message(82, encoding="uint8")
        + encode_message(0, encoding="uint8")  # channel 0
        + encode_message(0, encoding="uint8")  # state = off
    )
    pp._arcom.serial_object.write(msg)
    result = _probe_ack(pp, "opcode 82")
    if result is None:
        print("  => No ack received. pypulsepal should NOT call _read_confirmation() here.")
        print("     (aligns with Sanworks official API)")
    else:
        print(f"  => Firmware sent byte {result}. Ack IS present (differs from Sanworks API).")
    return result


def test_opcode_90_op1(pp):
    """Opcode 90 op1: save_to_sd.

    Firmware source: confirmBit is declared but never written to serial.
    Expected: no ack byte.
    """
    from pypulsepal.utils import encode_message

    print("\n--- Opcode 90 op1 (save_to_sd) ---")
    filename = b"acktest.pps"
    msg = (
        pp.encoded_opcode
        + encode_message(90, encoding="uint8")
        + encode_message(1, encoding="uint8")  # op 1 = save
        + encode_message(len(filename), encoding="uint8")
        + filename
    )
    pp._arcom.serial_object.write(msg)
    time.sleep(0.2)  # extra wait for SD write
    result = _probe_ack(pp, "opcode 90/1")
    if result is None:
        print("  => Confirmed: no ack (consistent with firmware source).")
    else:
        print(f"  => UNEXPECTED byte {result} received.")
    return result


def run(port):
    from pypulsepal import PulsePal

    print(f"\n=== PulsePal ack behaviour test — {port} ===\n")
    pp = PulsePal(serial_port=port, baudrate=115200)
    print(
        f"Connected: model={pp.model}  firmware={pp.firmware_version}"
        f"  dac_bitMax={pp.dac_bitMax}"
    )

    _drain(pp)

    # --- opcode 82 first (no reconnect needed) ---
    r82 = test_opcode_82(pp)
    _drain(pp)

    # --- opcode 90 op1 ---
    r90 = test_opcode_90_op1(pp)
    _drain(pp)

    # --- opcode 81 last (disconnects session) ---
    r81 = test_opcode_81(pp)
    # Do not attempt further reads — firmware closed the session

    print("\n=== Summary ===")
    print(f"  Opcode 81 (disconnect):     {'NO ACK' if r81 is None else f'byte={r81}'}")
    print(f"  Opcode 82 (set_continuous): {'NO ACK' if r82 is None else f'byte={r82}'}")
    print(f"  Opcode 90/1 (save_to_sd):   {'NO ACK' if r90 is None else f'byte={r90}'}")
    print(
        "\nUpdate PLAN_pypulsepal.md Priority 0b table with these results "
        "and note firmware version + model."
    )

    try:
        pp._arcom.close()
    except Exception:
        pass


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/test_ack_behaviour.py <serial_port>")
        sys.exit(1)
    run(sys.argv[1])
