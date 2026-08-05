"""pin.py

Micropython file that provides our mock implementation of the machine.Pin class.
Used by most other classes.
"""

from micropython import const


# pylint: disable=too-few-public-methods
class _PinBoard:
    """Basic class for the Pin.board, empty for now as ESP32 doesn't use this, but can be
    expanded on in future development."""


class Pin:
    """Basic simulated fake implementation of machine.Pin.

    Mostly for use as attributes in other classes, simulates basic operation and uses a multiton
    registry for keeping pins with the same ID as the same object.

    Features to still implement:
      + Buffering the stored value for Pin.IN

    TODO - could possibly implement a strict mode to throw on unknown pins
    """

    # Pin constants
    # Most values included from ESP-idf codebase at components/hal/include/hal/gpio_types.h
    IN = const(0x01)  # GPIO_MODE_DEF_INPUT = BIT0 = 1
    OUT = const(0x01 | 0x02)  # GPIO_MODE_INPUT_OUTPUT = (BIT0 | BIT1) = 3
    OPEN_DRAIN = const(0x01 | 0x02 | 0x04)  # GPIO_MODE_INPUT_OUTPUT_OD = 7
    PULL_UP = const(2)  # from machine_pin.c
    PULL_DOWN = const(1)  # from machine_pin.c too
    IRQ_RISING = const(1)  # GPIO_INTR_POSEDGE = 1
    IRQ_FALLING = const(2)  # GPIO_INTR_NEGEDGE = 2
    WAKE_LOW = const(4)  # GPIO_INTR_LOW_LEVEL = 4
    WAKE_HIGH = const(5)  # GPIO_INTR_HIGH_LEVEL = 5
    DRIVE_0 = const(0)  # GPIO_DRIVE_CAP_0 = 0
    DRIVE_1 = const(1)  # GPIO_DRIVE_CAP_1 = 1
    DRIVE_2 = const(2)  # GPIO_DRIVE_CAP_2 = 2
    DRIVE_3 = const(3)  # GPIO_DRIVE_CAP_3 = 3

    # Multiton registry
    _PIN_REGISTRY: dict[int, "Pin"] = {}

    # Pin.board, empty class instance as unused
    board = _PinBoard()

    def __new__(cls, pin_id: "str | int | Pin", **kwargs):
        """Overridden new constructor to control returning an instance from the registry.

        If an entry with the same ID exists in the `_PIN_REGISTRY` then that instance will be
        returned.

        For flexibility (and to make supporting classes that use pins much easier) the provided
        `pin_id` can be a `Pin` instance, in this case the provided instance will just be
        returned. This matches what happens on board when you provide a Pin instance. Mostly is
        useful as most peripheral classes can accept either Pin instances or pin ID's so this
        just reduces the need for typechecks in those.
        """
        if isinstance(pin_id, (cls, Pin)):
            return pin_id

        if isinstance(pin_id, str):
            raise ValueError("String id support for Pins not yet supported, ints only")

        # Extra safety check to prevent unsupported IDs
        if not isinstance(pin_id, int):
            raise ValueError(f"Unknown Pin_id {pin_id} of type {type(pin_id)}")

        if pin_id in cls._PIN_REGISTRY:
            # TODO - maybe add an argument to reset attributes
            return cls._PIN_REGISTRY[pin_id]

        pin = super().__new__(cls)
        cls._PIN_REGISTRY[pin_id] = pin
        return pin

    def __init__(
        self,
        pin_id: "str | int | Pin",
        mode=-1,
        pull=-1,
        value=None,
        drive=-1,
    ):
        """Constructor to initialize a pin object with provided parameters.

        When this gets called (even on an already initialized instance passed from __new__) it
        will set attributes for any arguments that are explicitly passed (aka not None or -1)
        and leave the others as either the default or their previously set value.

        Since we override `__new__` for the multiton returned instances, __init__ will get
        called even on already-initialized instances. To prevent Pin attributes from getting
        reset we include an initialization guard which sets the attributes to default values on
        first initialization. So future initialization will keep previous values and first
        initialization sets defaults.

        :param pin_id: The ID for the pin, can be either a string or int but currently int is only
          supported type. Can technically accept a Pin instance due to __new__ calling this,
          but is guarded against.
        :param mode: The pin mode, controls what happens when pin value is set, see `value()` for
          more info. For test authors there will be helper methods to read or write a value and
          ignore the mode.
        :param pull: Specifies if the pin has a pull resistor attached. Can be `None`,
          `Pin.PULL_UP`, or `Pin.PULL_DOWN`. Don't think is too relevant for mocking.
        :param value: Sets the initial pin value if in `Pin.OUT` or `Pin.OPEN_DRAIN` mode.
        :param drive: The pins output power drive, not relevant for mock but will store.

        TODO - investigate board reset stuff, can't qemu the pins
        """
        # Initialization guard, set defaults on first creation, then call `Pin.init()` which will
        # set the specified arguments and leave others as default.
        if not getattr(self, "_initialized", False) and not isinstance(pin_id, Pin):
            self._id = pin_id
            self._mode = Pin.IN
            self._pull: int | None = None
            self._drive = Pin.DRIVE_0
            self._cur_value = 0

        # Set an initialized guard so default values get set once
        self.init(mode=mode, pull=pull, value=value, drive=drive)
        self._initialized = True

    def init(self, mode=-1, pull=-1, value=None, drive=-1) -> None:
        """Re-initialise the pins attributes, only arguments that are specifically passed will
        be set.

        Look at the constructor for information about the arguments.
        """
        allowed_mode = [Pin.IN, Pin.OUT, Pin.OPEN_DRAIN]
        allowed_pull = [Pin.PULL_UP, Pin.PULL_DOWN]
        allowed_drive = [Pin.DRIVE_0, Pin.DRIVE_1, Pin.DRIVE_2, Pin.DRIVE_3]

        def check_value(arg_str, proposed_val, allowed_vals):
            """Little helper to check that a proposed argument is one of the allowed vals.
            Returns prposed_val if value okay, so can easily one-line assignment
            """
            if proposed_val not in allowed_vals:
                raise ValueError(
                    f"Proposed Pin attribute {arg_str} value {proposed_val} not in allowed values"
                    f"{allowed_vals}"
                )
            return proposed_val

        self._mode = check_value("mode", mode, allowed_mode) if mode != -1 else self._mode
        self._pull = check_value("pull", pull, allowed_pull) if pull != -1 else self._pull
        self._drive = check_value("drive", drive, allowed_drive) if drive != -1 else self._drive

        # TODO - check whether value would still get set in other modes or just ignored
        #  Because you can still set a value with Pin.IN it just doesn't get set till mode changes
        if value is not None:
            self.value(value)

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

    def __repr__(self):
        """Basic string representation of the Pin.

        It's worth noting that the string representation of a Pin in micropython depends on the
        ESP-IDF version that the port was compiled with. In ESP-IDF v5.5.0 and above the mode,
        pull, and drive are included in the string output (if they're assigned).

        TODO - double check this and implement full once I have a proper reference from the board.
        """
        return f"Pin({self._id})"

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

    @property
    def pin_id(self) -> str | int:
        """Property to get the pin id, needed for printing in other classes as Pins normally
        print as ``Pin(<id>, ...)``, whereas when other objects print they just print the <id>
        part. So need to access the ID."""
        return self._id
