from typing import Optional

import time

from dataclasses import dataclass

from ctypes import (
    c_bool,
    c_byte,
    c_ubyte,
    c_int,
    c_uint16,
    c_double,
    byref,
    create_string_buffer,
)

import numpy as np
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from dwfconstants import (
    hdwfNone,
    AnalogOutNodeCarrier,
    trigsrcExternal1,
    DwfTriggerSlopeRise,
    DwfStateDone,
    acqmodeScanShift,
)
from utils import dwf


@dataclass
class Acquisition:
    num_samples: int
    frequency: int

    @property
    def period(self):
        return self.num_samples / self.frequency


@dataclass
class AnalogAcquisition(Acquisition):
    channel: int
    channel_range: int


@dataclass
class DigitalAcquisition(Acquisition):
    pass


@dataclass
class Waveform:
    function: int
    frequency: int
    amplitude: float
    offset: float
    symmetry: float
    phase: float


@dataclass
class Pulse:
    channel: int


@dataclass
class Device:
    index: int
    name: str
    serial: str
    identifier: int
    revision: int
    num_digital_pins = 2
    acquire_digital = True

    def __post_init__(self):
        self.handle = c_int()

        self.is_open = False
        self.is_generating = False
        self.is_pulsing = False

        self.analog_acquisition = None
        self.digital_acquisition = None

    @property
    def is_active(self):
        self.is_generating or self.is_pulsing

    def open(self):
        if self.is_open:
            raise AttributeError("Device already open.")

        dwf.FDwfDeviceOpen(c_int(self.index), byref(self.handle))
        if self.handle.value == hdwfNone.value:
            raise IOError(f"Failed to open device {self.index}.")
        self.is_open = True

    def configure_acqusition(
        self,
        analog_acquisition: AnalogAcquisition,
        digital_acquisition: Optional[DigitalAcquisition],
    ):
        if not self.is_open:
            raise AttributeError("Cannot configure unopened device.")
        if self.is_active:
            raise AttributeError("Cannot configure active device.")

        dwf.FDwfAnalogInChannelEnableSet(
            self.handle, c_int(analog_acquisition.channel), c_bool(True)
        )
        dwf.FDwfAnalogInChannelRangeSet(
            self.handle,
            c_int(analog_acquisition.channel),
            c_double(analog_acquisition.channel_range),
        )
        dwf.FDwfAnalogInFrequencySet(
            self.handle, c_double(analog_acquisition.frequency)
        )
        dwf.FDwfAnalogInBufferSizeSet(
            self.handle, c_int(analog_acquisition.num_samples)
        )

        dwf.FDwfAnalogInTriggerSourceSet(self.handle, trigsrcExternal1)
        dwf.FDwfAnalogInTriggerConditionSet(self.handle, DwfTriggerSlopeRise)
        dwf.FDwfAnalogInTriggerPositionSet(
            self.handle, c_double(analog_acquisition.period / 2)
        )

        dwf.FDwfAnalogInConfigure(self.handle, c_int(0), c_int(1))

        self.analog_acquisition = analog_acquisition

        if digital_acquisition:
            digital_in_system_frequency = c_double()
            dwf.FDwfDigitalInInternalClockInfo(
                self.handle, byref(digital_in_system_frequency)
            )

            dwf.FDwfDigitalInAcquisitionModeSet(self.handle, acqmodeScanShift)
            dwf.FDwfDigitalInDividerSet(
                self.handle,
                c_int(
                    int(digital_in_system_frequency.value)
                    // digital_acquisition.frequency
                ),
            )
            dwf.FDwfDigitalInSampleFormatSet(self.handle, c_int(16))
            dwf.FDwfDigitalInBufferSizeSet(
                self.handle, c_int(digital_acquisition.num_samples)
            )
            dwf.FDwfDigitalInConfigure(self.handle, c_bool(0), c_bool(1))

            self.digital_acquisition = digital_acquisition

    def configure_generation(self, channel, waveform: Waveform):
        if not self.is_open:
            raise AttributeError("Cannot configure unopened device.")
        if self.is_active:
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
        if self.is_active:
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
        if not self.is_open:
            raise AttributeError("Cannot configure unopened device.")
        if self.is_active:
            raise AttributeError("Cannot start active device.")

        clock_frequency = waveform.frequency  # Hz

        # analog_buffer_size = c_int()
        # dwf.FDwfAnalogInBufferSizeInfo(self.handle, 0, byref(analog_buffer_size))
        # num_analog_acquisition_samples = analog_buffer_size.value
        num_analog_acquisition_samples = 100

        analog_acquisition_frequency = (
            num_analog_acquisition_samples * clock_frequency
        )  # Hz

        analog_acquisition = AnalogAcquisition(
            num_analog_acquisition_samples, analog_acquisition_frequency, channel, 5
        )

        digital_acquisition = None
        if self.acquire_digital:
            # digital_buffer_size = c_int()
            # dwf.FDwfDigitalInBufferSizeInfo(self.handle, byref(digital_buffer_size))
            # num_digital_acquisition_samples = digital_buffer_size.value
            num_digital_acquisition_samples = 200

            digital_acquisition_frequency = (num_digital_acquisition_samples // 10) * (
                clock_frequency
            )  # Hz

            digital_acquisition = DigitalAcquisition(
                num_digital_acquisition_samples, digital_acquisition_frequency
            )

        self.configure_acqusition(
            analog_acquisition,
            digital_acquisition,
        )
        self.configure_generation(channel, waveform)
        self.clock(clock_frequency)

        self.is_generating = True

    def acquire_data(self):
        if not self.is_open:
            raise AttributeError("Unopened device cannot acquire.")
        if not self.is_generating:
            raise AttributeError("Cannot acquire from inactive device.")

        analog_acquisition_status = c_byte()

        if self.acquire_digital:
            digital_acquisition_status = c_byte()
            num_valid_digital_acquisition_samples = c_int(0)

        analog_acquisition_data = (c_double * self.analog_acquisition.num_samples)()
        if self.acquire_digital:
            digital_acquisition_data = (
                c_uint16 * self.digital_acquisition.num_samples
            )()

        while self.is_generating:
            while True:
                dwf.FDwfAnalogInStatus(
                    self.handle, c_int(1), byref(analog_acquisition_status)
                )
                if analog_acquisition_status.value == DwfStateDone.value:
                    break
                time.sleep(0.001)
            dwf.FDwfAnalogInStatusData(
                self.handle,
                0,
                analog_acquisition_data,
                self.analog_acquisition.num_samples,
            )

            if self.acquire_digital:
                dwf.FDwfDigitalInStatus(
                    self.handle, c_int(1), byref(digital_acquisition_status)
                )
                dwf.FDwfDigitalInStatusSamplesValid(
                    self.handle, byref(num_valid_digital_acquisition_samples)
                )
                dwf.FDwfDigitalInStatusData(
                    self.handle,
                    byref(digital_acquisition_data),
                    num_valid_digital_acquisition_samples.value * 2,
                )

            parsed_digital_acquisition_data = []
            if self.acquire_digital:
                for pin in range(self.num_digital_pins):
                    pin_data = np.zeros(self.digital_acquisition.num_samples)
                    for i in range(num_valid_digital_acquisition_samples.value):
                        pin_data[i] = (digital_acquisition_data[i] >> pin) & 1
                    parsed_digital_acquisition_data.append(pin_data)

            yield np.fromiter(
                analog_acquisition_data, dtype=float
            ), parsed_digital_acquisition_data

    def acquire_plots(self):
        if not self.is_open:
            raise AttributeError("Unopened device cannot acquire.")
        if not self.is_generating:
            raise AttributeError("Cannot acquire from inactive device.")

        for analog_data, digital_data in self.acquire_data():
            figure = Figure()

            if self.acquire_digital:
                subfigures = figure.subfigures(1, 2)
                analog_figure = subfigures[0]
                digital_figure = subfigures[1]
            else:
                analog_figure = figure

            analog_axes = analog_figure.subplots()
            analog_axes.plot(
                np.arange(
                    0,
                    self.analog_acquisition.period,
                    1.0 / self.analog_acquisition.frequency,
                ),
                analog_data,
            )
            analog_axes.set_title("Analog")
            analog_axes.set_xlabel("Time (seconds)")

            if self.acquire_digital:
                digital_axes = digital_figure.subplots(
                    nrows=self.num_digital_pins, ncols=1, sharex=True
                )
                digital_axes[0].set_title("Digital")
                digital_axes[-1].set_xlabel("Time (seconds)")
                digital_figure.subplots_adjust(hspace=0)

                for axis in digital_axes:
                    axis.set_xlim(0, self.digital_acquisition.period)
                    axis.set_ylim(-0.1, 1.1)
                    axis.get_yaxis().set_visible(False)

                for pin in range(self.num_digital_pins):
                    digital_axes[pin].plot(
                        np.arange(
                            0,
                            self.digital_acquisition.period,
                            1.0 / self.digital_acquisition.frequency,
                        ),
                        digital_data[-1 - pin],
                    )

            yield figure

    def start_pulsing(self, pulse: Pulse):
        if not self.is_open:
            raise AttributeError("Unopened device cannot pulse.")
        if self.is_pulsing:
            raise AttributeError("Device already pulsing.")

        dwf.FDwfDigitalOutIdleSet(self.handle, c_int(pulse.channel), c_int(1))
        dwf.FDwfDigitalOutCounterInitSet(
            self.handle, c_int(pulse.channel), c_int(1), c_int(0)
        )
        dwf.FDwfDigitalOutCounterSet(
            self.handle, c_int(pulse.channel), c_int(0), c_int(0)
        )
        dwf.FDwfDigitalOutEnableSet(self.handle, c_int(pulse.channel), c_int(1))

        dwf.FDwfDigitalOutConfigure(self.handle, c_int(1))

        self.is_pulsing = True

    def stop_pulsing(self, pulse: Pulse):
        if not self.is_open:
            raise AttributeError("Unopened device cannot pulse.")
        if not self.is_pulsing:
            raise AttributeError("Device already not pulsing.")

        dwf.FDwfDigitalOutIdleSet(self.handle, c_int(pulse.channel), c_int(0))
        dwf.FDwfDigitalOutEnableSet(self.handle, c_int(pulse.channel), c_int(0))

        dwf.FDwfDigitalOutConfigure(self.handle, c_int(1))

        self.is_pulsing = False

    def stop(self):
        if not self.is_open:
            raise AttributeError("Cannot stop unopened device.")
        if not self.is_generating:
            raise AttributeError("Cannot stop inactive device.")

        dwf.FDwfDigitalOutReset(self.handle)
        dwf.FDwfAnalogOutReset(self.handle, c_int(self.analog_acquisition.channel))

        if self.acquire_digital:
            dwf.FDwfDigitalInReset(self.handle)
        dwf.FDwfAnalogInReset(self.handle)

        self.is_generating = False

    def close(self):
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
