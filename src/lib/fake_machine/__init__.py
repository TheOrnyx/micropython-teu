"""
__init__.py

MicroPython module for providing fake test double versions of ESP32 machine module classes.
Adds Mocked implementations for Machine classes to facilitate off-board testing on the UNIX port.

These classes have the same interface as their ESP32 counterparts, meaning embedded code using
these peripheral classes can be tested off-board with minimal changes required to the original CUT.

Please read the documentation for this library for information on how to use and usage examples.
"""

from .uart import UART
from .pin import Pin

# A conditional import for the static type checking (not included at runtime)
TYPE_CHECKING = False
if TYPE_CHECKING:
    pass

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


def shadow_builtin_machine():
    """Shadows the builtin ``machine`` module by modifying the sys.modules to make the
    'machine' entry point to this module. Meaning future code importing machine will be
    importing us.

    Should be called in test class setup to ensure code under test is using our machine module."""
    # pylint: disable=import-outside-toplevel
    import sys

    sys.modules["machine"] = sys.modules[__name__]


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
