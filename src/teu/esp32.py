"""esp32.py

Custom stubbed out implementation of the ESP32-specific ``esp32`` module for the UNIX port.

This file will contain the basic stubbed out versions of the ``esp32`` module contents,
with matching constant values, and function return values just being basic canned values,
usually collected from my ESP32 board. Classes will be implemented as basic stubbed out dummy
classes with the same API.
"""

# The "return None" stub functions seem to make pylint think it's duplicate code with esp32...
# pylint: disable=duplicate-code

import errno
import sys
from collections import namedtuple  # For the PCNT irq


def register_esp32_module():
    """Register this module in ``sys.modules`` by adding it as the entry for ``'esp32'``,
    so going ``import esp32`` will import this module. Gets called by ``teu.shadow_builtins()``.

    On the ESP32 calling this will shadow the built-in ``esp32`` module, which might cause
    problems if code involves these functions. To help with this the ``teu.shadow_builtins()``
    method will have an extra ``shadow_esp_modules=True`` optional arg which can be passed as
    False if you only want the machine and time modules shadowed.
    """
    sys.modules["esp32"] = sys.modules[__name__]


# Top-level constants
HEAP_DATA = 4
HEAP_EXEC = 1
WAKEUP_ALL_LOW = False
WAKEUP_ANY_HIGH = True

# Canned return values for idf_heap_info calls with the HEAP constants
IDF_HEAP_INFO_DATA_CANNED = [
    (32767, 32031, 31744, 0),
    (4194304, 4134464, 4128768, 4134464),
    (240, 4, 0, 4),
    (7288, 92, 80, 4),
    (15072, 14656, 14336, 14656),
    (16648, 3448, 2560, 3120),
    (85192, 35160, 34816, 35160),
    (113840, 112968, 110592, 112968),
]

IDF_HEAP_INFO_EXEC_CANNED = [
    (15072, 14656, 14336, 14656),
    (16920, 16160, 15872, 16128),
    (113840, 112968, 110592, 112968),
]


def wake_on_touch(wake) -> None:
    """Configures whether ESP32 should wake on touch, stub does nothing"""
    return None


def wake_on_ulp(wake) -> None:
    """Configures whether the ESP32 can be woken by the ULP processor, stub does nothing."""
    return None


def wake_on_ext0(pin=None, level=None) -> None:
    """Configures how EXT0 wakes the device from sleep, takes a pin and one of the
    `WAKEUP_ALL_*` constants for level. Stub does nothing.

    The two args have default values which are the previous set pin and level, so they are
    technically optional.
    """
    return None


def wake_on_ext1(pins, level) -> None:
    """Configures how EXT1 wakes the device from sleep, takes optional list/tuple of pins and a
    level (like ext0). Stub does nothing."""
    return None


def wake_on_gpio(pins, level) -> None:
    """Configures how GPIO wakes the device from sleep, takes optional list/tuple of pins and a
    level. Stub does nothing"""
    return None


def raw_temperature() -> int:
    """Reads and returns the raw value of the devices internal temperature sensor.

    Stub will just return ``122`` as that was the temperature I was getting from the board
    while working.
    """
    return 122


def idf_heap_info(capabilities):
    """Returns information about the ESP-IDF heap memory regions as a list of tuples.

    I can't really tell how the code handles the different capabilities values but I will
    provide canned return values collected from the ESP32 for the constants ``HEAP_DATA`` and
    ``HEAP_EXEC``, others will be returned as an empty list
    """
    if capabilities == HEAP_DATA:
        return IDF_HEAP_INFO_DATA_CANNED
    if capabilities == HEAP_EXEC:
        return IDF_HEAP_INFO_EXEC_CANNED

    return []


# --------- Stubbed out classes -----


class Partition:
    """Basic stubbed out dummy implementation of the ``esp32.Partition`` class. Board version
    of class gives access to the flash memory partitions for updates and stuff.

    Dummy implementation will mostly just stub out the methods which will return canned values
    and do nothing.

    TODO - could improve this in future work by having a basic singleton for the ESP32 flash
    memory partition so things like find will return a faked partition, but not doing currently
    due to time.
    """

    # Class constants
    BOOT = 0
    RUNNING = 1
    TYPE_APP = 0
    TYPE_DATA = 1

    def __init__(self, id_, block_size=4096):
        """Create an object representing partition. ID is string partition label, block size is
        byte size of individual blocks.

        Dummy will just store the arguments as attributes.
        """
        self.id_ = id_
        self.block_size = block_size

    @staticmethod
    # pylint: disable-next=redefined-builtin
    def find(type=0, subtype=0xFF, label=None, block_size=4096):
        """Find a partition by `type`, `subtype` and `label`. Returns potentially empty list of
        found partitions. Stub will just return empty list even though a Partition would
        normally exist on the ESP32.
        """
        return []

    def info(self):
        """Returns a 6-tuple ``(type, subtype, addr, size, label, encrypted)`` for partition
        info.

        For the stub I'll just return the ``info()`` result for the basic factory flash
        partition on my ESP32. For future work it would be good to mock this properly though.
        """
        return (0, 0, 65536, 2031616, "factory", False)

    def readblocks(self, block_num, buf, offset=0) -> None:
        """Read data from the partition blocks starting at `block_num` into `buf`. Stub does
        nothing."""
        return None

    def writeblocks(self, block_num, buf, offset=0) -> None:
        """Write the data from `buf` into the partition blocks starting at `block_num`. Stub
        does nothing."""
        return None

    def ioctl(self, cmd, arg):
        """Control the block device and query parameters.

        Stub will stub out a basic response for cmd 4 (number of blocks) but will just return
        None for others.
        """
        if cmd == 4:
            return 0

        return None

    def set_boot(self) -> None:
        """Sets this partition as the boot partition, stub does nothing."""
        return None

    def get_next_update(self):
        """Gets the next update partition after this, and returns a Partition object for it.

        On the board if no next update partition is found then the partition constructor will
        raise an ``OSError``. Stub will just raise the same OSError.
        """
        raise OSError(errno.ENOENT)

    @classmethod
    def mark_app_valid_cancel_rollback(cls):
        """Signals that the current boot is considered successful.

        On-board if there's no partitions with ``otadata`` (over-the-air data) available then
        this will raise an ``OSError: (-261, 'ESP_ERR_NOT_FOUND') ``, stub will just raise this.
        """
        raise OSError(-261, "ESP_ERR_NOT_FOUND")


class PCNT:
    """Basic stubbed out dummy implementation of the ESP32 pulse counter class to count pulses
    for a Pin.

    Dummy implementation will just stub out the methods with basic canned return values.
    For future work it would be good to add some extra test utilities to this and maybe connect
    it to the Pin properly, but for now a basic dummy will suffice.

    Future work would also need to implement the multiton stuff
    """

    # Basic namedtuple for the PCNT irq, probs not best solution but good for basic dummy.
    _irq = namedtuple("_irq", ("flags", "trigger"))

    # Constants
    IGNORE = 0
    INCREMENT = 1
    DECREMENT = 2
    NORMAL = 0
    REVERSE = 1
    HOLD = 2
    IRQ_ZERO = 64
    IRQ_THRESHOLD0 = 8
    IRQ_THRESHOLD1 = 4
    IRQ_MIN = 16
    IRQ_MAX = 32

    def __init__(  # pylint: disable=redefined-builtin
        self,
        id_,
        channel=0,
        pin=None,
        rising=None,
        falling=None,
        mode_pin=None,
        mode_low=None,
        mode_high=None,
        min=None,
        max=None,
        filter=None,
        threshold0=None,
        threshold1=None,
        value=None,
    ):
        """Create and instantiate a PCNT object. Stub will just store the attributes.

        The board version of this uses a multiton and follows the same process as other objects
        like that where the constructor is basically a re-init for existing objects and just
        calls the init. I also cannot tell the default values for the parameters as they get
        initialized internally and I can't tell what they are, so the extra vars will get
        set to None by default.

        The board version of this method (and ``init()``) have a good bit of complexity behind
        it, with arguments being grouped together so if one gets passed then the others must be
        passed or be reset to default. For this basic dummy implementation I will not be
        replicating this logic, but it would be good to do for future work.
        """
        self.id_ = id_
        self.channel = channel
        self.pin = pin
        self.rising = rising
        self.falling = falling
        self.mode_pin = mode_pin
        self.mode_low = mode_low
        self.mode_high = mode_high
        self.min = min
        self.max = max
        self.filter = filter
        self.threshold0 = threshold0
        self.threshold1 = threshold1
        self.value(value)

    def init(  # pylint: disable=redefined-builtin
        self,
        channel=0,
        pin=None,
        rising=None,
        falling=None,
        mode_pin=None,
        mode_low=None,
        mode_high=None,
        min=None,
        max=None,
        filter=None,
        threshold0=None,
        threshold1=None,
        value=None,
    ):
        """Re-init the PCNT, see ``__init__()`` for details and notes about future work"""
        self.channel = channel
        self.pin = pin
        self.rising = rising
        self.falling = falling
        self.mode_pin = mode_pin
        self.mode_low = mode_low
        self.mode_high = mode_high
        self.min = min
        self.max = max
        self.filter = filter
        self.threshold0 = threshold0
        self.threshold1 = threshold1
        self.value(value)

    def deinit(self) -> None:
        """Deinit this PCNT, not defined in docs but in esp32 port. Stub does nothing"""
        return None

    def __del__(self):
        """del override, just calls deinit so does nothing. Defined in esp32 port but not in
        docs."""
        self.deinit()

    def value(self, value=None) -> int:
        """Reads the current value of the pulse counter, can pass `value` as 0 to reset
        counter.

        Dummy implementation will currently just return 0 always. Will also implement the basic
        board functionality of raising an exception if `value` is anything other than 0 when
        provided.
        """
        if value is not None and value != 0:
            raise ValueError("value")

        return 0

    def irq(self, handler=None, trigger=64):
        """Register an interrupt handler for a specific counter trigger event.

        Dummy implementation won't do anything here as it's not worth doing if the rest of the
        functionality isn't implemented (and I'm running out of time).

        This function returns a basic irq object which contains bound methods to get the flag
        mask that caused the interrupt and the trigger mask for the interrupt. To replicate
        this we will return a basic ``_irq`` namedtuple which will have basic functions for
        canned responses to these. Future work would obviously implement a better system.
        """

        def flags():
            return 0

        def trigger_handler():
            return trigger

        return self._irq(flags=flags, trigger=trigger_handler)

    def start(self) -> None:
        """Seems to start/ resume the PCNT, not defined in docs but available on board. Stub
        does nothing."""
        return None

    def stop(self) -> None:
        """Seems to pause the PCNT, not defined in docs but available on board. Stub does
        nothing."""
        return None

    def __repr__(self):
        """Basic string representation of PCNT."""
        return f"PCNT({self.id_})"


class RMT:
    """Basic stubbed out dummy implementation of the esp32 RMT (remote control) class.

    Dummy implementation will just stub out the methods with canned responses.
    """

    PULSE_MAX = 32767

    def __init__(
        self,
        id_=-1,
        pin=None,
        resolution_hz=10000000,
        clock_div=None,
        idle_level=False,
        tx_carrier=None,
        num_symbols=64,
    ):
        """Create new RMT object. Stub will just set basic attributes"""
        self.id_ = id_
        self.pin = pin
        self.resolution_hz = resolution_hz
        self.clock_div_ = clock_div
        self.idle_level_ = idle_level
        self.tx_carrier = tx_carrier
        self.num_symbols_ = num_symbols

    @staticmethod
    def source_freq() -> int:
        """Get the source clock frequency, returns same as board (80Hz)."""
        return 80000000

    def clock_div(self) -> int:
        """Returns the clock divider. Will use board calculation of ``source_freq() /
        resolution_hz``."""
        return self.source_freq() // self.resolution_hz

    def wait_done(self, *, timeout=0) -> bool:
        """Returns true if channel is idle, false if busy. Stub will just return True always."""
        return True

    def loop(self, enable_loop: bool) -> None:
        """Deprecated method to configure looping on the channel based on `enable_loop`. Stub
        does nothing."""
        return None

    def loop_count(self, n) -> None:
        """Newer method to configure looping on channel. n=0 disables looping, n=-1 enables
        infinite, n=<pos_int> to loop for specific count. Stub does nothing"""
        return None

    def active(self, arg=None) -> bool:
        """If called without args, returns True if ongoing transmission. If called with False
        arg, stops ongoing transmission. Stub does nothing but return False.

        Will replicate the basic raise if arg is True because pretty simple.
        """
        if arg is True:
            raise ValueError("activate by calling write_pulses()")

        return False

    def deinit(self) -> None:
        """Deinit the RMT, stub does nothing."""
        return None

    def __del__(self):
        """C code has `del` implementation, just calls deinit so will do nothing."""
        self.deinit()

    def write_pulses(self, duration, data=True) -> None:
        """Begin transmitting a sequence of data. Stub will do nothing.

        Interestingly `data` has a default value of ``True`` even though it's meant to be
        passed as a tuple or list of output levels.
        """
        return None

    @staticmethod
    def bitstream_rmt(value=None) -> bool:
        """Configures rmt usage in the ``machine.bitstream`` implementation. True makes
        bitstream try to use RMT, False makes it stick to bit-banging.

        Returns whether bitstream using RMT is enabled, stub will just return default True
        state always. Could actually store an enabled value for later but fine for now.
        """
        return True

    @staticmethod
    def bitstream_channel(value=None):
        """Deprecated version of ``bitstream_rmt()`` where `value` sets if bitstream should use
        RMT. Returns 1 if bitstream RMT is enabled, None otherwise.

        Stub will just return 1 always.
        """
        return 1

    def __repr__(self):
        """Basic string representation of RMT object, with pin, source_freq, resolution_hz,
        and idle_level."""
        return (
            f"RMT(pin={self.pin}, source_freq={self.source_freq()}, "
            f"resolution_hz={self.resolution_hz}, idle_level={int(self.idle_level_)})"
        )


class ULP:
    """Basic stubbed out dummy implementation of the ULP Ultra-Low-Power co-processor class."""

    RESERVE_MEM = 2040

    def __init__(self):
        """Init ULP object."""

    def set_wakeup_period(self, period_index, period_us) -> None:
        """Set the wake-up period. Stub does nothing."""
        return None

    def load_binary(self, load_addr, program_binary) -> None:
        """Load program binary into ULP at specific addr. Stub does nothing."""
        return None

    def run(self, entry_point) -> None:
        """Start the ULP running at given entry point. Stub does nothing."""
        return None


class NVS:
    """Basic stubbed out dummy implementation of the esp32 NVS nonvolatile storage class.

    For future work it could be good to have a basic fake here, just keeping track of what's
    been set so it can be retrieved with a get without raising.
    """

    def __init__(self, namespace):
        """Creates an NVS object providing access to a `namespace`."""
        self.namespace_ = namespace

    def get_i32(self, key) -> int:
        """Returns signed integer value for specified key, raises OSError if key does not
        exist. Stub will just raise the OSError."""
        raise OSError(-4354, "ESP_ERR_NVS_NOT_FOUND")

    def set_i32(self, key, value) -> None:
        """Set a value for a specific key. Stub will do nothing"""
        return None

    def get_blob(self, key, buffer) -> int:
        """Get blob of data for key and store in buffer, return length of data read,
        raises OSError if key does not exist. Stub will just raise the OSError"""
        raise OSError(-4354, "ESP_ERR_NVS_NOT_FOUND")

    def set_blob(self, key, value_buf) -> None:
        """Set blob of data at key to data in `value_buf`. Stub does nothing."""
        return None

    def erase_key(self, key) -> None:
        """Erase specific key and value. Raises OSError if unknown key. Stub will just raise."""
        raise OSError(-4354, "ESP_ERR_NVS_NOT_FOUND")

    def commit(self) -> None:
        """Commits changes, stub does nothing."""
        return None
