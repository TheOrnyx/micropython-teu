"""uart.py

This file holds the ``teu.fake_machine.UART`` programmable fake class, along with the
``UARTResponseStrategy`` strategy objects.

The programmable ``UART`` fake is based on the ESP32 ports version of ``machine.UART`` and is
primarily configured through the chosen (or custom) response strategy which decides what should
be queued to the read buffer for each write. There are also additional util methods for tests.

The UART class is re-exported in the __init__ and can be accessed through
``fake_machine.UART``, the response strategies can be set/ modified using util methods or the
classes can be accessed through the module ``fake_machine.uart.UARTResponseStrategy``."""

import io
import micropython
from micropython import const

# Local Pin import
from .pin import Pin
from . import utils

# Type checkers will always have TYPE_CHECKING to true so this will only run in linters
# Thanks Micropython-Stubs for this info
TYPE_CHECKING = False
if TYPE_CHECKING:
    # Needed for linting tools
    from typing import Callable, Literal  # pylint: disable=unused-import


class UARTResponseStrategy:
    """Base class for the ``UART.write()`` response queuing strategy. Controls what gets
    appended to the read buffer when the device is written to.

    Has an abstract ``.get_response()`` method that takes in the data being written,
    along with the UART object being written to. The returned ``bytes`` object will get its
    data appended to the UARTs read buffer.

    Also has an optional abstract ``reset_state()`` method that's called when the
    ``UART.reset_stub()`` method is called. Shouldn't be needed but could be useful.
    """

    # TODO - could add add a GeneratorResponseStrategy that uses a generator function.

    def get_response(self, data: bytes, uart: "UART") -> bytes:
        """Abstract method for handling what gets appended to the read buffer.

        Takes in the data being written to the UART device and the UART object and returns the
        bytes object to queue. Returning an empty bytes object will cause nothing to be queued.

        :param data: The data being written to the UART device.
        :param uart: The UART device being used
        :returns: The bytes object to queue to the read buffer.
        """
        raise NotImplementedError

    def reset_state(self, uart: "UART") -> None:
        """Abstract method to reset the state of the strategy if any exists.

        Will just get called in ``UART.reset_stub()``, also takes in ``UART`` object in case
        needed."""
        return None


class MappingResponseStrategy(UARTResponseStrategy):
    """UART write response strategy for mapping-based configurations.

    Accepts mappings as a dictionary of "data written to device" to "response to queue to read
    buffer" like `{"A": "Resp-A"}`, so when `UART.write()` is called this strategy will return
    the value associated with the data written in the mapping dictionary, or queue the written
    data if no mapping exists.

    If this strategy is in "strict_mode" (`_is_strict` set to true, default) then when no
    mapping exists for written data it will raise an exception instead of echoing. Good for
    situations where you want to ensure only proper data is being written. Can be disabled.

    On-board, ``UART.write()`` can accept any objects that implement the 'buffer protocol'
    which means the input could be a ``bytes``, a ``str``, an ``array.array`` or any other
    buffer object. But for simplicity our mappings only officially support ``bytes`` or ``str``
    objects, with string mappings being encoded to utf-8 bytes objects before storing,
    but non-string objects get converted with plain ``bytes(obj)`` constructor, so they can be
    used if needed.

    TODO - could implement a lambda mapping type maybe
    """

    @staticmethod
    def encode_mappings_dict(mappings: dict[bytes | str, bytes | str]) -> dict[bytes, bytes]:
        """Helper method that takes in a mappings dictionary and converts each item to a bytes
        object if it isn't already, to normalize for later comparisons. Will handle strings by
        encoding but otherwise will attempt to convert with the bytes constructor, will raise
        an error if the conversion fails.

        Recommended to either using `str` or `bytes` objects for the mappings, but others are
        supported just in case, as long as they can be converted to bytes with the plain
        ``bytes(obj)`` constructor.

        :param mappings: The mappings to check and encode, each item should either be `str`,
          `bytes`, or convertable with the plain ``bytes(obj)`` constructor.
        :returns: A dictionary where all items are bytes
        """
        # Convert all to bytes
        return dict(
            (
                key.encode("utf-8") if isinstance(key, str) else bytes(key),
                val.encode("utf-8") if isinstance(val, str) else bytes(val),
            )
            for key, val in mappings.items()
        )

    def __init__(
        self, mappings: dict[bytes | str, bytes | str] | None = None, is_strict: bool = True
    ):
        """Initializes UARTResponseStrategy instance using mappings if provided.

        :param mappings: The response mappings, entries get converted to bytes.
        :param is_strict: Whether this strategy should be strict and raise exception on unmapped
          data being written, instead of echoing back. Default is True
        :raises TypeError: If mappings contains items that aren't bytes or strings.
        """
        self._mappings: dict[bytes, bytes] = (
            self.encode_mappings_dict(mappings) if mappings else {}
        )
        self._is_strict = is_strict

    def get_response(self, data: bytes, uart: "UART") -> bytes:
        """Get the correct response from the mappings. If mapping doesn't exist for `data` will
        either raise if in strict mode, or echo back written data if not.

        :raises KeyError: if `_is_strict` is true and no mapping exists for `data`.
        """
        if self._is_strict and data not in self._mappings:
            raise KeyError(f"No mapping exists for provided key: {data!r}")
        return self._mappings.get(data, data)

    def add_mapping(self, input_: str | bytes, response: str | bytes) -> None:
        """Add provided mapping to mappings dict. Converts strings to bytes."""
        b_input = input_.encode("utf-8") if isinstance(input_, str) else bytes(input_)
        b_resp = response.encode("utf-8") if isinstance(response, str) else bytes(response)
        self._mappings[b_input] = b_resp

    def set_mappings(
        self, mappings: dict[bytes | str, bytes | str], is_strict: bool | None = None
    ) -> None:
        """Set the response mappings to the provided dict, replacing original mappings. Entries
        are converted to bytes objects for compatibility. Updates is_strict if provided.
        """
        self._mappings = self.encode_mappings_dict(mappings) if mappings else {}
        self._is_strict = is_strict if is_strict is not None else self._is_strict

    def reset_state(self, uart: "UART") -> None:
        """Reset the state of this strategy, removes mappings and sets ``is_strict`` to default
        True."""
        self._mappings.clear()
        self._is_strict = True

    @property
    def is_strict(self) -> bool:
        """Returns whether strategy is in strict mode."""
        return self._is_strict

    @is_strict.setter
    def is_strict(self, strict: bool):
        """Set whether strategy should be in strict mode."""
        self._is_strict = strict


class ListResponseStrategy(UARTResponseStrategy):
    """UART write response strategy for supporting list-based responses.

    Holds a list/ queue of responses like `[b"A", b"B", b"C", b"D",]` and on each `UART.write()`
    the next item will be queued for response, with multiple options for handling list
    exhaustion. List act likes a FIFO queue.

    String response items will be internally converted to `bytes` before being added to the list,
    for compatibility and safety with conversions and comparisons.

    Accepts 4 different options for controlling what to do when list is exhausted. These options
    are:

    * `"empty"` - respond with empty bytes (will make read return None, replicating timeout).
    * `"repeat_last"` - responds with last item in list whenever UART written to.
    * `"raise"` - raises an `IndexError` when attempting a UART write.
    * `"cycle"` - Switch the index back to the first item when reaching the end.
    """

    # Allowed on_exhausted strings
    ALLOWED_ON_EXHAUSTED = ("empty", "repeat_last", "raise", "cycle")

    def __init__(self, responses: list[str] | list[bytes], on_exhausted: str = "empty"):
        """Initialize response strategy, see class docstring for more info.

        :param responses: the response list, string elements are converted to bytes.
        :param on_exhausted: "empty", "repeat_last", "raise", or "cycle", see class docstring.
        :raises ValueError: If `on_exhausted` is not one of the allowed values.
        """
        if on_exhausted not in self.ALLOWED_ON_EXHAUSTED:
            raise ValueError(f"Unknown on_exhausted option: {on_exhausted}")
        self._responses = [
            r.encode("utf-8") if isinstance(r, str) else bytes(r) for r in responses
        ]
        self._index = 0  # The index into the list
        self._on_exhausted = on_exhausted

    def get_response(self, data: bytes, uart: "UART") -> bytes:
        # List exhausted
        if self._index >= len(self._responses):
            if self._on_exhausted == "repeat_last" and self._responses:
                return self._responses[-1]
            if self._on_exhausted == "raise":
                raise IndexError("UART Response list exhausted")
            if self._on_exhausted == "cycle" and self._responses:
                self._index = 1  # 1 since returning 0-th element
                return self._responses[0]
            return b""

        response = self._responses[self._index]
        self._index += 1
        return response

    def set_responses(self, responses: list[str] | list[bytes]) -> None:
        """Update the response list and reset index. To help reuse instances.

        :param responses: The new response list, string elements are converted to bytes."""
        self._index = 0
        self._responses = [r.encode("utf-8") if isinstance(r, str) else r for r in responses]

    def add_responses(
        self, responses: list[str] | list[bytes], reset_index: bool = False
    ) -> None:
        """Add responses to the response list."""
        bytes_responses = [r.encode("utf-8") if isinstance(r, str) else r for r in responses]
        self._responses.extend(bytes_responses)
        self._index = 0 if reset_index else self._index

    def reset_state(self, uart: "UART") -> None:
        """Reset state by clearing list, resetting index and setting `_on_exhausted` back to
        default 'empty'"""
        self._responses.clear()
        self.on_exhausted = "empty"
        self._index = 0

    @property
    def on_exhausted(self) -> str:
        """Property for ``_on_exhausted``"""
        return self._on_exhausted

    @on_exhausted.setter
    def on_exhausted(self, on_exhausted: str):
        """Update ``_on_exhausted``.

        :raises ValueError: if `on_exhausted` not one of the allowed values.
        """
        if on_exhausted not in self.ALLOWED_ON_EXHAUSTED:
            raise ValueError(f"Unknown on_exhausted option: {on_exhausted}")
        self._on_exhausted = on_exhausted


class ConstantResponseStrategy(UARTResponseStrategy):
    """UART response strategy for queueing the same constant response in the read buffer on
    each write call.
    """

    def __init__(self, response: str | bytes):
        """Initialize constant response strategy with single item."""
        self._response = (
            response.encode("utf-8") if isinstance(response, str) else bytes(response)
        )

    def get_response(self, data: bytes, uart: "UART") -> bytes:
        return self._response

    def set_constant_response(self, response: str | bytes) -> None:
        """Set the constant response for this strategy. To allow reusing class instance."""
        self._response = (
            response.encode("utf-8") if isinstance(response, str) else bytes(response)
        )

    def reset_state(self, uart: "UART") -> None:
        """Resets by just setting the constant response to an empty bytes object. Maybe not
        best but should be fine."""
        self._response = b""


class CallbackResponseStrategy(UARTResponseStrategy):
    """UART write response strategy for getting the response through a Callback which takes
    in the written data and the UART object and returns the `bytes` object to queue.

    Callback would be something like ``lambda data, uart: b"OK"`` or a function that takes in
    a `bytes` and `UART` object and returns a `bytes`.
    """

    def __init__(self, response_cb: Callable[[bytes, "UART"], bytes]):
        """Initializes the callback strategy with the provided callback.

        :param response_cb: the response callback to use when UART is written to.
        :type response_cb: callback in form of ``Callable[[bytes, "UART"], bytes]``. Must take in
            a bytes for data written and the UART that was written to, and return bytes to queue.
        :raises TypeError: if `response_cb` is not callable
        """
        if not callable(response_cb):
            raise TypeError("Provided response callback is not callable")
        self._callback = response_cb

    def get_response(self, data: bytes, uart: "UART") -> bytes:
        """Get the response to queue for this write by calling the callback.

        :raises TypeError: If the callback doesn't return a ``bytes`` object.
        """
        response = self._callback(data, uart)
        if not isinstance(response, bytes):
            raise TypeError(f"Callback response {response} was not of type bytes")
        return response

    def reset_state(self, uart: "UART") -> None:
        """Resets the state by setting the callback to just a plain lambda that returns empty
        bytes."""
        self._callback = lambda d, u: b""


class EchoResponseStrategy(UARTResponseStrategy):
    """Very basic UART response strategy that just echoes back whatever was written. No reset
    logic needed."""

    def get_response(self, data: bytes, uart: "UART") -> bytes:
        return data


# ----------------- Regular UART class ---------------------


class UART(io.IOBase):
    """Flexible test fake implementation of the ESP32 port implementation of ``machine.UART``.
    Fills out all expected API methods and constants from board version, replicates the
    multiton registry so the same instance for an ID is returned, and provides configurable
    test support.

    This class operates as a basic simulated fake object, when written to using `UART.write()`
    the object will use its ``UARTResponseStrategy`` response strategy to decide what to append
    to the read buffer, which gets returned on `UART.read()` calls. Allowing test authors to
    simulate a basic UART device by mimicking write responses to test driver logic.

    Test authors can also register a basic ``Callable[["UART"], None]`` read callback with
    ``.set_read_callback(cb)``. This will get ran with the UART object when one of the
    ``.read()``, ``.readinto()``, ``.readline()`` methods are called and can be used to inject
    data into the read buffer or modify the object. Useful for mimicking devices that constantly
    stream data to be read.

    These are the existing `UARTResponseStrategy` classes (check the individual class
    docstrings for more info):

    * `MappingResponseStrategy`: for defining dictionary mappings of written data -> queued
      response. For example, ``{"A": "Resp-A", "B": "Resp-B"}`` will queue "Resp-A" when "A" is
      written to the UART device and "Resp-B" when "B" is written.
      Queues the written data if no mapping exists, raises in strict mode.
    * `ListResponseStrategy`: for defining a list of responses where each write will queue
      the next element to the read buffer.
      Has 4 different options for controlling operation when list is exhausted: "empty",
      "repeat_last", "raise", and "cycle".
    * `ConstantResponseStrategy`: for queueing the same data to the read buffer each write.
    * `CallbackResponseStrategy`: for when you want more control over what to queue, will run a
      user defined callback which takes in the bytes being written and the UART object and should
      return the data to queue.
    * `EchoResponseStrategy`: simple example response strategy that just echoes back the data.

    See the ``docs/designs/uart.md`` file for more information on how the class operates and
    examples for how to use it.

    To create instances of this class for testing test authors can either use the
    ``UART.create_stub()`` factory for tests which allows you to instantiate the fake with a
    configured response strategy all in one line.

    Alternatively the constructor can be used directly and the response strategy can be
    configured afterwards. This can be helpful for tests where you're testing a class where
    initializing it and the uart is helpful in the setUp (see the example test_modem_unix.py
    for an example of this usage).

    Implements functions for the io.IOBase abstract class to be able to used in stream
    operations. Might not support all stream operations, but I know printing to this as a file
    works. Currently, uses a workaround to avoid a crash (see #79).

    Is also iterable.
    """

    # Module-specific constants
    # Definitions for these can be found in the ESP-IDF codebase at
    # components/hal/include/hal/uart_types.h
    RTS = const(0x1)  # UART_HW_FLOWCTRL_RTS = 1
    CTS = const(0x2)  # UART_HW_FLOWCTRL_CTS = 2
    INV_TX = const(1 << 5)  # UART_SIGNAL_TXD_INV = 32
    INV_RX = const(1 << 2)  # UART_SIGNAL_RXD_INV = 4
    INV_RTS = const(1 << 6)  # UART_SIGNAL_RTS_INV = 64
    INV_CTS = const(1 << 3)  # UART_SIGNAL_CTS_INV = 8
    IRQ_RXIDLE = const(0x1000)  # Defined in machine_uart.c

    # Found in components/esp_driver_uart/include/driver/uart.h, ordinal enum
    IRQ_RX = const(1 << 0)  # first enum val, shifted in machine_uart def
    IRQ_BREAK = const(1 << 1)  # Second element of uart_event_type_t enum (so 1 ordinal)

    # Custom constants
    WRITE_BUF_SIZE = const(512)  # Default byte size for write buffer

    # Class attribute for allowed UART IDS
    # TODO - maybe allow modifying this later.
    ALLOWED_IDS = (1, 2)

    # Default pin assignment for UART ids. Key is UART ID and value is pin ids ``(TX, RX)``
    # Using pin ID rather than instance for safety (and to reduce module loading overhead).
    # NOTE - UART1 pins are using SPIRAM default pins since our target board has WROVER-E.
    _DEFAULT_PINS: dict[int, tuple[int | str, int | str]] = {1: (5, 4), 2: (17, 16)}

    # Multiton lookup registry for UART instances
    _UART_REGISTRY: dict[int, "UART"] = {}

    def __new__(
        cls,
        uid: int,
        override_id_checks: bool = False,
        **kwargs,
    ):
        """Override of instance creation, used to return existing instance if uid matches an
        item in the `_UART_REGISTRY`.

        :param override_id_checks: Whether to ignore the checks that confirm the ID would exist on
          board, False by default. Shouldn't be needed but will keep for testing.
        """
        if not override_id_checks and uid not in cls.ALLOWED_IDS:
            raise ValueError(
                f"UART({uid}) is not an allowed UART ID, please use one of {cls.ALLOWED_IDS}"
            )

        if uid in cls._UART_REGISTRY:
            return cls._UART_REGISTRY[uid]  # Reuse existing

        # Create new instance
        # uart = super().__new__(cls)
        uart = object.__new__(cls)  # Calling object.__new__() prevents IOBase crash.
        return uart

    def __init__(
        self,
        uid: int,
        baudrate: int = -1,
        bits: int = 0,
        parity: int | None = -1,
        stop: int = 1,
        tx: Pin | int | str | None = None,
        rx: Pin | int | str | None = None,
        txbuf: int = -1,
        rxbuf: int = -1,
        timeout: int = -1,
        timeout_char: int = -1,
        invert: int = -1,
        flow: int = -1,
        rts: Pin | int | str | None = None,
        cts: Pin | int | str | None = None,
        add_to_registry: bool = True,
        override_id_checks: bool = False,
        response_strategy: UARTResponseStrategy | None = None,
        **kwargs,
    ):
        """Initializes UART instance, guarded against re-initialization from __new__ so the
        buffers and strategy don't get reset on future initializations. First init will set
        default values, every init (including first) calls ``.init()`` with args.

        When a UART object is initialized only arguments that are explicitly provided will be
        set, unprovided arguments will be set to the default value if this is first
        initialization, otherwise they will remain as the previously set value. This matches
        the board functionality where the constructor can be used to re-init certain attributes.

        When initializing a UART object the provided pins for `tx`, `rx`, `rts`, and `cts` can
        either be the Pin instance, a pin ID (int or str), -1 to assign no pin, or None (
        default) to keep previous Pin.

        :param add_to_registry: Extra test arg for whether to add this item to the register on
          first initialization. Not really needed.
        """
        # Re-initialization guard, sets the attributes to defaults on first run.
        # Init() gets called after which will set any specified arguments.
        if not getattr(self, "_initialized", False):
            # super().__init__()

            def_tx, def_rx = self._get_default_pins(uid)

            # Special attributes
            self.id_ = uid
            self._read_buf: bytearray = bytearray(0)
            self._response_strategy: UARTResponseStrategy = (
                response_strategy or EchoResponseStrategy()  # Default to echo
            )
            self._write_buf = micropython.RingIO(UART.WRITE_BUF_SIZE)
            self._break_callback = None
            self._read_callback = None  # Read callback, gets called in readinto if not None

            # Regular attributes, set to default on first.
            # Explicitly provided attributes will get set in following init() call
            self.baudrate = 115200
            self.bits = 8
            self.parity: int | None = (
                # docs and implementation seems to differ for parity
                # docs use None, 0 (even), 1 (odd).
                # C source code uses 0 (None), 1 (even), 2 (odd), but prints them as doc version.
                None
            )
            self.stop = 1
            self.tx: Pin | None = def_tx
            self.rx: Pin | None = def_rx
            self.txbuf = 256
            self.rxbuf = 256
            self.timeout = 0
            self.timeout_char = 0
            self.invert = 0
            self.flow = 0
            self.rts: Pin | None = None
            self.cts: Pin | None = None

            # Add to registry
            self._in_registry = add_to_registry
            if add_to_registry:
                self._UART_REGISTRY[uid] = self

            self._initialized = True

        # Don't want black to split this onto 15 lines
        # fmt: off
        self.init(
            baudrate, bits, parity, stop, tx, rx, txbuf, rxbuf, timeout, timeout_char, invert,
            flow, rts, cts
        )
        #fmt: on

    def init(
        self,
        baudrate: int = 0,
        bits: int = 0,
        parity: int | None = -1,
        stop: int = 0,
        tx: Pin | int | str | None = None,
        rx: Pin | int | str | None = None,
        txbuf: int = -1,
        rxbuf: int = -1,
        timeout: int = -1,
        timeout_char: int = -1,
        invert: int = -1,
        flow: int = -1,
        rts: Pin | int | str | None = None,
        cts: Pin | int | str | None = None,
    ):
        """Reinitialize the set UART attributes. Performed by user code. Only sets arguments
        that were specified, any unspecified arguments will remain as their previous values.

        The basic validation logic for the args is replicated, with ValueErrors being raised
        for wrong assignments. This is implemented based on the C code.
        """
        # Instance attributes
        self.baudrate = baudrate if baudrate > 0 else self.baudrate

        # Bits: can either be 5,6,7,8. 0 Does nothing, anything else raises
        allowed_bits = (5, 6, 7, 8)
        if bits in allowed_bits:
            self.bits = bits
        elif bits != 0:
            raise ValueError("invalid data bits")

        # Parity: None is None, odd value makes 1, even makes 2. -1 is sentinel for previous.
        if parity is None:
            self.parity = None
        elif parity != -1 and parity & 1:
            self.parity = 1
        elif parity != -1:
            self.parity = 2

        # Stop: Can either be 1 or 2, 0 does nothing. Others raise
        allowed_stop = (1, 2)
        if stop in allowed_stop:
            self.stop = stop
        elif stop != 0:
            raise ValueError("invalid stop bits")

        self.tx = self._pin_val(tx, self.tx)
        self.rx = self._pin_val(rx, self.rx)
        self.rts = self._pin_val(rts, self.rts)
        self.cts = self._pin_val(cts, self.cts)
        self.txbuf = txbuf if txbuf > 0 else self.txbuf
        self.rxbuf = rxbuf if rxbuf > 0 else self.rxbuf

        self.timeout = timeout if timeout > -1 else self.timeout
        self.timeout_char = timeout_char if timeout_char > -1 else self.timeout_char

        # Invert: -1 for previous, raises if not valid invert, using same logic as board
        inv_mask = self.INV_TX | self.INV_RX | self.INV_RTS | self.INV_CTS
        if invert != -1:
            if invert & (~inv_mask):
                raise ValueError("invalid inversion mask")
            self.invert = invert

        # Flow: Same logic as invert
        flow_mask = self.RTS | self.CTS
        if flow != -1:
            if flow & (~flow_mask):
                raise ValueError("invalid flow control mask")
            self.flow = flow

    @classmethod
    def reset_registry(cls):
        """Helper method to reset the `_UART_REGISTRY` registry, reacommended to call between
        tests to ensure nothing stored in registry instances remains between tests,
        such as queued buffer data."""
        cls._UART_REGISTRY.clear()

    @staticmethod
    def create_stub(
        uid: int,
        is_strict: bool = True,
        mappings: dict[bytes | str, bytes | str] | None = None,
        response_list: list[str] | list[bytes] | None = None,
        list_exhausted_behaviour: Literal["empty", "repeat_last", "raise", "cycle"] | None = None,
        constant_response: str | bytes | None = None,
        response_callback: Callable[[bytes, "UART"], bytes] | None = None,
        custom_response: UARTResponseStrategy | None = None,
        initial_buffer_contents: bytes = b"",
        read_cb: Callable[["UART"], None] | None = None,
        **kwargs,
    ) -> "UART":
        """Factory for creating a UART test object with programmed response behaviour.
        Alternative to manually constructing both the UART and response strategy. See `UART` class
        docstring for more information about the response strategies and their behaviour.

        Will raise an exception if multiple response strategy items are provided. If none are
        provided then it will default to using the `EchoResponseStrategy`.

        The created instance will be added to the `_UART_REGISTRY` multiton registry so code
        under test will receive the configured version when instantiating their own UART.

        :param uid: The id for this UART device.
        :param is_strict: makes the response strategy more strict (if supported). Currently, will
          make mapping responses raise if unmapped data is written and will default the list
          exhausted behaviour of `ListResponseStrategy` to "raise" if no behaviour was specified.
          True by default.
        :param mappings: The mappings for the `MappingResponseStrategy`, what you'd normally pass
          to `set_mappings`. Maps written data to the response to queue to the read buffer.
        :param response_list: The response list for the `ListResponseStrategy`, each UART write
          will queue the next list item.
        :param list_exhausted_behaviour: Controls the behaviour of the `ListResponseStrategy` when
          it runs out of responses. Accepts "empty", "repeat_last", "raise", or "cycle".
          Defaults to "empty" (unless `is_strict` is true, which will default to "raise").
        :param constant_response: Defines the single value for `ConstantResponseStrategy` to use.
        :param response_callback: Callback of form ``Callable[[bytes, "UART"], bytes]`` for
          `CallbackResponseStrategy` to use.
        :param custom_response: A subclass of `UARTResponseStrategy`, for custom strategies.
        :param initial_buffer_contents: The initial contents to fill the `read_buf` with.
        :param kwargs: For any other attributes that you want to pass along to the UART
          constructor. For specifying things like pin values.
        :param read_cb: Read callback to pass into ``.set_read_callback()``, gets called when
          device is being read from.
        :raises ValueError: if multiple response strategies are provided.
        """
        # Check multiple responses aren't provided.
        provided_responses = [
            x is not None
            for x in (
                mappings,
                response_list,
                constant_response,
                response_callback,
                custom_response,
            )
        ]
        if sum(provided_responses) > 1:
            raise ValueError("Only one UART response strategy may be provided.")

        uart = UART(uid, add_to_registry=True, **kwargs)

        if mappings is not None:
            uart.response_strategy = MappingResponseStrategy(mappings, is_strict)
        elif response_list is not None:
            list_exhausted_behaviour = list_exhausted_behaviour or (
                "raise" if is_strict else "empty"
            )
            uart.response_strategy = ListResponseStrategy(response_list, list_exhausted_behaviour)
        elif constant_response is not None:
            uart.response_strategy = ConstantResponseStrategy(constant_response)
        elif response_callback is not None:
            uart.response_strategy = CallbackResponseStrategy(response_callback)
        elif custom_response is not None:
            uart.response_strategy = custom_response

        # If none of the above are chosen then the default will remain as `EchoResponseStrategy`

        if read_cb:
            uart.set_read_callback(read_cb)
        if initial_buffer_contents:
            uart.push_response(initial_buffer_contents)
        return uart

    def deinit(self):
        """deinit, currently just does nothing.

        Used to remove the item from the registry but changed as can't imagine being useful.
        """
        return None

    def any(self):
        """Return integer for number of characters that can be read without blocking. Just
        returns the length of the ``_read_buf``."""
        return len(self._read_buf)

    def read(self, nbytes=None) -> bytes | None:
        """Read data from the buffer fake `_read_buf` read buffer, consuming bytes read and
        returning them. If `nbytes` is not None then will only read a max of that many bytes
        from the buffer.

        Return None and run read callback if buffer is empty, simulating timeout.

        Delegates to `readinto` to simplify logic, which also runs the read callback.
        """
        if not self._read_buf:
            self._call_read_cb()  # Call read callback before returning
            return None

        nbytes = nbytes if nbytes is not None else len(self._read_buf)
        buf = bytearray(nbytes)
        bytes_read = self.readinto(buf, nbytes)
        return bytes(buf[:bytes_read])

    def readinto(self, buf: bytearray, nbytes=None) -> int | None:
        """Read bytes into buf. Returns num bytes stored in `buf` or None if no data available
        (to simulate timeout).

        Also calls the read callback with `self`, if callback has been set.
        """

        if not self._read_buf:
            self._call_read_cb()  # Call read callback before returning
            return None

        max_bytes = min(nbytes or len(buf), len(buf), len(self._read_buf))
        buf[0:max_bytes] = self._read_buf[:max_bytes]  # Check if inclusive
        self._read_buf = self._read_buf[max_bytes:]

        # Call read callback if defined
        if self._read_callback is not None and callable(self._read_callback):
            self._read_callback(self)
        return max_bytes

    def readline(self, size: int | None = None) -> bytes | None:
        """Read line and return the read line as a bytes object, or None on timeout (no data).
        If there is no newline in data then whole buffer will be read.

        Calculates the amount of data to read and then delegates to ``.readinto()`` to get the
        data, which also runs the read callback.
        """

        if self.any() == 0:  # Return none if no data
            self._call_read_cb()  # Call read callback before returning
            return None

        # Unclear whether read max is -1 or None so just turn -1 to None
        size = None if size == -1 else size

        # start with maxlen and change to newline index if present
        newline_index = len(self._read_buf)
        if b"\n" in self._read_buf:
            newline_index = self._read_buf.find(b"\n") + 1  # Include newline

        index = min(size, newline_index) if size else newline_index
        buf = bytearray(index)
        self.readinto(buf, nbytes=index)
        return bytes(buf)

    def write(self, buf) -> int:
        """
        Write buffer contents to device and return the number of bytes written to the "device",
        (so should just return the size of `buf`).

        Will use the `UART._response_strategy` to decide how to respond, the return value of
        `UARTResponseStrategy.get_response()` will be appended to the `_read_buf` to be read in
        the next `UART.read()` call.

        The default response strategy is to echo back written data, see the class docstring for
        info about pre-defined response strategies.

        Also copies the contents of `buf` into the `_write_buf` for inspection in tests.

        :param buf: The data to write to the UART "device", should either be String or buffer
          object, this will attempt to convert non-string inputs to bytes using constructor
          ``bytes(obj)``. Which should support buffer objects.

        TODO - could add a control for whether subsequent write calls will append _read_buf data
        or replace it (because a UART device might not buffer data like that)
        """

        # For safety and compatibility if a user passes in a string then we convert to bytes
        # Just to keep all internal processing using bytes objects.
        byte_buf = buf.encode("utf-8") if isinstance(buf, str) else bytes(buf)

        response = self._response_strategy.get_response(byte_buf, self)
        self._read_buf += response
        self._write_buf.write(byte_buf)

        return len(byte_buf)

    def __iter__(self):
        """Called when using object as iterator, don't need to do much as UART iteration uses
        readline."""
        return self

    def __next__(self) -> bytes:
        """Next item when iterating, uses readline if device contains data."""
        if self.any() != 0:
            data = self.readline()
            return data or b""

        raise StopIteration

    def ioctl(self, op: int, arg) -> int:
        """Function for handling ioctl interfacing, docs seem to indicate it's required for
        stream usage.

        Just gonna mostly copy the recommended basic implementation faking flush, poll, and
        close.
        """

        # print(f"DEBUG: uart ioctl called with op {op}, arg {arg}")

        # op constants from micropython/py/stream.h
        # pylint: disable=invalid-name
        _MP_STREAM_POLL = const(3)
        _MP_STREAM_POLL_RD = const(0x0001)
        _MP_STREAM_FLUSH = const(1)
        _MP_STREAM_CLOSE = const(4)

        if op == _MP_STREAM_POLL:
            ret = _MP_STREAM_POLL_RD if self.any() else 0
            return ret
        if op in (_MP_STREAM_FLUSH, _MP_STREAM_CLOSE):
            return 0

        return -1  # Unsupported operation return

    def sendbreak(self):
        """Send break condition on the bus, calls the `_break_callback` with `self` if not None"""
        if self._break_callback is not None and callable(self._break_callback):
            self._break_callback(self)

    def flush(self):
        """Wait until all data has been sent. Does nothing"""
        pass

    def txdone(self):
        """Returns whether data currently being sent or data transfer is currently occuring.

        Mocked version currently just returns true as we don't simulate the individual data
        sending.
        """
        return True

    def irq(self, handler=None, trigger=0, hard=False):
        """Configures interrupt handler to be called when UART event occurs and returns IRQ object.

        This will have a very basic implementation which will just do basic parameter
        validation and then return a canned IRQ object, with the same methods but canned return
        values.

        For future work this class should properly implement the interrupts, this method
        doesn't store the IRQ (instances reuse same value) nor does the class call the handler
        when the interrupt events occur. Mostly due to time and a lack of reference code using
        this feature.
        """
        if handler is not None and not callable(handler):
            raise ValueError("handler must be None or callable")

        # Convert None to empty lambda, so util irq doesn't break
        handler = (lambda x: None) if handler is None else handler

        allowed_triggers = self.IRQ_RX | self.IRQ_RXIDLE | self.IRQ_BREAK
        trig_not_supported = trigger & (~allowed_triggers)
        if trigger != 0 and trig_not_supported:
            raise ValueError(f"trigger {trigger:#04x} unsupported")
        if hard:
            raise ValueError("hard IRQ is not supported")

        return utils.IRQ(handler=handler, target=self, trigger=trigger)

    def __repr__(self):
        """Returns a tuple-like representation of the UART and its items.

        Example default output from ESP32:
        ``UART(1, baudrate=115201, bits=8, parity=None, stop=1, tx=10, rx=9, rts=-1, cts=-1,
        txbuf=256, rxbuf=256, timeout=0, timeout_char=0, irq=0)``

        "invert" and "flow" only get printed if set.
        """
        tx_str = self.tx.pin_id if self.tx else -1
        rx_str = self.rx.pin_id if self.rx else -1
        rts_str = self.rts.pin_id if self.rts else -1
        cts_str = self.cts.pin_id if self.cts else -1

        uart_str = (
            f"UART({self.id_}, baudrate={self.baudrate}, bits={self.bits}, parity={self.parity}, "
            f"stop={self.stop}, tx={tx_str}, rx={rx_str}, rts={rts_str}, cts={cts_str}, "
            f"txbuf={self.txbuf}, rxbuf={self.rxbuf}, timeout={self.timeout}, "
            f"timeout_char={self.timeout_char}, irq=0"
        )

        # Invert and flow take specific formatting, prints as flags or'd | together
        if self.invert:
            inv_flags = (
                (self.INV_TX, "INV_TX"),
                (self.INV_RX, "INV_RX"),
                (self.INV_RTS, "INV_RTS"),
                (self.INV_CTS, "INV_CTS"),
            )
            uart_str += ", invert=" + "|".join(
                name for flag, name in inv_flags if self.invert & flag
            )

        if self.flow:
            flow_flags = ((self.RTS, "RTS"), (self.CTS, "CTS"))
            uart_str += ", flow=" + "|".join(
                name for flag, name in flow_flags if self.flow & flag
            )

        uart_str += ")"
        return uart_str

    # ---------- Stub util methods -------

    def reset_stub(self, reset_strategy=True) -> None:
        """Reset the stub state of the UART test object. Shouldn't be too necessary but helpful
        to have.

        Clears read and write buffers and the break and read callbacks. Resets the response
        strategy if `reset_strategy` is True.

        TODO - maybe allow this to reset the actual UART attributes to defaults.
        """
        self._read_buf = bytearray()
        self._write_buf = micropython.RingIO(UART.WRITE_BUF_SIZE)
        self.set_break_callback(None)
        self.set_read_callback(None)
        if reset_strategy:
            self._response_strategy.reset_state(self)

    def set_read_callback(self, cb: Callable[["UART"], None] | None) -> None:
        """Set or unset the read callback that gets ran whenever this device is written to,
        with this instance being passed in. Useful for mimicking devices that constantly stream
        data whenever read.

        :param cb: Either callable that accepts a UART, or ``None`` to remove callback
        :raises TypeError: If provided `cb` is not callable or None.
        """
        if cb is None:
            self._read_callback = None
        elif callable(cb):
            self._read_callback = cb
        else:
            raise TypeError("Provided read callback was not Callable")

    def register_device(self) -> None:
        """Adds device to the uart registry, same as `add_to_registry` init argument, shouldn't
        be needed."""
        self._UART_REGISTRY[self.id_] = self

    def push_response(self, buf: bytes):
        """Queue bytes onto the read buffer, appending to the end. Useful for pushing an
        initial response when testing."""
        self._read_buf += utils.buffer_to_bytes(buf)

    def get_written_data(self) -> bytes:
        """Return bytes written to the UART device by reading `_write_buf`. Consumes contents."""
        return self._write_buf.read()

    def set_break_callback(self, cb: Callable[["UART"], None] | None) -> None:
        """Set a callback for the ``.sendbreak()`` method, will be called with the UART object.
        Passing in None will disable the callback.

        :raises TypeError: If provided `cb` is not callable or None.
        """
        if cb is None:
            self._break_callback = None
        elif callable(cb):
            self._break_callback = cb
        else:
            raise TypeError("Provided break callback was not Callable")

    def _call_read_cb(self) -> None:
        """Basic helper to run the read callback with `self` if set. To reduce code
        duplication. Does nothing if read callback not set.
        """
        if self._read_callback is not None and callable(self._read_callback):
            self._read_callback(self)

    # -------- Util methods for controlling response strategy -----
    #
    # Util methods for either switching to a specific response strategy (and adding responses
    # to it) or configuring an existing response strategy.

    def set_mappings(
        self, mappings: dict[bytes | str, bytes | str], is_strict: bool = True
    ) -> None:
        """Set the ``UART.write()`` input to ``UART.read()`` output mappings, replaces existing
        mappings if any exist.

        If the response_strategy is not currently `MappingResponseStrategy` then a new instance
        will be created and provided with the mappings. Otherwise, we reuse existing instance.

        Any mappings that are strings will be converted to `bytes` objects before storing, for more
        information see the docs for `MappingResponseStrategy`.

        :param mappings: The dictionary for the UART mappings. The key represents data written
          to the device and the value represents the data to queue in the read buffer, which will
          be returned when ``UART.read()`` is called.
        :param is_strict: Whether to put the response strategy in strict mode, where unknown
          mappings cause a raise, True by default.
        """
        if isinstance(self._response_strategy, MappingResponseStrategy):
            self._response_strategy.set_mappings(mappings, is_strict)
        else:
            self._response_strategy = MappingResponseStrategy(mappings, is_strict)

    def add_mapping(self, input_: bytes | str, response: bytes | str) -> None:
        """Add a new mapping response entry, raises TypeError if the response strategy is not
        `MappingResponseStrategy`. Typically, ``UART.set_mappings()`` is preferred for use.

        :raises TypeError: If the response strategy is not currently `MappingResponseStrategy`
        """
        if not isinstance(self._response_strategy, MappingResponseStrategy):
            raise TypeError(
                "UART.add_mapping() requires response strategy to be MappingResponseStrategy, "
                "please use UART.set_mappings()."
            )

        self._response_strategy.add_mapping(input_, response)

    def set_constant_response(self, constant_response: str | bytes) -> None:
        """Set a constant response for this UART, will cause any write operation to this device
        to queue up the provided `constant_response` in the read buffer.

        The response strategy for this device will be changed to a ``ConstantResponseStrategy``
        if it isn't already.

        :param constant_response: The constant response to queue on write. Will get converted
          to a bytes object if it's a string.
        """
        # Reuse strategy if currently a Constant
        if isinstance(self._response_strategy, ConstantResponseStrategy):
            self._response_strategy.set_constant_response(constant_response)
        else:
            self._response_strategy = ConstantResponseStrategy(constant_response)

    def set_response_list(
        self, responses: list[str] | list[bytes] | None = None, on_exhaust: str | None = None
    ) -> None:
        """Set a response list for this UART, where each write call will queue the next item to
        the read buffer, with `on_exhausted` controlling what happens when the list is
        exhausted. See ``ListResponseStrategy`` docstring for more information.

        The response strategy for this device will be changed to a ``ListResponseStrategy`` if
        it isn't already. If currently using List response then the instance will be reused and
        the responses and on_exhausted will be updated, just in case.

        If `responses` is None and this object is using a list response strategy then this
        method will update the on_exhausted of that strategy. Will raise if not.

        :param responses: The response list, elements are converted to bytes. If None
          then will update strategy's on_exhausted.
        :param on_exhaust: Either one of "empty", "repeat_last", "raise", or "cycle", or if None
          then either keep the existing on_exhausted value or default to "empty".
        :raises TypeError: if trying to update the strategy's on_exhausted when strategy is not
          currently a list response.
        """
        # Reuse if currently is ListResponse
        if isinstance(self._response_strategy, ListResponseStrategy):
            if responses is not None:
                self._response_strategy.set_responses(responses)
            if on_exhaust is not None:
                # Not sure why pylint complains here
                # pylint: disable-next=attribute-defined-outside-init
                self._response_strategy.on_exhausted = on_exhaust
        elif responses is None:  # Trying to update when not a list response
            raise TypeError(
                "Error: trying to update UART ListResponseStrategy on_exhausted when current "
                "strategy is not ListResponseStrategy"
            )
        else:  # Create new
            exhaust = on_exhaust if on_exhaust is not None else "empty"
            self._response_strategy = ListResponseStrategy(responses, exhaust)

    def add_responses_to_list(
        self, responses: list[str] | list[bytes], reset_index: bool = False
    ) -> None:
        """Updates the response list to append the new responses to the end, raises if not
        currently using a ListResponseStrategy.

        :param responses: The responses to append to the end of the current response list.
        :param reset_index: Whether to reset the list responses index back to 0.
        :raises TypeError: If the response strategy is not a ``ListResponseStrategy``
        """
        if not isinstance(self._response_strategy, ListResponseStrategy):
            raise TypeError(
                "Error: trying to add to response list but response strategy is not "
                f"ListResponseStrategy, currently: {type(self._response_strategy).__name__}"
            )
        self._response_strategy.add_responses(responses, reset_index)

    @property
    def response_strategy(self) -> UARTResponseStrategy:
        """Get the current response strategy"""
        return self._response_strategy

    @response_strategy.setter
    def response_strategy(self, strategy: UARTResponseStrategy):
        self._response_strategy = strategy

    @staticmethod
    def _pin_val(p_id: Pin | int | str | None, old_pin) -> Pin | None:
        """Tiny helper to return the value to set for a pin, respects the rules of -1
        unasigning the pin and None leaving previous.

        Maybe move to a like util area."""
        if p_id == -1:
            return None
        return Pin(p_id) if p_id is not None else old_pin

    @classmethod
    def _get_default_pins(cls, uid: int):
        """Get a tuple of (tx, rx) default pins for given uart ID.

        To keep ID checking occurring only once per object if the ID shouldn't exist then
        return None's.
        """
        if uid not in cls._DEFAULT_PINS:
            return None, None
        def_tx, def_rx = cls._DEFAULT_PINS[uid]
        p_tx = Pin(def_tx)
        p_rx = Pin(def_rx)
        return p_tx, p_rx
