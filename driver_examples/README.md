# Driver example tests

This folder will contain subfolders that consist of custom test files that are based on existing
open source MicroPython drivers available on the internet.

These will be drivers written for `UART` or `I2C` peripheral devices and will have a lot of internal
parsing and validation logic which isn't very well tested (or could be tested better).

The code for these drivers will be vendored into their respective folders, with proper licensing and
attribution attached. The drivers may be modified slightly to simplify the testing, such as reducing
the time for sleeps in timeout tests. But the main logic will be left as-is.

The custom tests will use the `teu.fake_machine` test library and the configurable
`fake_machine.UART`, `fake_machine.I2C` classes to mimic the devices responses and validate how the
driver parses them. It will also test how the driver handles faults in responses (such as an invalid
response) and that expected failures are handled properly without causing unexpected runtime errors.

And if any major bugs are found (especially ones that might be hard to test for without the fake
device), then tests marked as expected failure will be written for them.

> [!note]
> The reason the expected failure tests will fail are either from potential ways the driver could
> address the bug, or ways the driver fails to handle edge cases and produces a runtime error.
>
> For example the MPU9250 `test_mpu6500_rejects_invalid_full_scale_selection` test fails for an
> expected scenario where the constructor would raises on an invalid `accel_fs` value and prevent
> the future runtime error during reading, this might not be the only fix for the bug but it's a
> stand in for a potential good solution.

These tests will be written as if the `teu` library is in the path when running, so they will use
plain `import teu` rather than a direct relative import like `from lib import teu`.

The available tests will be runnable through the `run_driver_tests.py` tools script, since
MicroPython testing can be quite fiddly to do manually.

## Tests

These are the tests currently present in this folder, along with a brief description of what they're
for and a link to the original driver repo.

| Folder                                   | Description                                                                                                                        | Source                                                                                                                                                                                                                 |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [sara_modem_quilty/](sara_modem_quilty/) | Tests for the UART-based SARA-R4 modem driver from the James Quilty Environmental Monitoring Project                               | [drivers/modem](https://gitlab.ecs.vuw.ac.nz/QuiltyGroup/Research/ENGR489/Environmental-Monitoring-2020/engr489-project/-/blob/0f039cd59d1efa295b878b15110db787b9a570f1/software/device/embedded/src/drivers/modem.py) |
| [pythings_sim800l/](pythings_sim800l/)   | Tests for the UART-based SIM800L GSM/GPRS modem driver for the PythingsOS project                                                  | [pythings/Drivers](https://github.com/pythings/Drivers)                                                                                                                                                                |
| [mpu9250_i2c/](mpu9250_i2c/)             | Tests for the I2C-based MPU-9250 9-axis motion tracking device (combination 6-axis gyroscope/accelerator and 3-axis magnetometer). | [tuupola/micropython-mpu9250](https://github.com/tuupola/micropython-mpu9250/tree/master)                                                                                                                              |
| [tinypico_lis3dh/](tinypico_lis3dh/)     | Tests for the I2C-based LIS3DH 3-axis Accelerometer driver by TinyPico.                                                            | [tinypico-micropython/lis3dh library/lis3dh.py](https://github.com/tinypico/tinypico-micropython/blob/master/lis3dh%20library/lis3dh.py)                                                                               |

## Running the tests:

The MicroPython script in `tools/run_driver_tests.py` is able to run these driver tests and accepts a CLI arg to only run a specific driver test:

```bash
# From project root

# Run all tests
micropython tools/run_driver_tests.py

# Run only a specific test (partially matches so "unix" runs sara_modem_quilty.test_modem_unix)
micropython tools/run_driver_tests.py unix

# Can also run multiple (but not too useful since not many tests)
micropython tools/run_driver_tests.py unix sim800 # Runs sim800 and modem tests
```
