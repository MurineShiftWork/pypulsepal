# Vendored from: pybpodapi.com.arcom (https://github.com/pybpod/pybpod-api)
# Source package version: pybpod-api 1.8.2
# License: MIT  Copyright (c) 2019 Scientific Software Platform, Champalimaud Foundation
# Authors: Joshua Sanders, Carlos Mão de Ferro, Ricardo Ribeiro, Luís Teixeira
# Vendored to remove pybpod-api as a runtime dependency of pypulsepal.

import logging
import struct

import numpy as np
import serial

logger = logging.getLogger(__name__)


class DataType(object):
    def __init__(self, name, size):
        self.name = name
        self.size = size

    def __str__(self):
        return self.name


class ArduinoTypes(object):
    BYTE = DataType("byte", 1)
    CHAR = DataType("char", 1)
    UINT8 = DataType("uint8", 1)
    INT16 = DataType("int16", 2)
    UINT16 = DataType("uint16", 2)
    UINT32 = DataType("uint32", 4)
    UINT64 = DataType("uint64", 8)
    FLOAT32 = DataType("float32", 4)
    FLOAT64 = DataType("float64", 8)

    @staticmethod
    def get_array(array, dtype):
        if dtype == ArduinoTypes.CHAR or dtype == ArduinoTypes.UINT8:
            return ArduinoTypes.get_uint8_array(array)
        elif dtype == ArduinoTypes.UINT16:
            return ArduinoTypes.get_uint16_array(array)
        elif dtype == ArduinoTypes.UINT32 or dtype == ArduinoTypes.FLOAT:
            return ArduinoTypes.get_uint32_array(array)
        else:
            return None

    @staticmethod
    def get_uint8_array(array):
        return np.array(array, dtype=str(ArduinoTypes.UINT8)).tobytes()

    @staticmethod
    def get_int16_array(array):
        return np.array(array, dtype=str(ArduinoTypes.INT16)).tobytes()

    @staticmethod
    def get_uint16_array(array):
        return np.array(array, dtype=str(ArduinoTypes.UINT16)).tobytes()

    @staticmethod
    def get_uint32_array(array):
        return np.array(array, dtype=str(ArduinoTypes.UINT32)).tobytes()

    @staticmethod
    def get_float(value):
        return struct.pack("<f", value)

    @staticmethod
    def cvt_float32(message_bytes):
        return struct.unpack("<f", message_bytes)[0]

    @staticmethod
    def cvt_float64(message_bytes):
        return struct.unpack("<d", message_bytes)[0]

    @staticmethod
    def cvt_int64(message_bytes):
        return int.from_bytes(message_bytes, byteorder="little")

    @staticmethod
    def cvt_uint32(message_bytes):
        return struct.unpack("<L", message_bytes)[0]

    @staticmethod
    def cvt_uint64(message_bytes):
        return struct.unpack("<Q", message_bytes)[0]


class ArCOM(object):
    """ArCOM is an interface to simplify data transactions between Arduino and Python."""

    def open(self, serial_port, baudrate=115200, timeout=1):
        self.serial_object = serial.Serial(
            serial_port, baudrate=baudrate, timeout=timeout
        )
        return self

    def close(self):
        self.serial_object.close()

    def bytes_available(self):
        return self.serial_object.inWaiting()

    def write_char(self, value):
        self.serial_object.write(str.encode(value))

    def write_array(self, array):
        self.serial_object.write(array)

    def read_byte(self):
        return self.serial_object.read(ArduinoTypes.BYTE.size)

    def read_char(self):
        return self.serial_object.read(ArduinoTypes.CHAR.size).decode("utf-8")

    def read_uint8(self):
        return int.from_bytes(
            self.serial_object.read(ArduinoTypes.UINT8.size), byteorder="little"
        )

    def read_uint16(self):
        return int.from_bytes(
            self.serial_object.read(ArduinoTypes.UINT16.size), byteorder="little"
        )

    def read_uint32(self):
        return int.from_bytes(
            self.serial_object.read(ArduinoTypes.UINT32.size), byteorder="little"
        )

    def read_uint64(self):
        return int.from_bytes(
            self.serial_object.read(ArduinoTypes.UINT64.size), byteorder="little"
        )

    def read_float32(self):
        return struct.unpack("<f", self.serial_object.read(ArduinoTypes.FLOAT32.size))[0]

    def read_bytes_array(self, array_len=1):
        return [self.read_byte() for _ in range(array_len)]

    def read_char_array(self, array_len=1):
        return [self.read_char() for _ in range(array_len)]

    def read_uint8_array(self, array_len=1):
        return [self.read_uint8() for _ in range(array_len)]

    def read_uint16_array(self, array_len=1):
        return [self.read_uint16() for _ in range(array_len)]

    def read_uint32_array(self, array_len=1):
        return [self.read_uint32() for _ in range(array_len)]

    def read_float32_array(self, array_len=1):
        return [self.read_float32() for _ in range(array_len)]
