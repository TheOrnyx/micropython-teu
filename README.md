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
classes for peripherals like GPIO Pins, UART devices, I2C buses, RTCs, etc, which are used by the
embedded code. It also provides unique `esp` and `esp32` modules on the ESP32 port which give access
to more low-level ESP32-specific functionality.

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

The output of this project will be a distributable test library for the MicroPython UNIX port called
`teu`. This library will provide an implementation of the esp32s `machine` module called
`fake_machine` (as `teu.fake_machine`) with configurable test fake versions of certain classes (see
scope) and stubbed out dummies of any "out of scope" classes. It will also include native support
for shadowing the built-in modules we override with our test versions, so code that does `import machine` receives `fake_machine`.

It will also provide stubbed out versions of the `esp` and `esp32` modules to prevent import
errors. A modified version of the `time` module will also be provided, which will bring the
outputs in-line with the ESP32 ports version.

The implemented custom `fake_machine` test classes will allow code written for the ESP32 to run
off-board and will allow test authors to test hardware-dependent code much easier on their host
system and in CI/CD pipelines without needing to create large custom test doubles or mess with
mocking frameworks. The classes will be API-identical to the on-board versions so ESP32 code won't
error from missing functions or constants. They will also have no dependencies on external
libraries, meaning they can be used in projects without needing extra dependencies.

The design of the test objects will focus on being easy-to-use and reasonably simple abstractions of
the original implementations, mimicking important hardware side-effects where needed.

#### Basic test container

I will also produce a docker container image which will shadow the specific built-in modules
(`time`, `machine`, `esp*`) with our custom module versions. This means that users that just want to
test their basic ESP32 code without worrying about import errors or time calculation problems can
use the container which will ensure calls to `import time`, `import machine`, etc, will receive our
custom modules like so:

```python
(mp-esp32-unix) [12:03:50] ornyx@PossumTop ~/D/u/2/E/micropython-esp32-unix [SIGINT]
> podman run -it gitlab.ecs.vuw.ac.nz:45678/course-work/project489/2026/project/silouzaki/micropython-esp32-unix:mp_v1.29.0-with-stubs
root@d02a4fa91540:/# ls /usr/lib/micropython
machine  time.py  unittest
root@d02a4fa91540:/# micropython
MicroPython cc12057519 on 2026-09-16; linux [GCC 13.3.0] version
Type "help()" for more information.
>>> import machine
>>> machine
<module 'machine' from '/usr/lib/micropython/machine/__init__.py'>
>>> import time
>>> time
<module 'time' from '/usr/lib/micropython/time.py'>
>>> time.localtime(0)  # 2000 epoch instead of built-in unix 1970 epoch
(2000, 1, 1, 0, 0, 0, 5, 1)
>>> machine.UART(1)
UART(1, baudrate=9600, bits=8, parity=None, stop=1, tx=5, rx=4, rts=-1, cts=-1, txbuf=256, rxbuf=256, timeout=0, timeout_char=0, irq=0)
```

### Project Scope

Due to the time-constraints it is infeasible to have fully designed and implemented versions of each
of the missing `machine` and `esp32` module classes. So the focus will be on classes that are used
by the James Quilty Environmental Monitoring project, as it gives a good reference for testing. The
main classes in question are `machine.UART`, `machine.Pin`, and `machine.I2C`, with the addition of
`machine.RTC` if time permits.

As previously mentioned, classes that are being considered "out of scope" will be implemented as
basic stubbed out dummy objects to fill out the expected API and allow other code to run without
import errors. This will also provide a good jumping-off point for future projects to expand on.

### Implemented modules and classes

So far these are the implemented classes/ modules, their on-board counterpart and any notes.

These implemented modules are also parity tested to ensure the basic implementations match the
board. This just involves using a script on the ESP32 to extract a tree dictionary representation of
the functions, constants, classes (recursively checking class items too), and modules
(non-recursively since couldn't find any nested module definitions) that are available on the board.

The extracted trees are then copied into a test file which goes over the tree and asserts that each
item is available in the implementation, and that constants have the same value.

<!-- Maybe talk more about this later, maybe in its own section -->

> [!note]

> Most of the "Basic stub"/ "Basic dummy" classes are the stubbed out "out-of-scope" classes,
> they're mostly minimal implementations to fill out the required API to prevent `ImportError`s
> and `AttributeError`s from calls.
>
> Implementations that perform some basic simulation or expose simple attributes relating to return values
> that can be configured are considered "basic stub" classes, whereas the implementations with almost no
> underlying logic are considered "basic dummy" classes. But they're pretty interchangeable since the basic
> stubs don't have a lot of extra functionality.

| Test object        | Board version      | Status                        | Notes                                                                                                                                                                                                                                                                 |
| ------------------ | ------------------ | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `teu.fake_machine` | `machine`          | Implemented                   | Implementation mostly finished with proper test fakes implemented for `UART` and `I2C`, and `Pin`, with the rest being implemented as dummy's/ stubs with same items as board. Following table entries are `fake_machine` classes (`.UART` means `fake_machine.UART`) |
| `.UART`            | `machine.UART`     | Mostly Complete               | Missing a few features around IRQ and attribute validation                                                                                                                                                                                                            |
| `.Pin`             | `machine.Pin`      | Mostly Complete               | Basically fully implemented, only missing high-impedance state logic and maybe additional test helpers, could also do with some more test support since doesn't do too much.                                                                                          |
| `.I2C`             | `machine.I2C`      | Basic implementation complete | A basic version of the class is implemented, further work would involve more configuration options, better `SoftI2C` support, and Pin operations                                                                                                                      |
| `.SoftI2C`         | `machine.SoftI2C`  | Minimal implementation        | Is implemented as a basic subclass of `fake_machine.I2C` with a singleton instead of multiton, needs more work for future.                                                                                                                                            |
| `.Signal`          | `machine.Signal`   | Basic dummy                   | Basic stubbed out dummy that wraps around a pin, reads and sets the value.                                                                                                                                                                                            |
| `.ADC`             | `machine.ADC`      | Basic stub                    | Basic stub with attributes to set the `read_u6` and `read_uv` return values, needs better block support and ID validation in future. Would also need better support for programming the responses (list, callback etc)                                                |
| `.ADCBlock`        | `machine.ADCBlock` | Basic dummy                   | Basic stubbed out dummy, further work would need implementing the block system properly and keeping registry of instances.                                                                                                                                            |
| `.DAC`             | `machine.DAC`      | Basic dummy                   | Basic stubbed out dummy, holds a pin but doesn't do anything.                                                                                                                                                                                                         |
| `.PWM`             | `machine.PWM`      | Basic stub                    | Basic stub with board logic implemented for converting the different `duty` values. Future work needs the last used duty type logic and proper pin interfacing.                                                                                                       |
| `.SPI`             | `machine.SPI`      | Basic stub                    | Basic stubbed out dummy, very basic start for SPI with just a read buffer for read response, future work would be something akin to UART with more customizable response handling                                                                                     |
| `.SoftSPI`         | `machine.SoftSPI`  | Basic stub                    | Basic stubbed out dummy, subclass of SPI with modified `__init__` and `__repr__`, future work would be based on full SPI implementation.                                                                                                                              |
| `.I2S`             | `machine.I2S`      | Basic dummy                   | Basic stubbed out dummy, doesn't really have any functionality besides returning empty on read.                                                                                                                                                                       |
| `.RTC`             | `machine.RTC`      | Basic stub                    | Basic stub which holds a static datetime which can be set and read, also has a basic faked memory. Future work could be an actual simulated RTC implementation                                                                                                        |
| `.Timer`           | `machine.Timer`    | Basic dummy                   | Basic stubbed out dummy, doesn't have any functionality besides the basic period calculations for storing and printing. Future work would ideally implement a basic timer system.                                                                                     |
| `.Counter`         | `machine.Counter`  | Basic dummy                   | Basic stubbed out dummy, not much functionality. Future work would involve properly implementing.                                                                                                                                                                     |
| `.Encoder`         | `machine.Encoder`  | Basic dummy                   | Basic stubbed out dummy, not much functionality. Future work would involve properly implementing.                                                                                                                                                                     |
| `.WDT`             | `machine.WDT`      | Basic dummy                   | Basic stubbed out dummy, not much functionality to implement honestly, not even sure how you'd simulate a reset.                                                                                                                                                      |
| `.SDCard`          | `machine.SDCard`   | Basic dummy                   | Very basic stubbed out dummy, basically no functionality and `AbstractBlockDev` methods just return 0. Further work could make a basic faked filesystem or at least stub out the blockdev functions a bit better.                                                     |
| `.TouchPad`        | `machine.TouchPad` | Basic stub                    | Very basic stub, just returns a read_val. Class not in regular machine docs, only ESP32 port docs.                                                                                                                                                                    |
|                    |                    |                               |                                                                                                                                                                                                                                                                       |
| `teu.esp_time`     | `time`             | Custom shim implementation    | Custom `time` module which is implemented as a shim around built-in UNIX time and modifies problematic functions to match the output of ESP32 (fixes epoch and tuple size problems). Includes method to shadow builtin.                                               |
| `teu.esp`          | `esp`              | Stubbed out implementation    | Basic stubbed out implementation with matching constants and functions with canned returns. Items match what's available on board.                                                                                                                                    |
| `teu.esp32`        | `esp32`            | Stubbed out implementation    | Basic stubbed out implementation of `esp32` module with stubbed out functions, matching constants and basic stubbed out dummy implementations for following classes: `esp32.Partition`, `esp32.PCNT`, `esp32.RMT`, `esp32.ULP`, `esp32.NVS`. Also parity tested.      |
| `teu.espnow`       | `espnow`           | Basic stubbed out dummy       | Very basic stubbed out dummy implementation of the `espnow` module. Contains basic dummy's for `ESPNowBase` and its child `ESPNow` which mostly just raise the un-initialized OSError. Future work could improve this without too much work.                          |
| `teu.aioespnow`    | `aioespnow`        | Basic stubbed out dummy       | Just a basic module which implements the `ESPNow` subclass `AIOESPNow` which includes a few extra async methods.                                                                                                                                                      |
| `teu.network`      | `network`          | Basic stubbed out dummy       | Needed for `espnow` and not available on UNIX. Very basic stubbed out dummy implementations of WLAN, PPP, and LAN, not very accurate internally but was a rush job.                                                                                                   |

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

<!-- TODO - update this before submission -->

The contents of the repository's folders:

- [ci/](ci/) - Contains the dockerfile for building the custom MicroPython docker container image
- [docs/](docs/) - Contains design info and documentation for my implementations. Will contain examples and guides for using the objects later.
- [src/](src/) - Contains the code for the modules.
- [tests/](tests/) - Contains tests which test the individual functionality of the implemented test objects and run in pipeline. Also contains parity tests, and a few example tests.
- [tools/](tools/) - Contains tool scripts for helping out with various things.

______________________________________________________________________

## Basic Usage

<!-- TODO - could add a section explaining how the shadowing works so it's a bit more understandable -->

Here's a very basic guide on how to use our custom `teu` and `teu.fake_machine` modules.

> [!note]
> For more in-depth information in using our module and its test classes please check the
> [docs/](docs/) folder.

```python
# In a test file
import teu
from teu import fake_machine  # Nice to import fake_machine too so can use directly

# Shadow the built-in modules (machine, time, esp*) before any code-under-test imports them
teu.shadow_builtins()

# Now whenever code imports machine it will be using the fake_machine
import machine

# Now create some objects and test stuff
pin_f = fake_machine.Pin(5)
pin_m = machine.Pin(5)
assert pin_m is pin_f  # Will be true as they're using same class
```

You can also just import `fake_machine` and use its shadow method if you don't need the time and
esp modules shadowed.

```python
from teu import fake_machine
fake_machine.shadow_builtin_machine()  # Shadow just the builtin machine module

import machine  # imports fake_machine

assert machine is fake_machine  # True
```
