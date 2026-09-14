# Tests for implemented classes and some examples

This folder contains tests for the implemented `fake_machine` classes, these tests check the
functionality of the implementations and make sure their features work correctly.

This folder also contains a few tests that feature the classes in more "real" environments by
mimicking a device with the test fakes, for demonstration and test purposes.

## Available tests

These are the tests available in this folder and what they're for:

| File                                                         | Description                                                                                                                                                                                                                                |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [test_uart.py](./test_uart.py)                               | Various tests that check the logic and functionality of `fake_machine.UART` with a few example usages as well (needs reworking).                                                                                                           |
| [test_uart_strategies.py](./test_uart_strategies.py)         | Various tests that test the functionality and logic of the `UARTResponseStrategy` classes                                                                                                                                                  |
| [test_pin.py](./test_pin.py)                                 | Tests for the `fake_machine.Pin` functionality and logic of the features like the re-initialization.                                                                                                                                       |
| [test_i2c.py](./test_i2c.py)                                 | Tests for the functionality and logic of the `fake_machine.I2C` and `fake_machine.I2CDevice` classes, testing their individual features (like the I2CDevice register blocks), as well as the logic of features like the re-initialization. |
| [test_i2c_ds1307.py](./test_i2c_ds1307.py)                   | Example tests showing `I2CDevice` being configured to mimick a `DS1307` RTC to test the drivers parsing                                                                                                                                    |
| [`test_machine_api_parity.py`](./test_machine_api_parity.py) | Test that compares the `fake_machine` contents to the `machine` contents extracted from the ESP32 and ensures all classes, methods, functions, and constants on the ESP32 are present in `fake_machine` and that constants values match.   |
