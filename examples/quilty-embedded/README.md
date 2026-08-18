# Tests for the James Quilty embedded environment project

This folder contains tests for the James Quilty ["Open Data Recorder for Environmental Monitoring"](https://gitlab.ecs.vuw.ac.nz/QuiltyGroup/Research/ENGR489/Environmental-Monitoring-2020/engr489-project) projects embedded MicroPython software.

These tests make use of our custom test library and its classes to demonstrate how they can be
integrated into existing codebases to more easily test the logic (along with edge cases). They also
serve as a good example of how the test objects can be used.

## Running the tests

To avoid including the entire reference project in my repo this folder only contains the tests I've created.<br>
To run them you'll need to both copy these tests to the proper location along with including our custom test classes.

1. First copy the tests to the cloned Quilty projects embedded test folder at `software/device/embedded/src/test/`.
1. Copy our test library to the embedded codebases `lib` folder at `software/device/embedded/src/lib/`.
1. Start `micropython` from the embedded codebases `src` folder at `software/device/embedded/src/`.
1. Run the following commands in the REPL to run the test you want:
   ```python
   from lib import unittest
   unittest.main("test/<name-of-test>")  # Replace with the name of your test
   # For example: unittest.main("test/test_modem_unix")
   ```

## Files

- [test_modem_unix.py](test_modem_unix.py) contains tests for the `modem` driver.
