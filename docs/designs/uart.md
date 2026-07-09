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

## Things to add/ ideas

- Callback for when the device is connected to (the client code creates a UART device to use)
