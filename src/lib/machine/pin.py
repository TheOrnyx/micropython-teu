"""pin.py

File for providing the Pin machine class mock.
"""

from micropython import const


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

    def __init__(self, pin_id, mode=-1, pull=-1, value=None, drive=0, alt=-1):
        """Basic initialization"""
        self._id = pin_id
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
