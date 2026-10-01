# TinyPico LIS3DH 3-axis Accelerometer driver

This folder contains a custom test file based on the [LIS3DH driver by the TinyPico project](https://github.com/tinypico/tinypico-micropython/blob/master/lis3dh%20library/lis3dh.py).

The LIS3DH is a 3-axis linear Accelerometer. The driver is a part of the TinyPico project and
handles the configuration of the device, along with the reading and decoding of the devices data,
which is done through I2C registers.

The custom tests will test this processing and decoding logic, and ensure that it gets read
properly. The tests will also check that expected data is written to the devices registers when
applicable and that any expected exceptions get raised.

The tests will also try to find a few potential bugs/ oversights in the system that might've been
harder to detect and test without the use of the fake I2C, and could cause problems at runtime in a
real situation.
