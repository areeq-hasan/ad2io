import time

from dataclasses import dataclass

from ctypes import c_bool, c_byte, c_ubyte, c_int, c_double, byref, create_string_buffer

import numpy as np

from dwfconstants import (
    hdwfNone,
    AnalogOutNodeCarrier,
    trigsrcExternal1,
    DwfTriggerSlopeRise,
    DwfStateDone,
)
from utils import dwf


@dataclass
class Acquisition:
    channel: int
    num_samples: int
    frequency: float
    channel_range: int

    @property
    def period(self):
        return self.num_samples / self.frequency


@dataclass
class Waveform:
    function: int
    frequency: int
    amplitude: float
    offset: float
    symmetry: float
    phase: float


@dataclass
class Device:
    index: int
    name: str
    serial: str
    identifier: int
    revision: int

    def __post_init__(self):
        self.handle = c_int()

        self.is_open = False
        self.is_generating = False

        self.acquisition = None

    def open(self):
        if self.is_open:
            raise AttributeError("Device already open.")

        dwf.FDwfDeviceOpen(c_int(self.index), byref(self.handle))
        if self.handle.value == hdwfNone.value:
            raise IOError(f"Failed to open device {self.index}.")
        self.is_open = True

    def configure_acqusition(self, acquisition):
        if not self.is_open:
            raise AttributeError("Cannot configure unopened device.")
        if self.is_generating:
            raise AttributeError("Cannot configure active device.")

        dwf.FDwfAnalogInChannelEnableSet(
            self.handle, c_int(acquisition.channel), c_bool(True)
        )
        dwf.FDwfAnalogInChannelRangeSet(
            self.handle, c_int(acquisition.channel), c_double(acquisition.channel_range)
        )
        dwf.FDwfAnalogInFrequencySet(self.handle, c_double(acquisition.frequency))
        dwf.FDwfAnalogInBufferSizeSet(self.handle, c_int(acquisition.num_samples))

        dwf.FDwfAnalogInTriggerSourceSet(self.handle, trigsrcExternal1)
        dwf.FDwfAnalogInTriggerConditionSet(self.handle, DwfTriggerSlopeRise)
        dwf.FDwfAnalogInTriggerPositionSet(
            self.handle, c_double(acquisition.period / 2)
        )

        dwf.FDwfAnalogInConfigure(self.handle, c_int(0), c_int(1))

        self.acquisition = acquisition

    def configure_generation(self, channel, waveform: Waveform):
        if not self.is_open:
            raise AttributeError("Cannot configure unopened device.")
        if self.is_generating:
            raise AttributeError("Cannot configure active device.")

        dwf.FDwfDeviceAutoConfigureSet(self.handle, c_int(0))

        dwf.FDwfAnalogOutNodeEnableSet(
            self.handle, c_int(channel), AnalogOutNodeCarrier, c_bool(True)
        )
        dwf.FDwfAnalogOutNodeFunctionSet(
            self.handle,
            c_int(channel),
            AnalogOutNodeCarrier,
            c_ubyte(waveform.function),
        )
        dwf.FDwfAnalogOutNodeFrequencySet(
            self.handle,
            c_int(channel),
            AnalogOutNodeCarrier,
            c_double(waveform.frequency),
        )
        dwf.FDwfAnalogOutNodeAmplitudeSet(
            self.handle,
            c_int(channel),
            AnalogOutNodeCarrier,
            c_double(waveform.amplitude),
        )
        dwf.FDwfAnalogOutNodeOffsetSet(
            self.handle, c_int(channel), AnalogOutNodeCarrier, c_double(waveform.offset)
        )
        dwf.FDwfAnalogOutNodeSymmetrySet(
            self.handle,
            c_int(channel),
            AnalogOutNodeCarrier,
            c_double(waveform.symmetry),
        )
        dwf.FDwfAnalogOutNodePhaseSet(
            self.handle, c_int(channel), AnalogOutNodeCarrier, c_double(waveform.phase)
        )

        dwf.FDwfAnalogOutTriggerSourceSet(self.handle, c_int(0), trigsrcExternal1)
        dwf.FDwfAnalogOutTriggerSlopeSet(self.handle, c_int(0), DwfTriggerSlopeRise)
        dwf.FDwfAnalogOutRunSet(self.handle, c_int(0), c_double(1 / waveform.frequency))
        dwf.FDwfAnalogOutRepeatSet(self.handle, c_int(0), c_int(0))
        dwf.FDwfAnalogOutRepeatTriggerSet(self.handle, c_int(0), c_bool(True))

        dwf.FDwfAnalogOutConfigure(self.handle, channel, c_bool(True))

        dwf.FDwfDeviceAutoConfigureSet(self.handle, c_int(1))

    def clock(self, frequency):
        if not self.is_open:
            raise AttributeError("Cannot configure unopened device.")
        if self.is_generating:
            raise AttributeError("Cannot configure active device.")

        system_frequency = c_double()
        dwf.FDwfDigitalOutInternalClockInfo(self.handle, byref(system_frequency))

        dwf.FDwfDigitalOutEnableSet(self.handle, c_int(0), c_int(1))
        dwf.FDwfDigitalOutDividerSet(
            self.handle,
            c_int(0),
            c_int(int(system_frequency.value) // frequency),
        )
        dwf.FDwfDigitalOutCounterSet(self.handle, c_int(0), c_int(1), c_int(1))
        dwf.FDwfDigitalOutConfigure(self.handle, c_int(1))

    def start(self, channel, waveform: Waveform):
        clock_frequency = waveform.frequency  # Hz

        buffer_size = c_int()
        dwf.FDwfAnalogInBufferSizeInfo(self.handle, 0, byref(buffer_size))
        num_acquisition_samples = buffer_size.value

        clock_period = 1 / clock_frequency  # seconds
        acquisition_period = clock_period  # seconds
        frequency = num_acquisition_samples / acquisition_period  # Hz

        self.configure_acqusition(
            Acquisition(channel, num_acquisition_samples, frequency, 5)
        )
        self.configure_generation(channel, waveform)
        self.clock(clock_frequency)

        self.is_generating = True

    def acquire(self):
        if not self.is_open:
            raise AttributeError("Unopened device cannot acquire.")

        status = c_byte()
        data = (c_double * self.acquisition.num_samples)()

        while self.is_generating:
            while True:
                dwf.FDwfAnalogInStatus(self.handle, c_int(1), byref(status))
                if status.value == DwfStateDone.value:
                    break
                time.sleep(0.001)

            dwf.FDwfAnalogInStatusData(
                self.handle, 0, data, self.acquisition.num_samples
            )
            yield np.fromiter(data, dtype=float)

    def stop(self):
        if not self.is_open:
            raise AttributeError("Cannot stop unopened device.")
        if not self.is_generating:
            raise AttributeError("Cannot stop inactive device.")

        dwf.FDwfAnalogOutReset(self.handle, c_int(self.acquisition.channel))
        dwf.FDwfAnalogInReset(self.handle)
        self.is_generating = False

    def close(self):
        print("called!")
        if not self.is_open:
            raise AttributeError("Device already closed.")
        dwf.FDwfDeviceClose(self.handle)
        self.is_open = False


class Devices:
    def __init__(self):
        self.available = []
        self.active_index = None

        self.load()

    def load(self):
        devices = []

        num_devices = c_int()
        dwf.FDwfEnum(c_int(0), byref(num_devices))

        name = create_string_buffer(64)
        serial = create_string_buffer(16)
        identifier = c_int()
        revision = c_int()
        for index in range(num_devices.value):
            dwf.FDwfEnumDeviceName(c_int(index), name)
            dwf.FDwfEnumSN(c_int(index), serial)
            dwf.FDwfEnumDeviceType(c_int(index), byref(identifier), byref(revision))
            devices.append(
                Device(
                    index,
                    name.value.decode(),
                    serial.value.decode()[3:],
                    identifier.value,
                    revision.value,
                )
            )

        self.available = devices
        self.active_index = None

    def activate(self, device_index):
        self.active_index = device_index
        self.active.open()

    def deactivate(self):
        if self.active_index is not None:
            self.active.close()
        self.active_index = None

    @property
    def active(self):
        if self.active_index is None:
            raise AttributeError("No device has been activated.")
        return self.available[self.active_index]

    def close(self):
        dwf.FDwfDeviceCloseAll()
