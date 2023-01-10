"""
   DWF Python Example
   Author:  Digilent, Inc.
   Revision:  2022-01-11

   Requires:                       
       Python 2.7, 3
"""

import sys
import time

from ctypes import *

import numpy as np
import matplotlib.pyplot as plt

from dwfconstants import *

if sys.platform.startswith("win"):
    dwf = cdll.dwf
elif sys.platform.startswith("darwin"):
    dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
else:
    dwf = cdll.LoadLibrary("libdwf.so")

NUM_PINS = 16

digital_out_system_frequency = c_double()
digital_in_system_frequency = c_double()

acquisition_frequency = 100
num_acqusition_samples = 1000
acquisition_period = num_acqusition_samples // acquisition_frequency
acquisition_samples = (c_uint16 * num_acqusition_samples)()

acquisition_status = c_byte()
num_valid_acquisition_samples = c_int(0)

version = create_string_buffer(16)
dwf.FDwfGetVersion(version)
print("DWF Version: " + str(version.value))

print("Opening first device")
device = c_int()
dwf.FDwfDeviceOpen(c_int(-1), byref(device))

if device.value == 0:
    szerr = create_string_buffer(512)
    dwf.FDwfGetLastErrorMsg(szerr)
    print(str(szerr.value))
    print("failed to open device")
    quit()

dwf.FDwfDigitalOutInternalClockInfo(device, byref(digital_out_system_frequency))
dwf.FDwfDigitalInInternalClockInfo(device, byref(digital_in_system_frequency))

# COUNTER
clock_frequency = 1  # Hz
dwf.FDwfDigitalOutEnableSet(device, c_int(0), c_int(1))
dwf.FDwfDigitalOutDividerSet(
    device, c_int(0), c_int(int(digital_out_system_frequency.value) // clock_frequency)
)
dwf.FDwfDigitalOutCounterSet(device, c_int(0), c_int(1), c_int(1))
dwf.FDwfDigitalOutConfigure(device, c_int(1))

# ACQUISITION
dwf.FDwfDigitalInAcquisitionModeSet(device, acqmodeScanShift)
dwf.FDwfDigitalInDividerSet(
    device, c_int(int(digital_in_system_frequency.value) // acquisition_frequency)
)
dwf.FDwfDigitalInSampleFormatSet(device, c_int(16))
dwf.FDwfDigitalInBufferSizeSet(device, c_int(num_acqusition_samples))
dwf.FDwfDigitalInConfigure(device, c_bool(0), c_bool(1))

# PLOT
figure, axes = plt.subplots(nrows=NUM_PINS, ncols=1, sharex=True)

figure.supxlabel("Time (seconds)")
figure.supylabel("Logical State (0/1)")
plt.subplots_adjust(hspace=0)
# figure.tight_layout()

for axis in axes:
    axis.set_xlim(0, acquisition_period)
    axis.set_ylim(-0.1, 1.1)
    axis.get_yaxis().set_visible(False)

plots = [axis.plot([], [])[0] for axis in axes]
for plot in plots:
    plot.set_xdata(np.arange(0, acquisition_period, 1.0 / acquisition_frequency))

try:
    while True:
        dwf.FDwfDigitalInStatus(device, c_int(1), byref(acquisition_status))
        dwf.FDwfDigitalInStatusSamplesValid(
            device, byref(num_valid_acquisition_samples)
        )
        dwf.FDwfDigitalInStatusData(
            device, byref(acquisition_samples), num_valid_acquisition_samples.value * 2
        )

        for pin in range(NUM_PINS):
            data = np.zeros(num_acqusition_samples)
            for i in range(num_valid_acquisition_samples.value):
                data[i] = (acquisition_samples[i] >> pin) & 1
            plots[(NUM_PINS - 1) - pin].set_ydata(data)

        plt.draw()
        plt.pause(0.01)
except KeyboardInterrupt:
    pass

dwf.FDwfDeviceCloseAll()
