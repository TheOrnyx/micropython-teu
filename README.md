# Testing ESP32 MicroPython code on UNIX (TEU)

This is the main repo for my ENGR489 capstone project "Testing Embedded Code Without the Embedded
System" focusing on supporting testing MicroPython code written for the ESP32 off-board using the
UNIX port.

This repo contains the implementations, tests, and documentation for my testable MicroPython module
implementations for parts like hardware peripherals (like the `machine` module). This repo also
contains tools and configurations for the CI/CD pipeline and docker container config.

[TOC]

## Project info

### Project Purpose

The purpose of this project is to address the problems with testing embedded MicroPython software
written for the generic ESP32 port without the need for the hardware. As testing the code off-board
is appealing due to some of the following problems with board testing:

- Configuring peripherals to reliably produce outputs for a specific test scenario (bad values,
  timeouts, etc) can be difficult and even impossible in some situations.
- Testing code on-board can be time-consuming due to slow upload and test times of the limited
  board specs. It also makes it more difficult to continuously test as you code.
- Automating code testing in a pipeline requires a dedicated board to be setup and configured for
  testing, which can cause bottlenecks in the pipeline.

MicroPython provides a `machine` module, which acts as a hardware abstraction layer and exposes
peripherals like GPIO Pins, UART devices, and RTCs as simple classes which are used by the embedded
code. It also provides unique `esp` and `esp32` modules on the ESP32 port which give access to more
low-level ESP32-specific functionality.

MicroPython also provides a minimal UNIX port, which runs on a regular Linux/Mac/BSD host and would
be ideal for off-board testing, but it only provides an almost-empty `machine` module, missing the
hardware peripheral classes and esp32-specific modules. This creates two problems for testing ESP32
code off-board using the UNIX port:

- Any module that does `import machine` and touches a hardware class can't be imported without
  causing an import error, which limits testing on the UNIX port.
- Even hardware-independent code isn't guaranteed to behave identically off-board, since some
  ports have functional differences (e.g. `time` on UNIX uses a different time epoch than the
  ESP32 port and `time.localtime()` returns a 9-tuple on UNIX vs. an 8-tuple on the ESP32).

### Project goal and outputs

The output of this project will be a distributable test library for the MicroPython UNIX port which
will provide an implementation of the missing `machine` module called `fake_machine` with test
versions of certain classes (see scope) and stubbed out dummies of any "out of scope" classes. It
will also include native support for shadowing the built-in `machine` module.

It will also provide stubbed out versions of the `esp` and `esp32` modules to prevent import
errors. A modified version of the `time` module will also be provided, which will bring the
outputs in-line with the ESP32 ports version.

The implemented custom `fake_machine` test classes will allow code written for the ESP32 to run
off-board and will allow test authors to test hardware-dependent code much easier on their host
system and in CI/CD pipelines without needing to create large custom test doubles or mess with
mocking frameworks. The classes will be API-identical to the on-board versions to reduce the need to
refactor the code under test. They will also have no dependencies on external libraries, meaning
they can be used in projects without needing extra dependencies.

The design of the test objects will focus on being easy-to-use and reasonably simple abstractions of
the original implementations, mimicking important hardware side-effects where needed.

### Project Scope

Due to the time-constraints it is infeasible to have fully designed and implemented versions of each
of the missing `machine` and `esp32` module classes. So the focus will be on classes that are used
by the James Quilty Environmental Monitoring project, as it gives a good reference for testing. The
main classes in question are `machine.UART`, `machine.Pin`, and `machine.I2C`, with the addition of
`machine.RTC` if time permits.

As previously mentioned, classes that are being considered "out of scope" will be implemented as
basic stubbed out dummy objects to fill out the expected API and allow other code to run without
import errors. This will also provide a good jumping-off point for future projects to expand on.

### Implemented features

So far these are the implemented classes, their on-board counterpart and any notes.

> [!note]

> Most of the "Basic stub"/ "Basic dummy" classes are the stubbed out "out-of-scope" classes,
> they're mostly minimal implementations to fill out the required API to prevent `ImportError`s.
>
> Implementations that perform some basic simulation or expose attributes relating to return values
> that can be configured are considered "basic stub" classes, whereas the implementations with almost no
> underlying logic are considered "basic dummy" classes.

| Test object    | Board version      | Status                        | Notes                                                                                                                                                                                                                  |
| -------------- | ------------------ | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fake_machine` | `machine`          | WIP                           | Following table entries are `fake_machine` classes (`.UART` means `fake_machine.UART`)                                                                                                                                 |
| `.UART`        | `machine.UART`     | Mostly Complete               | Missing a few features around IRQ and attribute validation                                                                                                                                                             |
| `.Pin`         | `machine.Pin`      | Mostly Complete               | Basically fully implemented, only missing high-impedance state logic and maybe additional test helpers                                                                                                                 |
| `.I2C`         | `machine.I2C`      | Basic implementation complete | A basic version of the class is implemented, further work would involve more configuration options, better `SoftI2C` support, and Pin operations                                                                       |
| `.SoftI2C`     | `machine.SoftI2C`  | Minimal implementation        | Is implemented as a basic subclass of `fake_machine.I2C` with a singleton instead of multiton, needs more work for future.                                                                                             |
| `.Signal`      | `machine.Signal`   | Basic dummy                   | Basic stubbed out dummy that wraps around a pin, reads and sets the value.                                                                                                                                             |
| `.ADC`         | `machine.ADC`      | Basic stub                    | Basic stub with attributes to set the `read_u6` and `read_uv` return values, needs better block support and ID validation in future. Would also need better support for programming the responses (list, callback etc) |
| `.ADCBlock`    | `machine.ADCBlock` | Basic dummy                   | Basic stubbed out dummy, further work would need implementing the block system properly and keeping registry of instances.                                                                                             |
| `.DAC`         | `machine.DAC`      | Basic dummy                   | Basic stubbed out dummy, holds a pin but doesn't do anything.                                                                                                                                                          |
| `.PWM`         | `machine.PWM`      | Basic stub                    | Basic stub with board logic implemented for converting the different `duty` values. Future work needs the last used duty type logic and proper pin interfacing.                                                        |
| `.SPI`         | `machine.SPI`      | Basic stub                    | Basic stubbed out dummy, very basic start for SPI with just a read buffer for read response, future work would be something akin to UART with more customizable response handling                                      |
| `.SoftSPI`     | `machine.SoftSPI`  | Basic stub                    | Basic stubbed out dummy, subclass of SPI with modified `__init__` and `__repr__`, future work would be based on full SPI implementation.                                                                               |
| `.I2S`         | `machine.I2S`      | Basic dummy                   | Basic stubbed out dummy, doesn't really have any functionality besides returning empty on read.                                                                                                                        |
| `.RTC`         | `machine.RTC`      | Basic stub                    | Basic stub which holds a static datetime which can be set and read, also has a basic faked memory. Future work could be an actual simulated RTC implementation                                                         |
| `.Timer`       | `machine.Timer`    | Basic dummy                   | Basic stubbed out dummy, doesn't have any functionality besides the basic period calculations for storing and printing. Future work would ideally implement a basic timer system.                                      |
| `.Counter`     | `machine.Counter`  | Basic dummy                   | Basic stubbed out dummy, not much functionality. Future work would involve properly implementing.                                                                                                                      |
| `.Encoder`     | `machine.Encoder`  | Basic dummy                   | Basic stubbed out dummy, not much functionality. Future work would involve properly implementing.                                                                                                                      |
| `.WDT`         | `machine.WDT`      | Basic dummy                   | Basic stubbed out dummy, not much functionality to implement honestly, not even sure how you'd simulate a reset.                                                                                                       |
| `.SDCard`      | `machine.SDCard`   | Basic dummy                   | Very basic stubbed out dummy, basically no functionality and `AbstractBlockDev` methods just return 0. Further work could make a basic faked filesystem or at least stub out the blockdev functions a bit better.      |
| `.TouchPad`    | `machine.TouchPad` | Basic stub                    | Very basic stub, just returns a read_val. Class not in regular machine docs, only ESP32 port docs.                                                                                                                     |

The following are classes that are specified in the main MicroPython docs but are unavailable on the
generic ESP32 port so they are unimplemented.

| Class               | Reason for missing                                                                                                                  |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `machine.I2CTarget` | Excluded from build in `mpconfigport`, only available on newer chips                                                                |
| `machine.CAN`       | Not available on ESP32                                                                                                              |
| `machine.SD`        | Only available on the cc3200 port                                                                                                   |
| `machine.USBDevice` | Seems to be only available on some newer ESP32 models. Is included as `SOC_USB_OTG_SUPPORTED`, but can't find def for generic ESP32 |

______________________________________________________________________

## Project Structure

The contents of the repository's folders:

- [ci/](ci/) - Contains the dockerfile for building the custom MicroPython docker container image
- [docs/](docs/) - Contains design info and documentation for my implementations. Will contain examples and guides for using the objects later.
- [src/](src/) - Contains the code for the modules as well as tests for them which ensure they work and perform as expected.
- [tools/](tools/) - Contains tool scripts for helping out with various things.

______________________________________________________________________

## Basic Usage

Here's a very basic guide on how to use our custom `fake_machine` module.

> [!note]
> For more in-depth information in using our module and its test classes please check the
> [docs/](docs/) folder.

```python
# In a test file
import fake_machine

# Call the shadow method to shadow the built-in machine before any code uses machine
fake_machine.shadow_builtin_machine()

# Now whenever code imports machine it will be using the fake_machine
import machine

# Now create some objects and test stuff
pin_f = fake_machine.Pin(5)
pin_m = machine.Pin(5)
pin_m is pin_f  # Will be true as they're using same class
```
