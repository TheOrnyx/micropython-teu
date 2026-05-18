"""
__init__.py

MicroPython module to expose a modified machine module.
Adds basic Mocks and Stubs for Machine classes to facilitate off-board testing.
"""

from micropython import const
from .uart import UART
from .pin import Pin

# A conditional import for the static type checking (not included at runtime)
try:
    from typing import Callable
except ImportError:
    Callable = object  # type: ignore[assignment]

## Temporarily disabling as don't rlly need to import original Machine atm
# Import the built-in machine and modify path temporarily to allow
# extending machine
# import sys

# _path = sys.path
# sys.path = ()
# try:
#     from machine import *
# finally:
#     sys.path = _path
#     del _path
#     del sys  # unload sys


def machine_test():
    """This is an awesome test waow"""
    print("This is a new method!")


class RTC:
    """Basic stub for the RTC (real-time clock) class

    TODO - Implement properly later
    TODO - check which methods are available on ESP32, docs are strange
    """

    def __init__(self, c_id=0):
        """Creates the RTC object"""
        self._id = c_id

    def datetime(self, datetimetuple=None):
        """Either get or set date and time of RTC based on parameter
        Either returns 8-item tuple or sets time using one

        Format is:
        (year, month, day, weekday, hours, minutes, seconds, subseconds)
        """
        return None if datetimetuple else (2026, 1, 1, 1, 1, 1, 1, 1)

    def init(self, datetime):
        """Initialize the RTC.

        datetime in format of:
        (year, month, day, hour, minute, second, microsecond, tzinfo)
        """
        pass

    def deinit(self):
        """Reset RTC to Jan 1 2015"""
        pass

    def alarm(self, alarm_id, time, repeat=False):
        """Set the RTC alarm.
        Time is either ms value to set alarm for time+ms in future,
        or a datetimetuple.

        If passing in ms then repeat can be used for periodic alarm
        """
        pass

    def alarm_left(self, alarm_id=0):
        """Get number of ms left till alarm expires."""
        pass

    def alarm_cancel(self, alarm_id=0):
        """Cancel a running alarm"""
        pass

    def irq(self, trigger, handler=None, wake=None):
        """Create irq object handled by clock alarm

        NOTE - The ESP32 might not support IRQ's for the RTC, check

        :param handler: The callback function to use
        :param wake: The sleep mode interrupt can wake up system with
        """
        pass

    def memory(self, data=None):
        """Write data to RTC memory.

        :param data: buffer protocol object (bytes, bytearray, etc) to
        write to RTC data.

        :return: If no data supplied read RTC memory and return as bytes
        """
        return None
