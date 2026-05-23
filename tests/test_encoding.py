import numpy as np

from pypulsepal.definitions import PULSEPAL_CYCLE_FREQUENCY
from pypulsepal.utils import encode_message, volts_to_bytes

DAC_MODEL_1 = 255
DAC_MODEL_2 = 65535


class TestVoltsToBytes:
    def test_min_voltage_model2(self):
        assert volts_to_bytes(-10.0, DAC_MODEL_2) == 0

    def test_max_voltage_model2(self):
        assert volts_to_bytes(10.0, DAC_MODEL_2) == DAC_MODEL_2

    def test_zero_voltage_model2(self):
        result = volts_to_bytes(0.0, DAC_MODEL_2)
        assert result == np.ceil(DAC_MODEL_2 / 2)

    def test_min_voltage_model1(self):
        assert volts_to_bytes(-10.0, DAC_MODEL_1) == 0

    def test_max_voltage_model1(self):
        assert volts_to_bytes(10.0, DAC_MODEL_1) == DAC_MODEL_1

    def test_midpoint_model1(self):
        result = volts_to_bytes(0.0, DAC_MODEL_1)
        assert result == np.ceil(DAC_MODEL_1 / 2)

    def test_positive_voltage_model2(self):
        result = volts_to_bytes(5.0, DAC_MODEL_2)
        expected = np.ceil(((5.0 + 10) / 20.0) * DAC_MODEL_2)
        assert result == expected

    def test_negative_voltage_model2(self):
        result = volts_to_bytes(-5.0, DAC_MODEL_2)
        expected = np.ceil(((-5.0 + 10) / 20.0) * DAC_MODEL_2)
        assert result == expected


class TestEncodeMessage:
    def test_scalar_uint8(self):
        assert encode_message(73, encoding="uint8") == bytes([73])

    def test_scalar_uint16_little_endian(self):
        result = encode_message(1000, encoding="uint16")
        assert result == (1000).to_bytes(2, "little")

    def test_scalar_uint32_little_endian(self):
        result = encode_message(100000, encoding="uint32")
        assert result == (100000).to_bytes(4, "little")

    def test_list_uint8(self):
        assert encode_message([1, 2, 3], encoding="uint8") == bytes([1, 2, 3])

    def test_list_uint32(self):
        values = [20, 20000]
        result = encode_message(values, encoding="uint32")
        assert result == np.array(values, dtype="uint32").tobytes()

    def test_list_uint16(self):
        values = [0, 32768, 65535]
        result = encode_message(values, encoding="uint16")
        assert result == np.array(values, dtype="uint16").tobytes()

    def test_zero_uint8(self):
        assert encode_message(0, encoding="uint8") == b"\x00"

    def test_max_uint8(self):
        assert encode_message(255, encoding="uint8") == b"\xff"

    def test_multiple_parts_joined(self):
        a = encode_message(1, encoding="uint8")
        b = encode_message(2, encoding="uint8")
        assert a + b == bytes([1, 2])


class TestTimeScaling:
    def test_1ms_to_cycles(self):
        assert int(0.001 * PULSEPAL_CYCLE_FREQUENCY) == 20

    def test_1s_to_cycles(self):
        assert int(1.0 * PULSEPAL_CYCLE_FREQUENCY) == 20000

    def test_zero_duration(self):
        assert int(0.0 * PULSEPAL_CYCLE_FREQUENCY) == 0

    def test_cycle_frequency_value(self):
        assert PULSEPAL_CYCLE_FREQUENCY == 20000
