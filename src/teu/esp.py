"""esp.py

Custom stubbed out implementation of the ESP32 ``esp`` module which is only available on ESP
based devices.

This file will contain basic stubbed out versions of the ``esp` module functions, with return
values just being basic return values, usually collected from the board. The ``LOG_*``
constants for ``esp.osdebug()`` will also be included with the same value as is present on the
board.

Only the methods available on the generic ESP32 port will be included, the ``ESP8266`` specific
functions ``sleep_type()``, ``deepsleep()``, ``flash_id()``, and ``set_native_code_location()``
will not be included."""

# The "return None" stub functions seem to make pylint think it's duplicate code with esp32...
# pylint: disable=duplicate-code

import sys


def register_esp_module():
    """Register this module in ``sys.modules`` by adding it as the entry for ``'esp'``,
    so going ``import esp`` will import this module. Gets called by ``teu.shadow_builtins()``.

    On the ESP32 calling this will shadow the built-in ``esp`` module, which might cause
    problems if code involves these functions. To help with this the ``teu.shadow_builtins()``
    method will have an extra ``shadow_esp_modules=True`` optional arg which can be passed as
    False if you only want the machine and time modules shadowed.

    TODO - could maybe add a feature to this which will just re-export the built-in ``esp`` if
    being ran on an ESP32, but not doing for now as supporting this library on the board isn't
    the main focus.
    """
    sys.modules["esp"] = sys.modules[__name__]


# Constants for osdebug
LOG_NONE = 0
LOG_ERROR = 1
LOG_WARNING = 2
LOG_INFO = 3
LOG_DEBUG = 4
LOG_VERBOSE = 5


def flash_size() -> int:
    """Read the total size of flash memory on the device. Stubbed will just return same value
    as my ESP32 (its WROVER flash size)"""
    return 8388608


def flash_user_start() -> int:
    """Read the memory offset at which the user flash space begins. Stub just returns ESP32
    output."""
    return 2097152


def flash_read(byte_offset, buf) -> None:
    """Read flash memory starting at `byte_offset` into buf, amount written is length of buf.

    The docs seem to suggest second arg can be length or buffer but ESP32 only accepts buffers.
    Stubbed will just do nothing and return None, could add some validation to buf and
    byte_offset in future, maybe.
    """
    return None


def flash_write(byte_offset, buf) -> None:
    """Write data in `buf` to flash memory starting at `byte_offset`. Stub does nothing."""
    return None


def flash_erase(sector_no) -> None:
    """Erase the 4096-byte memory sector for `sector_no`. Stub does nothing."""
    return None


def osdebug(uart_no, level=None) -> None:
    """Changes the level of OS serial debug log messages. `level` is optional and can be one of
    the ``LOG_*`` constants. If ``None`` it restores default log level (``LOG_ERROR``) and if
    ``0`` it enables all log messages.

    Stub will do nothing as can't really replicate anything here.
    """
    return None


def gpio_matrix_in(pin, sig, inv) -> None:
    """Not included in docs but implemented in the C codebase for ESP32, bit hard to tell what
    it does as it's not really documented. From basic research it seems to be for remapping the
    default pin values for specific input pins on peripherals (like the default RX input pin for
    UART). But not sure

    Stub will just do nothing as implementation is handled by the hardware and doesn't seem to
    be implemented in C.
    """
    return None


def gpio_matrix_out(pin, sig, out_inv, oen_inv) -> None:
    """Similar to ``gpio_matrix_in`` but for output pins. Stub will do nothing"""
    return None
