# Testing ESP32 on UNIX (TEU)

A modified version of MicroPython that will replicate ESP32 port functionality in the UNIX port and add support for testing mocks.

# Goals

The goal of this project is to design and produce a modified version of MicroPython which will address the problem of testing MicroPython software written for the ESP32.
This modified version will attempt to replicate the functionality of the ESP32 port within the UNIX port (to ensure validity of testing) as well as provide mocks to improve testing support.

## Replicating ESP32 functionality

In order to facilitate testing of ESP32 software on the UNIX port the UNIX port must operate similarly to the ESP32 port.
Currently there are quite a few differences in how the UNIX port operates, such as: time handling, memory access, object sizes, etc which will need to be replicated to ensure testing is valid.

This part of the project will focus on producing a version of the UNIX port which is functionally identical to the ESP32 port which will allow testing off-board within a docker container.

## Adding support for testing mocks

The other goal is to improve testing by adding support for mocked versions for objects like communication devices, so faked ones can be configured and used when testing.
This will help improve the testing experience as testing can focus on the functionality of the code logic without needing to configure dedicated communication hardware.
