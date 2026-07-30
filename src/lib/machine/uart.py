"""uart.py

MicroPython file for the UART test objects, classes are reexported in main machine module __init__
"""

import io

import micropython
from micropython import const
import machine

# Type checkers will always have TYPE_CHECKING to true so this will only run in linters :3
# Thanks Micropython-Stubs for this info
TYPE_CHECKING = False
if TYPE_CHECKING:
    # Needed for linting tools
    from typing import Callable, Literal  # pylint: disable=unused-import


class UARTResponseStrategy:
    """Base class for the :meth:`UART.write()` response queuing strategy to control what gets
    appended to the read buffer.
    """

    def get_response(self, data: bytes, uart: "UART") -> bytes:
        """Abstract method for handling what gets appended to the read buffer.

        Takes in the data being written to the UART device and the UART object and returns the
        bytes object to queue. Returning an empty bytes object will cause nothing to be queued.

        :param data: The data being written to the UART device.
        :param uart: The UART device being used
        :returns: The bytes object to queue to the read buffer.
        """
        raise NotImplementedError


class MappingResponseStrategy(UARTResponseStrategy):
    """UART write response strategy for mapping-based configurations.

    Accepts mappings as a dictionary of "data written to device" to "response to queue to read
    buffer" like `{"A": "Resp-A"}`, so when `UART.write()` is called this strategy will return
    the value associated with the data written in the mapping dictionary, or queue the written
    data if no mapping exists.

    If this strategy is in "strict_mode" (`_is_strict` set to true) then when no mapping exists
    for written data then it will raise an exception.

    Due to the way the MicroPython internals work on board (and the fact that MicroPython lacks
    parsing of type hints or type checking) a user can pass a `str` to UART and have it work
    fine but for compatibility any mappings that are strings instead of bytes will be converted
    to bytes objects, this reflects our `UART` functionality where strings get converted to
    bytes before processing.

    TODO - could implement a lambda mapping type maybe
    """

    @staticmethod
    def encode_mappings_dict(mappings: dict[bytes | str, bytes | str]) -> dict[bytes, bytes]:
        """Helper method that takes in a mappings dictionary and converts each item to a bytes
        object if it isn't already, to normalize for later. Will raise a TypeError if an item
        is neither a bytes object or a string.

        :param mappings: The mappings to check and encode
        :returns: A dictionary where all items are bytes
        :raises TypeError: If mappings contains items that aren't bytes or a string.
        """
        # Initial check
        for key, val in mappings.items():
            if not isinstance(key, (str, bytes)) or not isinstance(val, (str, bytes)):
                raise TypeError(f"Invalid mapping type for key or value in entry [{key}:{val}")

        # Convert all to bytes
        return dict(
            (
                key.encode("utf-8") if isinstance(key, str) else key,
                val.encode("utf-8") if isinstance(val, str) else val,
            )
            for key, val in mappings.items()
        )

    def __init__(
        self, mappings: dict[bytes | str, bytes | str] | None = None, is_strict: bool = False
    ):
        """Initializes UARTResponseStrategy instance using mappings if provided.

        :param mappings: The response mappings, string entries get converted to bytes.
        :param is_strict: Whether this strategy should be strict and raise exception on unmapped
          data being written, instead of echoing back.
        :raises TypeError: If mappings contains items that aren't bytes or strings.
        """
        self._mappings: dict[bytes, bytes] = (
            self.encode_mappings_dict(mappings) if mappings else {}
        )
        self._is_strict = is_strict

    def get_response(self, data: bytes, uart: "UART") -> bytes:
        """Get the correct response from the mappings or echo back written data if no mapping.

        :raises KeyError: if `_is_strict` is true and no mapping exists for `data`.
        """
        if self._is_strict and data not in self._mappings:
            raise KeyError(f"No mapping exists for provided key: {data!r}")
        return self._mappings.get(data, data)

    def add_mapping(self, input_: str | bytes, response: str | bytes) -> None:
        """Add provided mapping to mappings dict. Converts strings to bytes."""
        b_input = input_.encode("utf-8") if isinstance(input_, str) else input_
        b_resp = response.encode("utf-8") if isinstance(response, str) else response
        self._mappings[b_input] = b_resp

    def set_mappings(self, mappings: dict[bytes | str, bytes | str]) -> None:
        """Set the response mappings to the provided dict, replacing original mappings.
        String entries are converted to bytes objects for compatibility."""
        self._mappings = self.encode_mappings_dict(mappings) if mappings else {}


class ListResponseStrategy(UARTResponseStrategy):
    """UART write response strategy for supporting list-based responses.

    Holds a list/ queue of responses like `["A", "B", "C", "D",]` and on each `UART.write()`
    the next item will be queued for response, with multiple options for handling list
    exhaustion. List act likes a FIFO queue.

    String response items will be internally converted to `bytes` before being added to the list,
    for compatibility and safety.

    Accepts 3 different options for controlling what to do when list is exhausted. These options
    are:

    * `"empty"` - respond with empty bytes (will make read return None, replicating timeout).
    * `"repeat_last"` - responds with last item in list whenever UART written to.
    * `"raise"` - raises an `IndexError` when attempting a UART write.
    """

    # TODO - could add some helper methods for this, like adding an item to the list and clearing

    def __init__(self, responses: list[str | bytes], on_exhausted: str = "empty"):
        """Initialize response strategy, see class docstring for more info.

        :param responses: the response list, string elements are converted to bytes.
        :param on_exhausted: "empty", "repeat_last" or "raise", see class docstring.
        """
        if on_exhausted not in ("empty", "repeat_last", "raise"):
            raise ValueError(f"Unknown on_exhausted option: {on_exhausted}")
        self._responses = [r.encode("utf-8") if isinstance(r, str) else r for r in responses]
        self._index = 0  # The index into the list
        self._on_exhausted = on_exhausted

    def get_response(self, data: bytes, uart: "UART") -> bytes:
        # List exhausted
        if self._index >= len(self._responses):
            if self._on_exhausted == "repeat_last" and self._responses:
                return self._responses[-1]
            if self._on_exhausted == "raise":
                raise IndexError("UART Response list exhausted")
            return b""

        response = self._responses[self._index]
        self._index += 1
        return response


class ConstantResponseStrategy(UARTResponseStrategy):
    """UART write response strategy for queueing the same bytes object as a response on each
    write."""

    def __init__(self, response: str | bytes):
        """Initialize strategy with single item."""
        self._response = response.encode("utf-8") if isinstance(response, str) else response

    def get_response(self, data: bytes, uart: "UART") -> bytes:
        return self._response


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
        response = self._callback(data, uart)
        if not isinstance(response, bytes):
            raise TypeError(f"Callback response {response} was not of type bytes")
        return response


class EchoResponseStrategy(UARTResponseStrategy):
    """Very basic UART response strategy that just echoes back whatever was written"""

    def get_response(self, data: bytes, uart: "UART") -> bytes:
        return data


class UART(io.IOBase):
    """Flexible test class mock for machine.UART.

    This class operates as a basic simulated fake object, when written to using `UART.write()` the
    object will use it's response strategy to decide what to append to the read buffer, which gets
    returned on `UART.read()` calls.

    This class allows to be put in a "strict mode" which will make the response strategies
    stricter in their processing.

    These are the existing `UARTResponseStrategy` classes (check the individual class
    docstrings for more info):

    * `MappingResponseStrategy`: for defining dictionary mappings of written data -> queued
      response. For example, ``{"A": "Resp-A", "B": "Resp-B"}`` will queue "Resp-A" when "A" is
      written to the UART device and "Resp-B" when "B" is written.
      Queues the written data if no mapping exists, throws in strict mode.
    * `ListResponseStrategy`: for defining a list of responses where each write will queue
      the next element to the read buffer.
      Has 3 different options for controlling operation when list is exhausted: "empty",
      "repeat_last", and "raise"
    * `ConstantResponseStrategy`: for queueing the same data to the read buffer each write.
    * `CallbackResponseStrategy`: for when you want more control over what to queue, will run a
      user defined callback which takes in the bytes being written and the UART object and should
      return the data to queue.
    * `EchoResponseStrategy`: simple example response strategy that just echoes back the data.

    See the ``docs/designs/uart.md`` file for more information on how the class operates and
    examples for how to use it.

    To create instances of this class for tests we recommend using the `UART.create_stub()`
    factory method as it has more flexibility around defining the response strategy without
    needing to instantiate the classes.

    Extends the io.IOBase abstract class to be able to used in stream operations.
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
    BUFFER_SIZE = const(512)  # Default bytes to allocate for the buffer (re-evaluate size later)
    DEFAULT_WRITE_BUF_SIZE = const(512)  # Default byte size for write buffer

    # Multiton lookup registry for UART instances
    _UART_REGISTRY: dict[int, "UART"] = {}

    def __new__(
        cls,
        uid,
        ignore_registry: bool = False,
        **kwargs,
    ):
        """Override of instance creation, used to return existing instance if uid matches an
        item in the `_UART_REGISTRY`.

        :param ignore_registry: If True then creates a new instance, even if one with the same
          id exists in the registry.
        """
        if uid in cls._UART_REGISTRY and not ignore_registry:
            # print("Using singleton UART")
            return cls._UART_REGISTRY[uid]

        # Create new instance
        uart = super().__new__(cls)
        return uart

    def __init__(
        self,
        uid,
        baudrate: int = 9600,
        bits: int = 8,
        parity: int | None = None,
        stop: int = 1,
        tx: machine.Pin | None = None,
        rx: machine.Pin | None = None,
        txbuf: int = 256,
        rxbuf: int = 256,
        timeout: int = 0,
        timeout_char: int = 0,
        invert: int | None = None,
        flow: int | None = None,
        rts: machine.Pin | None = None,
        cts: machine.Pin | None = None,
        ignore_registry: bool = False,
        add_to_registry: bool = False,
        response_strategy: UARTResponseStrategy | None = None,
        **kwargs,
    ):
        """Initialises UART instance, guarded against re-initialisation from __new__ so buffers
        and stuff are only created once.

        Instead of using the constructor we recommend using the `UART.create_stub` factory,
        as it is more streamlined.
        """

        # Guard to prevent re-initialization of existing instance returned by __new__
        if getattr(self, "_initialized", False):
            return

        super().__init__()  # init iobase stuff

        # Special attributes
        self.id_ = uid
        self._read_buf: bytearray = bytearray(0)
        self._response_strategy: UARTResponseStrategy = (
            response_strategy or EchoResponseStrategy()  # Default to echo
        )
        self._write_buf = micropython.RingIO(UART.DEFAULT_WRITE_BUF_SIZE)

        # Regular attributes
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop = stop
        self.tx = tx
        self.rx = rx
        self.txbuf = txbuf
        self.rxbuf = rxbuf
        self.timeout = timeout
        self.timeout_char = timeout_char
        self.invert = invert
        self.flow = flow
        self.rts = rts
        self.cts = cts

        # Add to registry
        self._in_registry = add_to_registry
        if add_to_registry:
            self._UART_REGISTRY[uid] = self

        self._initialized = True

    @staticmethod
    def create_stub(
        uid,
        is_strict: bool = False,
        mappings: dict[bytes | str, bytes | str] | None = None,
        response_list: list[bytes | str] | None = None,
        list_exhausted_behaviour: Literal["empty", "repeat_last", "raise"] | None = None,
        constant_response: str | bytes | None = None,
        response_callback: Callable[[bytes, "UART"], bytes] | None = None,
        custom_response: UARTResponseStrategy | None = None,
        initial_buffer_contents: bytes = b"",
        replace_existing: bool = True,
    ) -> "UART":
        """Factory for creating a UART test object with programmed response behaviour.
        Alternative to manually constructing both the UART and response strategy. See `UART` class
        docstring for more information about the response strategies and their behaviour.

        Will raise an exception if multiple response strategy items are provided. If none are
        provided then it will default to using the `EchoResponseStrategy`.

        Also adds the created instance to the `_UART_REGISTRY` dictionary so code under test
        will use it.

        :param uid: The id for this UART device.
        :param is_strict: makes the response strategy more strict (if supported). Currently, will
          make mapping responses raise if unmapped data is written and will default the list
          exhausted behaviour of `ListResponseStrategy` to "raise" if no behaviour was specified.
        :param mappings: The mappings for the `MappingResponseStrategy`, what you'd normally pass
          to `set_mappings`. Maps written data to the response to queue to the read buffer.
        :param response_list: The response list for the `ListResponseStrategy`, each UART write
          will queue the next list item.
        :param list_exhausted_behaviour: Controls the behaviour of the `ListResponseStrategy` when
          it runs out of responses. Accepts "empty", "repeat_last" and "raise".
          Defaults to "empty" (unless is_strict).
        :param constant_response: Defines the single value for `ConstantResponseStrategy` to use.
        :param response_callback: Callback of form ``Callable[[bytes, "UART"], bytes]`` for
          `CallbackResponseStrategy` to use.
        :param custom_response: A subclass of `UARTResponseStrategy`, for custom strategies.
        :param initial_buffer_contents: The initial contents to fill the `read_buf` with.
        :param replace_existing: If true (the default) and a `UART` instance exists with the same
          ID in the registry it will be replaced with the newly created one.
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

        uart = UART(uid, ignore_registry=replace_existing, add_to_registry=True)

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

        if initial_buffer_contents:
            uart.push_response(initial_buffer_contents)
        return uart

    @staticmethod
    def clear_registry():
        """Clears the `_UART_REGISTRY`"""
        UART._UART_REGISTRY.clear()

    def init(
        self,
        baudrate: int | None = None,
        bits: int | None = None,
        parity: int | None = None,
        stop: int | None = None,
        tx: machine.Pin | None = None,
        rx: machine.Pin | None = None,
        txbuf: int | None = None,
        rxbuf: int | None = None,
        timeout: int | None = None,
        timeout_char: int | None = None,
        invert: int | None = None,
        flow: int | None = None,
        rts: machine.Pin | None = None,
        cts: machine.Pin | None = None,
    ):
        """Reinitialize the set UART attributes. Performed by user code.

        TODO: probably handle resetting on invalid here, currently ignoring 0's for baudrate,
        bits, parity, and stop. As these would normally cause an error on 0 which would reset
        the attributes to defaults.
        """
        # Instance attributes
        self.baudrate = baudrate or self.baudrate
        self.bits = bits or self.bits
        self.parity = parity or self.parity
        self.stop = stop or self.stop
        self.tx = tx or self.tx
        self.rx = rx or self.rx
        self.txbuf = txbuf or self.txbuf
        self.rxbuf = rxbuf or self.rxbuf
        self.timeout = timeout if timeout is not None else self.timeout
        self.timeout_char = timeout_char if timeout_char is not None else self.timeout_char
        self.invert = invert if invert is not None else self.invert
        self.flow = flow if flow is not None else self.flow
        self.rts = rts or self.rts
        self.cts = cts or self.cts

    def deinit(self):
        """deinit, currently just removes device from registry if added"""
        if self._in_registry and self.id_ in self._UART_REGISTRY:
            del self._UART_REGISTRY[self.id_]

    def any(self):
        """Return integer for number of characters that can be read without blocking."""
        return len(self._read_buf)

    def read(self, nbytes=None) -> bytes | None:
        """Read from buffer, consuming bytes read and returning them.

        Default stub behaviour will just read from internal buffer.
        Return None if buffer is empty, simulating timeout.

        Delegates to `readinto` to simplify logic.
        """

        if not self._read_buf:
            return None

        nbytes = nbytes if nbytes is not None else len(self._read_buf)
        buf = bytearray(nbytes)
        bytes_read = self.readinto(buf, nbytes)
        return bytes(buf[:bytes_read])

    def readinto(self, buf: bytearray, nbytes=None) -> int | None:
        """Read bytes into buf. Returns num bytes stored or None on timeout."""

        if not self._read_buf:
            return None

        max_bytes = min(nbytes or len(buf), len(buf), len(self._read_buf))
        buf[0:max_bytes] = self._read_buf[:max_bytes]  # Check if inclusive
        self._read_buf = self._read_buf[max_bytes:]
        return max_bytes

    def readline(self, size: int | None = None) -> bytes | None:
        """Read line and return the read line as a bytes object, or None on timeout (no data).
        If there is no newline in data then whole buffer will be read."""

        if self.any() == 0:  # Return none if no data
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
        (so typically just the size of `buf`).

        Will use the `UART._response_strategy` to decide how to respond, the return value of
        `UARTResponseStrategy.get_response()` will be appended to the `_read_buf` to be read on
        the next `UART.read()` call.

        The default response strategy is to echo back written data, see `UART.create_stub()`
        for more response options.

        Also copies the contents of `buf` into the `_write_buf` for inspection in tests.

        :param buf: The data to write to the UART "device",

        TODO - could add a control for whether subsequent write calls will append _read_buf data
        or replace it (because a UART device might not buffer data like that)
        """

        # For safety and compatibility if a user passes in a string then we convert to bytes
        # Just to keep all internal processing using bytes objects.
        # If a non string/bytes/bytearray object is passed just encode the string representation
        byte_buf = bytes(buf) if isinstance(buf, (bytearray, bytes)) else str(buf).encode("utf-8")

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

        print(
            f"DEBUG: uart ioctl called with op {op}, arg {arg}"
        )  # NOTE - for testing, remove later

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
        """Send break condition, not sure if this will do anything"""
        pass

    def flush(self):
        """Wait until all data has been sent. Also probs do nothing here"""
        pass

    def txdone(self):
        """Returns whether data currently being sent or data transfer is currently occuring.

        Mocked version currently just returns true as we don't simulate the individual data
        sending.
        """
        return True

    def irq(self, handler=None, trigger=0, hard=False):
        """Configure interrupt handler to be called when UART event occurs.
        Returns IRQ object (TODO - do later, idk where the irq object is)

        TODO - figure out how we'll be handling IRQ's later
        """
        return None

    def __repr__(self):
        """Returns a tuple-like representation of the UART and its items.

        Example default output from ESP32:
        ``UART(1, baudrate=115201, bits=8, parity=None, stop=1, tx=10, rx=9, rts=-1, cts=-1,
        txbuf=256, rxbuf=256, timeout=0, timeout_char=0, irq=0)``

        "invert" and "flow" only get printed if set.
        """
        tx_str = self.tx or -1
        rx_str = self.rx or -1
        rts_str = self.rts or -1
        cts_str = self.cts or -1

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

    # Stub util methods

    def register_device(self) -> None:
        "Adds device to the uart registry, same as `add_to_registry` init argument"
        self._UART_REGISTRY[self.id_] = self

    def push_response(self, buf: bytes):
        """Queue bytes onto the read buffer, appending to the end"""
        self._read_buf += bytearray(buf)

    def get_written_data(self) -> bytes:
        """Return bytes written to the UART device by reading `_write_buf`"""
        return self._write_buf.read()

    # Util methods for controlling response strategy

    def set_mappings(self, mappings: dict[bytes | str, bytes | str]) -> None:
        """Set the write input to read output mappings, replaces existing mappings.

        If the response_strategy is not currently `MappingResponseStrategy` then a new instance
        will be created and given your mappings.

        Any mappings that are strings will be converted to `bytes` objects before storing, for more
        information see the docs for `MappingResponseStrategy`.

        TODO - check later whether changing the response strategy is fine or if should just raise.
        """
        if isinstance(self._response_strategy, MappingResponseStrategy):
            self._response_strategy.set_mappings(mappings)
        else:
            self._response_strategy = MappingResponseStrategy(mappings)

    def add_mapping(self, input_: bytes | str, response: bytes | str) -> None:
        """Add a new mapping response entry, raises TypeError if response strategy is not
        `MappingResponseStrategy`

        :raises TypeError: If the response strategy is not currently `MappingResponseStrategy`
        """
        if not isinstance(self._response_strategy, MappingResponseStrategy):
            raise TypeError(
                "UART.add_mapping() requires response strategy to be MappingResponseStrategy"
            )

        self._response_strategy.add_mapping(input_, response)

    @property
    def response_strategy(self) -> UARTResponseStrategy:
        """Get the current response strategy"""
        return self._response_strategy

    @response_strategy.setter
    def response_strategy(self, strategy: UARTResponseStrategy):
        self._response_strategy = strategy
