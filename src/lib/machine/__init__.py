"""
__init__.py

MicroPython module to expose a modified machine module.
Adds basic Mocks and Stubs for Machine classes to facilitate off-board testing.
"""

# Import the built-in machine and modify path temporarily to allow
# extending machine
import sys

_path = sys.path
sys.path = ()
try:
    from machine import *  # pylint: disable=all
finally:
    sys.path = _path
    del _path
    del sys  # unload sys

from .uart import UART


def machine_test():
    """This is an awesome test waow"""
    print("This is a new method!")


class Pin:
    """Basic mock/ stub for the Pin class, will hold value

    TODO - finish later obviously
    """

    # Pin constants
    # most values sourced from idf/components/hal/include/hal/gpio_types.h
    # TODO - check these are all correct using ESP32, some don't exist on port
    IN = const(0x01)  # Ref idf/components/esp_common/include/esp_bit_defs.h:41
    OUT = const(0x01 | 0x02)
    OPEN_DRAIN = const(0x01 | 0x02 | 0x04)
    PULL_UP = const(2)  # from machine_pin.c
    PULL_DOWN = const(1)
    DRIVE_0 = const(0)
    DRIVE_1 = const(1)
    DRIVE_2 = const(2)
    DRIVE_3 = const(3)
    IRQ_FALLING = const(2)
    IRQ_RISING = const(1)

    def __init__(self, id, mode=-1, pull=-1, value=None, drive=0, alt=-1):
        """Basic initialization"""
        self.id = id
        self.mode = mode
        self.pull = pull
        self._cur_value = 0
        # TODO - finish

    def init(self, mode=-1, pull=-1, value=None, drive=0, alt=-1):
        """Re-initialise the pin"""
        return None

    def value(self, x=None):
        """Set and get value of pin based on whether x is provided.
        Returns 1 or 0 if x not provided.
        Sets value to 1 or 0 based on x and returns None otherwise.

        TODO - implement proper value setting with respect to pin settings
        """

        if x:
            self._cur_value = int(bool(x))
            return None
        return self._cur_value

    def __call__(self, x=None):
        """Allows pin to be used as a callable to set value.
        Just calls value.
        """
        return self.value(x)

    def on(self):
        """Set pin to 1 output"""
        self._cur_value = 1

    def off(self):
        """Set pin to 0 output"""
        self._cur_value = 0

    def irq(
        self,
        handler=None,
        trigger=IRQ_FALLING | IRQ_RISING,
        priority=1,
        wake=None,
        hard=False,
    ):
        """Configure and return interrupt handler to be called when trigger
        source of pin is active

        TODO - implement when IRQ stuff is figured out
        """
        return None

    def toggle(self):
        """Toggle pin from 0 to 1 and vice versa"""
        self._cur_value = int(not self._cur_value)

    # TODO - figure out the Pin.board and Pin.cpu values on the ESP32 and
    # port here


class RTC:
    """Basic stub for the RTC (real-time clock) class

    TODO - Implement properly later
    TODO - check which methods are available on ESP32, docs are strange
    """

    def __init__(self, id=0):
        """Creates the RTC object"""
        self.id = id

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

    def alarm(self, id, time, repeat=False):
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
