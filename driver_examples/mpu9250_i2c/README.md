# MPU-9250 9-axis motion tracking driver

This folder contains a custom test file based on the [tuupola micropython-mpu9250 driver](https://github.com/tuupola/micropython-mpu9250/tree/master).

The MPU-9250 is a combined chip that contains an MPU-6500 6-axis motion tracking sensor, along with
an extra 3-axis magnetometer. Making it a 9-axis motion tracking sensor. The driver has 3 separate
modules with classes for the MPU-6500 (`mpu6500.py`), the AK8963 magnetometer (`ak8963.py`), and the
MPU-9250 (`mpu9250.py`) which combines these two and exposes their functionality together.

This driver handles the configuration of these peripherals, along with the reading and decoding of
the devices data. These are all done through I2C registers.

The custom tests will properly test the processing and decoding logic and ensure that it reads data
properly. And that any expected raises are properly triggered when expected.<br>

The tests will also try to find a few potential bugs/ oversights in the system that might've been
harder to detect and test without the use of the fake I2C, and could cause problems at runtime in a
real situation.

## Discovered bugs

Through the testing a few bugs were discovered and are tested in tests that are marked as expected
failures as the driver doesn't handle them.

Here's an explanation of some of the main ones:

- `test_mpu6500_rejects_invalid_full_scale_selection`:
  - The MPU6500 constructor assigns the `_accel_so` attribute based on matching one of 4 expected
    values, if the input matches none of these then `_accel_so` will silently get set to
    `None`. Meaning that when the driver attempts to calculate the acceleration it will raise a
    runtime error from being unable to divide with `None`.
  - Expected failure would be the constructor raising an error before the device gets configured.
- `test_ak8963_calibrate_survives_axis_with_no_variation`:
  - The `AK8963.calibrate()` method doesn't handle situations where an axis never changes, which
    could be caused by something like a stuck sensor. This means that if the calibrate function
    reads the same axis value for each reading when it does the calculations it will end up with 0
    from the `max - min` and raise a `ZeroDivisionError` when attempting to divide with it.
  - Expected failure as raises from zero division when values don't change.
- `test_ak8963_magnetic_flags_sensor_overflow`:
  - The AK8963 has an `ST2` status register, which has a `HOFL` bit, that when set to 1 specifies
    that the magnetic sensor has overflowed (likely from interference) and that the data being read
    is invalid and should be discarded until another write is valid and changes this bit to 0.
  - The `.magnetic()` method reads this register, but only to allow the device to continue reading,
    they don't check the `HOFL` bit. This means that if the magnetic sensor overflows the data will
    still be read and returned.
  - Expected failure reason not be best solution, currently expects the method to raise in this
    situation but a proper solution would be either returning None, a 0 tuple, or some custom
    error. Raise check is just to demonstrate.
