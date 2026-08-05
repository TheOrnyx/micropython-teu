# Testing ESP32 MicroPython code on UNIX (TEU)

This is the main repo for my ENGR489 capstone project "Testing Embedded Code Without the Embedded
System" focusing on supporting testing MicroPython code written for the ESP32 off-board using the
UNIX port.

This repo contains the implementations, tests, and documentation for my testable MicroPython module
implementations for things like hardware peripherals (like the `machine` module). This repo also
contains tools and configurations for the CI/CD pipeline and docker container config.

## Project info

### Target Board and Software

For this project I will be focusing on supporting embedded code written for the ESP32 microcontroller
in the MicroPython language. The ESP32 is a popular family of budget-friendly Microcontrollers
manufactured by Espressif and is a popular target for the MicroPython language. We are specifically
targetting the ESP32-devkitc with the WROVER-E chip.

MicroPython is a "lean and efficient" implementation of the Python3 language optimized for
microcontrollers. It includes a subset of the python3 standard library with a few extra
MicroPython-specific modules included--such as the `machine` module--which provides a kind of
Hardware-Abstraction-Layer by providing simple to use classes for peripherals like UART, RTCs, and
others.

It offers ports (aka versions) for a few different board types including our ESP32. They also
offer a minimal UNIX port, which allows us to run MicroPython code on our host Linux/Mac/BSD
system and is primarily used for development and testing of the MicroPython core. These ports have
some functional differences between them with class availability and function parameters differing
between ports.

<!--TODO - Maybe add some more info to this or rearrange the sections. Maybe explain the stuff more-->

### Goals

The goal of this project is to address the problem of testing embedded ESP32 MicroPython software
which typically relies on communication with peripherals, thus limiting off-board testing.

Embedded code can already be hard to test due to needing a physical board set up with the
peripherals attached and configured. This makes testing difficult as configuring your peripherals to
do things like return bad values to test logic can be quite cumbersome. It also makes testing
off-board currently not possible as the MicroPython UNIX port does not provide the hardware classes
meaning any code you want to test that imports these modules won't run.

Additionally, even code that doesn't rely on hardware peripherals isn't guaranteed to run perfectly
off-board as there are some functional differences between the UNIX and ESP32 ports of MicroPython
(such as the tuple length of `time.localtime()` being 9 on UNIX but 8 on ESP32) which would need to
be modified to ensure testing performs the same as on the ESP32.

### Outputs

The outputs for this project will be a distribution of the MicroPython UNIX port which will address
any glaring output differences between ports (like the `time.localtime()`) and support testing
hardware-dependent ESP32 code off-board through the use of flexible test double versions of hardware
classes. This will allow code written for the ESP32 to run off-board and will allow test authors/
programmers to test hardware-dependent code much easier on their host system. It will also make
automated testing in pre-commit and CI/CD pipelines much easier.

Currently the main output is our testable `fake_machine` module which is stored in this repo and
provides the test versions of specific classes, with out of scope modules just being stubbed out
through dummy implementations (see scope section).

The second part is the modified version of the core MicroPython codebase which is a mirror fork of the
main MicroPython github repo and will contain any changes to the core C codebase that are needed to make
the ports operate similarly. This fork is currently located [here](https://gitlab.ecs.vuw.ac.nz/course-work/project489/2026/project/silouzaki/micropython).

However, due to being able to implement our test doubles as native MicroPython modules (which is
much nicer), the core C codebase will likely remain unchanged, unless a very complicated feature is
needed.

### Scope

Obviously the goal of this project is not to entirely replace on-board testing, there will always
be a need to test that software performs correctly in the target environment, especially for integration
testing, and there will always be code that is too hardware-dependent to easily be simulated.

My goal is to facilitate off-board testing and allow people writing embedded MicroPython software
for the ESP32 to easily write and run unit tests for their codes logic off-board without needing to
spend ages creating their own custom test doubles.

The design of my test objects will focus on being easy-to-use and reasonably simple abstractions of
the original implementations, mimicking important hardware side-effects where needed.

Due to time constraints it is also unreasonable to expect all missing classes to receive proper test
double implementations, so I will be focusing on the main classes used in the Quilty Environmental
Monitoring project, with any others likely being implemented as basic stubbed out dummy objects to
fill out the expected API. This will provide a good jumping-off point for future projects to expand
on.

______________________________________________________________________

## Project Structure

The contents of the repository's folders:

- [ci/](ci/) - Contains the dockerfile for building the custom MicroPython docker container image
- [docs/](docs/) - Contains design info and documentation for my implementations. Will contain examples and guides for using the objects later.
- [src/](src/) - Contains the code for the modules as well as tests for them which ensure they work and perform as expected.
- [tools/](tools/) - Contains tool scripts for helping out with various things.

<!-- Maybe add a "How to use", but might do in a src/README -->

______________________________________________________________________

## Basic Usage

Here's a very basic guide on how to use our custom `fake_machine` module.

> [!note]
> For more in-depth information in using our module and its test classes please check the
> [docs/](docs/) folder.

```python
# In a test file
import fake_machine

# Call the shadow method to shadow the built-in machine
fake_machine.shadow_builtin_machine()

# Now whenever code imports machine it will be using the fake_machine
import machine

# Now create some objects and test stuff
pin_f = fake_machine.Pin(5)
pin_m = machine.Pin(5)
pin_m is pin_f  # Will be true as they're using same class
```
