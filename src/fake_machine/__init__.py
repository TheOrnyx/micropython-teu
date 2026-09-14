"""
__init__.py

MicroPython module for providing fake test double versions of ESP32 machine module classes.
Adds Mocked implementations for Machine classes to facilitate off-board testing on the UNIX port.

These classes have the same interface as their ESP32 counterparts, meaning embedded code using
these peripheral classes can be tested off-board with minimal changes required to the original CUT.

Please read the documentation for this library for information on how to use and usage examples.
"""

from micropython import const

from .pin import Pin
from .uart import UART
from .i2c import I2C, I2CDevice, SoftI2C

# Stubbed out dummy classes are in separate file otherwise linter gets mad
from .class_stubs import (
    Signal,
    ADC,
    ADCBlock,
    DAC,
    PWM,
    SPI,
    SoftSPI,
    I2S,
    RTC,
    Timer,
    Counter,
    Encoder,
    WDT,
    SDCard,
    TouchPad,
)

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


def reset_registries():
    """Resets each of the multiton registries so each test can have fresh instances and avoid
    leaking.

    The following classses get their registries reset:
      * ``fake_machine.Pin``
      * ``fake_machine.UART``
      * ``fake_machine.I2C``
    """
    UART.reset_registry()
    Pin.reset_registry()
    I2C.reset_registry()
    SoftI2C.reset_instance()


# ------- Built-in machine constants
# Taken from board

# IRQ wake values
SLEEP = const(2)
DEEPSLEEP = const(4)

# Reset reasons
HARD_RESET = const(2)
PWRON_RESET = const(1)
WDT_RESET = const(3)
DEEPSLEEP_RESET = const(4)
SOFT_RESET = const(5)

# Wake reasons
PIN_WAKE = const(2)
EXT0_WAKE = const(2)
EXT1_WAKE = const(3)
TIMER_WAKE = const(4)
TOUCHPAD_WAKE = const(5)
ULP_WAKE = const(6)

# ------- Built-in machine methods ---
#
# Stubbed out versions of the remaining ESP32 machine methods, most of the hardware-specific
# ones for resetting and what not won't have much functionality but will be stubbed out just in
# case.
# Most of these functions will just use bare return values but for future work it would be good
# to allow people to customize the return values, or they can just a mock framework for that.


class _Mem:
    """Basic class for simulating the machine memory attributes, will just store a single int
    value and read it back, instantiated once for each mem object ``mem8``, ``mem16``,
    ``mem32``. Also specifies the number of bytes for the access so writes only write the
    number of bytes the operation supports (cuz on board writing multiple bytes to a mem8
    address doesn't write to the following memory)

    Obviously it would be better to have this simulate actual memory but I'm not too sure what
    the available memory segment that this can read is and also don't want to have allocate a
    massive backing bytearray. But future work should make the 3 memory objects use the same
    backing memory, but for basic stub this should be fine.

    Partly copied from the micropython-mock-machine as it's a fine implementation for a basic
    stub.
    """

    def __init__(self, value, nbytes):
        """Init faked memory with single int value and nbytes."""
        self.value = value
        self.nbytes = nbytes

    def __getitem__(self, item):
        """Just return the stored value, ignore index."""
        return self.value

    def __setitem__(self, key, value):
        """Will set the memory value, uses nbytes to ensure data is proper size.

        Stores the bottom `nbytes` bytes of data, so 0xFF00 to 1-byte address writes 0.
        """
        bitcount = self.nbytes * 8
        mask = (2**bitcount) - 1
        self.value = value & mask


mem8 = _Mem(0xFF, 1)
mem16 = _Mem(0xFFFF, 2)
mem32 = _Mem(0xFFFFFFFF, 4)


# bytearray for the mem_backup memoryview
# TODO - make sure is fine
_MEM_BACKUP_REGION = bytearray(2048)


def mem_backup(region=0):
    """Get a memoryview over a speecific memory region. Returns a tuple of available regions
    with -1.

    ESP32 only has one mem_backup region, for the RTC. For basic stub this will be a memoryview
    over a 2048-byte long bytearray, same size as the RTC memory. -1 will return a tuple
    containing that memoryview.

    Does basic validation on the region since ESP32 only supports region 0.
    """
    if region == -1:
        return (memoryview(_MEM_BACKUP_REGION),)
    if region != 0:
        raise ValueError("Invalid region")
    return memoryview(_MEM_BACKUP_REGION)


def reset() -> None:
    """Perform a hard reset. Currently does nothing, could exit but doesn't seem very useful."""


def soft_reset() -> None:
    """Perform a soft reset. Normally resets heap and clears interpreter but does nothing here."""


def reset_cause() -> int:
    """Returns the reset cause. Stub will just return ``PWRON_RESET`` as that's what's present
    on startup.

    Could add a variable somewhere to change the return though, or have this take in an
    optional parameter to set the reset cause.
    """
    return PWRON_RESET


# Bootloader function not available on regular ESP32


def disable_irq() -> int:
    """Disable interrupt requests, on-board also returns the previous IRQ value.

    Stub implementation will just return 0.
    """
    return 0


def enable_irq(state) -> None:
    """Re-enable interrupt requests, normally takes in value returned from ``disable_irq()`` to
    return interrupts back to normal. Stub implementation does nothing.

    Could be good for future work if these did control some fake interrupt system, but probably
    not too helpful.
    """


def freq(hz=None) -> int | None:
    """Get or set the CPU frequency based on `hz` presence.

    Stub just returns default ESP32 result.

    TODO - check value is correct.
    """
    if hz is not None:
        return None
    return 160000000


def idle() -> None:
    """Idle the CPU to reduce power usage. Stub implementation does nothing.

    Could make a call to ``time.sleep(0)`` or another quick sleep so scheduled events run but
    want to avoid touching time since we'll probably shadow later.
    """


def sleep(time_ms=None) -> None:
    """Make the device sleep, deprecated on-board and just calls ``machine.lightsleep()`"""
    lightsleep(time_ms)


def lightsleep(time_ms=None) -> None:
    """Make the device sleep, stub does nothing.

    If future work implemented simulated sleeping then this and ``deepsleep()`` could set the
    wake_reason properly
    """


def deepsleep(time_ms=None) -> None:
    """Make the device sleep, stub does nothing."""


def wake_reason() -> int:
    """Returns the reason for waking, stub returns 0 (undefined wake reason) which is returned
    on-board when no wake has occurred yet.

    As previously mentioned in future work this could return the constant that would be used
    from a wake like lightsleep and deepsleep.
    """
    return 0


def wake_pins() -> tuple:
    """Gets a tuple of GPIO pin IDs that caused wakeup from deep sleep. Stub will just return
    an empty tuple"""
    return ()


def unique_id() -> bytes:
    """Return a byte string of the boards unique identifier (I think ESP32 uses MAC address).

    Stub will just return the bytestring from my ESP32, but maybe add a variable for this in
    future."""
    return b"\xe0\x8c\xfe\xc2f\x98"


def time_pulse_us(pin, pulse_level, timeout_us=1000000) -> int:
    """Time a pulse on a specific pin and return duration of pulse in ms.

    Stub will just return -2 which is returned on board on a timeout waiting for pin to reach
    initial level.

    Future work could implement this to actually use the Pin but would be better to just
    specify a return value.
    """
    return -2


def bitstream(pin, encoding, timing, data) -> None:
    """Transmit `data` by bit-banging the provided `pin`. Stub does nothing.

    This would be good to implement in future work, I wanted to implement a bit-banging
    implementation but wasn't sure how to approach it.
    """


def dht_readinto(pin, buf_in):
    """Read temperature from DHT temperature sensor connected on pin into buf.

    Honestly not too sure how this one works cuz it's not documented and only implemented in C
    (with no comments), so just returning None
    """
    return None
