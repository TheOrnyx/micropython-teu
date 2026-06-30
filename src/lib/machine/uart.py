"""uart.py

MicroPython file for the UART test objects, classes are reexported in main machine module __init__
"""

import io
import micropython
from micropython import const
import machine


class UART(io.IOBase):
    """Basic fake UART stub class.

    Stubs existing constants and methods, supplies utilities for basic
    stubs and can be extended to implement more complex fakes.

    Extends the io.IOBase abstract class to be able to used in stream operations.
    Is also iterable.

    TODO - see about whether the other iobase methods like seek need to be properly implemented
           for stream ops, see https://docs.micropython.org/en/latest/library/io.html#io.IOBase
    """

    # Module-specific constants
    RTS = const(0x1)
    CTS = const(0x2)
    IRQ_RXIDLE = const(0x1000)
    IRQ_RX = const(1 << 0)  # In the IDF files, first item of enum
    IRQ_BREAK = const(1 << 1)

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
        txbuf: int | None = None,
        rxbuf: int | None = None,
        timeout: int | None = None,
        timeout_char: int | None = None,
        invert: int | None = None,
        ignore_registry: bool = False,
        add_to_registry: bool = False,
        **kwargs,
    ):
        """Initializes UART instance, guarded against re-initialization so buffers and stuff
        are only created once.
        """

        # Guard to prevent re-initialization of existing instance returned by __new__
        if getattr(self, "_initialized", False):
            return

        super().__init__()  # init iobase stuff

        # Special attributes
        self.id_ = uid
        self._read_buf: bytearray = bytearray(0)
        self._write_mappings: dict[bytes, bytes] = {}
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

        # Add to registry
        self._in_registry = add_to_registry
        if add_to_registry:
            self._UART_REGISTRY[uid] = self

        self._initialized = True

    @staticmethod
    def create_stub(
        uid,
        mappings: dict | None = None,
        initial_buffer_contents: bytes = b"",
        replace_existing: bool = True,
    ) -> "UART":
        """Basic factory for creating a UART stub. Alternative to manually constructing. Also
        adds the created instance to the `_UART_REGISTRY` dictionary so code under test will
        use it.

        :param uid: The id for this UART device.
        :param mappings: The mappings for write responses, what you'd normally pass to
          `set_mappings`.
        :param initial_buffer_contents: The initial contents to fill the `read_buf` with.
        :param replace_existing: If true (the default) and a `UART` instance exists with the same
          ID in the registry it will be replaced with the newly created one.
        """
        uart = UART(uid, ignore_registry=replace_existing, add_to_registry=True)
        if mappings:
            uart.set_mappings(mappings)
        if initial_buffer_contents:
            uart.push_response(initial_buffer_contents)
        return uart

    @staticmethod
    def clear_registry():
        """Clears the `_UART_REGISTRY`"""
        UART._UART_REGISTRY.clear()

    def init(
        self,
        baudrate: int = 9600,
        bits: int = 8,
        parity: int | None = None,
        stop: int = 1,
        tx: machine.Pin | None = None,
        rx: machine.Pin | None = None,
        txbuf: int | None = None,
        rxbuf: int | None = None,
        timeout: int | None = None,
        timeout_char: int | None = None,
        invert: int | None = None,
    ):
        """Reinitialize the UART attributes. Likely performed by user code"""
        # Instance attributes
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

        Delegates to `readinto` to simplify mocking logic.
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
        """Write buffer contents to device and return the number of bytes written to the
         "device", (so the size of buf).

        Default stub behaviour just puts buffer contents into the read buffer.
        If a mapping for the provided input is set then will write the
        corresponding output to the read buffer.

        Will also copy the buf data into the `_write_buf` for inspection in tests.
        """

        # Extra safety against failure using different conversions.
        # Sometimes buf is bytes, sometimes bytearray, sometimes even string...
        byte_buf = (
            buf.encode("utf-8")
            if isinstance(buf, str)
            else bytes(buf) if isinstance(buf, bytearray) else buf
        )

        response = self._write_mappings.get(
            byte_buf, byte_buf
        )  # If not found we just write input
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

        TODO - Might allow mappings or a callback for the operations here but not sure how
               important they are, but need to test stream operations to see if they use this.
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
        """Returns whether data currently being sent or data transfer occuring

        Probs do nothing here too
        """
        return True

    def irq(self, handler=None, trigger=0, hard=False):
        """Configure interrupt handler to be called when UART event occurs.
        Returns IRQ object (TODO - do later, idk where the irq object is)

        TODO - figure out how we'll be handling IRQ's later
        """
        return None

    # Stub util methods

    def set_mappings(self, mappings: dict[bytes, bytes]) -> None:
        """Set the write input to read output mappings

        TODO - maybe add more complex mapping support later
        """
        self._write_mappings = mappings

    def add_mapping(self, input_: bytes, response: bytes) -> None:
        "Adds the provided mapping without removing other mappings"
        self._write_mappings[input_] = response

    def register_device(self) -> None:
        "Adds device to the uart registry, same as `add_to_registry` init argument"
        self._UART_REGISTRY[self.id_] = self

    def push_response(self, buf: bytes):
        """Queue bytes onto the read buffer, appending to the end"""
        self._read_buf += bytearray(buf)

    def get_written_data(self) -> bytes:
        """Return bytes written to the UART device by reading `_write_buf`"""
        return self._write_buf.read()
