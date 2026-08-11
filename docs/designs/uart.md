# The design, implementation, and usage of the UART class (WIP)

## Original Implementation

In MicroPython the [`machine.UART`](https://docs.micropython.org/en/latest/library/machine.UART.html) class represents a UART connection to an external device.
A created `UART` instance acts as a stream object and allows you to write to the device and read from
it.

These are the noteworthy operations:

- Create an object with `machine.UART(id, ...)` constructor
- Write to the device with `UART.write(buf)`
- See how many characters can be read from device with `UART.any()`
- Read characters from device using: `UART.read([nbytes])`, `UART.readinto(buf, [nbytes])`, or `UART.readline()`
- Send a break condition to device with `UART.sendbreak()`
- Configure interrupt handler for UART event with `UART.irq(handler, trigger)`.

## Goal of the design

## Quirks and limitations

The current implementation has a few quirks and limitations with it that I'll briefly explain here:

### IoBase functionality disabled

The board version of `UART` technically subclasses the `io.IOBase` class so the device can be used in print statements as a file etc.

We have the necessary methods for this subclass implemented but due to problems with how
MicroPython handles subclassing with builtin types trying to subclass when we override `__new__`
this results in a segmentation fault so it is currently disabled.

Please see [#79](https://gitlab.ecs.vuw.ac.nz/course-work/project489/2026/project/silouzaki/micropython-esp32-unix/-/work_items/79) for more info.

## Things to add/ ideas

- Callback for when the device is connected to (the client code creates a UART device to use)
