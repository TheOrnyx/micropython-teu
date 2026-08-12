"""pin.py

Micropython file that provides our mock implementation of the machine.Pin class.
Used by most other classes.
"""

import micropython
from micropython import const
from .utils import IRQ

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Callable


# pylint: disable=too-few-public-methods
class _PinBoard:
    """Basic class for the Pin.board, empty for now as ESP32 doesn't use this, but can be
    expanded on in future development."""


class Pin:
    """Basic simulated fake implementation of machine.Pin, mostly for use as attributes in
    other classes.

    Simulates the basic pin operations, such as value setting with respect to Mode, including
    buffering values in IN mode. Also has basic IRQ support.

    Uses a multiton registry for keeping pins with the same ID as the same object.

    Features to still implement:
      + Proper OPEN_DRAIN and high-impedance state implementation

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
          `Pin.PULL_UP`, or `Pin.PULL_DOWN`. Not currently using but will be needed for #80.
        :param value: Sets the initial pin value if in `Pin.OUT` or `Pin.OPEN_DRAIN` mode, buffers
          otherwise.
        :param drive: The pins output power drive, not relevant for mock but will store.
        """
        # Initialization guard, set defaults on first creation, then call `Pin.init()` which will
        # set the specified arguments and leave others as default.
        if not getattr(self, "_initialized", False) and not isinstance(pin_id, Pin):
            self._id = pin_id
            self._mode = Pin.IN
            self._pull: int | None = None
            self._drive = Pin.DRIVE_0
            self._cur_value = 0

            # The buffered pin value, set when writing in Pin.IN mode
            self._buf_val: int | None = None
            self._irq = IRQ(lambda p: None, self, 0)

        # Set an initialized guard so default values get set once
        self.init(mode=mode, pull=pull, value=value, drive=drive)
        self._initialized = True

    def init(self, mode=-1, pull=-1, value=None, drive=-1) -> None:
        """Re-initialise the pins attributes, only arguments that are specifically passed will
        be set.

        See the constructor docstring for information about the arguments.

        If mode changes and a buffered value is set then that buffered value will attempt to be
        written, unless the value argument is passed. If mode is still IN then value will be
        buffered again.
        """
        allowed_mode = [Pin.IN, Pin.OUT, Pin.OPEN_DRAIN]
        allowed_pull = [Pin.PULL_UP, Pin.PULL_DOWN]
        allowed_drive = [Pin.DRIVE_0, Pin.DRIVE_1, Pin.DRIVE_2, Pin.DRIVE_3]

        self._mode = self._check_value("mode", mode, allowed_mode) if mode != -1 else self._mode
        self._pull = self._check_value("pull", pull, allowed_pull) if pull != -1 else self._pull
        self._drive = (
            self._check_value("drive", drive, allowed_drive) if drive != -1 else self._drive
        )

        # If value is provided then attempt to set as Pin value
        # Otherwise attempt to set buf_value if it has been set
        if value is not None:
            self.value(value)
        elif self._buf_val is not None:
            self(self._buf_val)

    def value(self, x=None):
        """Either Set or get the value of this pin based on whether x is provided.

        If x is provided then it will be converted to 1 or 0 based on boolean value and stored
        and the function will return None. If x is omitted then the current value of the Pin
        will be returned.

        Will activate the interrupt if value is set and matches trigger event. Currently,
        we trigger the interrupt regardless of if one has been manually set, but the default
        initial callback won't do anything.

        The pin value will be set with respect to the Pin mode, if mode is ``Pin.OUT`` or
        ``Pin.OPEN_DRAIN`` then the value will be set. If mode is ``Pin.IN`` then the value
        will be buffered in the `_buf_val` and will be set once the mode changes back to OUT or
        OPEN_DRAIN.

        Reading the value doesn't change depending on mode as actual board logic is "undefined"
        so can just read no matter what.

        TODO - properly implement high-impedance state logic in #80
        """
        # Reading ignores mode
        if x is None:
            return self._cur_value

        new_val = int(bool(x))
        if self._mode in (Pin.OUT, Pin.OPEN_DRAIN):
            self._buf_val = None  # Force back to None as setting value clears buffer reg
            old_val = self._cur_value
            self._cur_value = int(bool(x))
            trigger = self._irq.trigger_val

            # Trigger interrupt on event/s
            if trigger & Pin.IRQ_RISING and self._cur_value > old_val:
                micropython.schedule(lambda _: self._irq(), None)
            if trigger & Pin.IRQ_FALLING and self._cur_value < old_val:
                micropython.schedule(lambda _: self._irq(), None)
        else:
            self._buf_val = new_val
        return None

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
        """Set pin output value to 1, respects mode by calling `self.value()`"""
        self.value(1)

    def off(self):
        """Set pin output value to 0, respects mode by calling `self.value()`"""
        self.value(0)

    def irq(
        self,
        handler: Callable[["Pin"], None] | None = None,
        trigger: int | None = None,  # Default IRQ_FALLING | IRQ_RISING
        wake: int | None = None,
    ) -> IRQ:
        """Configure and return interrupt handler to be called when trigger source of pin is
        active. If any arguments are provided then the IRQ will reset other unset values. If no
        arguments are provided then will just return the current IRQ object.

        Worth noting that repeated calls to IRQ will reuse the same underlying IRQ object and
        just update the handler and trigger value.

        The ESP32 port doesn't support ``priority`` or ``hard``, so those aren't included. Also
        wake will be unused for now.

        :param handler: Callback handler, should take in a Pin instance
        :param trigger: The event to trigger the interrupt, can be OR'd
        :param wake: Interrupt wake power mode, unused
        :returns: The current IRQ object.
        """
        num_set_args = [handler, trigger, wake].count(None)
        # Update IRQ if args provided
        if num_set_args > 0:
            c = handler if handler is not None else (lambda p: None)
            t = trigger if trigger is not None else (Pin.IRQ_FALLING | Pin.IRQ_RISING)
            self._irq.reinit(c, t)  # Reinit instead of replace
        return self._irq

    def toggle(self):
        """Toggle pin from 0 to 1 and vice versa, respects mode by calling `self.value()`"""
        self.value(int(not self._cur_value))

    @property
    def pin_id(self) -> str | int:
        """Property to get the pin id, needed for printing in other classes as Pins normally
        print as ``Pin(<id>, ...)``, whereas when other objects print they just print the <id>
        part. So need to access the ID."""
        return self._id

    @classmethod
    def reset_registry(cls):
        """Resets the pin registry by clearing it, Useful if you want to clear between tests.

        Shouldn't be as necessary as resetting something like the UART registry as Pin objects
        don't have as much info attached which could cause side-effects, except IRQs and mode."""
        cls._PIN_REGISTRY.clear()

    @staticmethod
    def _check_value(arg_str, proposed_val, allowed_vals):
        """Little helper to check that a proposed argument is one of the allowed vals.
        Returns proposed_val if value okay, so can easily one-line assignment
        """
        if proposed_val not in allowed_vals:
            raise ValueError(
                f"Proposed Pin attribute {arg_str} value {proposed_val} not in allowed values"
                f"{allowed_vals}"
            )
        return proposed_val
