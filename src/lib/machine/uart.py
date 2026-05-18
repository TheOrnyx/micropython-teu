"""uart.py

MicroPython file for the UART stubs and mocks, classes are reexported
in main machine module __init__

"""

# NOTE - Should this file maybe be called like mock_uart.py or smth

from micropython import const
import machine
from .pin import Pin


# Basic UART stub class
class UART:
    """Basic UART mock class.  Stubs existing constants and methods and supplies
    methods and attributes for mocking.

    TODO - implement a custom type for the UART devices output_buffer, as likely
    a few communication devices will use it
    TODO - implement more mock operations
    """

    # Module-specific constants
    RTS = const(0x1)
    CTS = const(0x2)
    IRQ_RXIDLE = const(0x1000)
    IRQ_RX = const(1 << 0)  # In the IDF files, first item of enum
    # NOTE - IRQ_TXIDLE doesn't exist on ESP32
    IRQ_BREAK = const(1 << 1)  # TODO - check, using ordinal enum again

    # Custom constants
    BUFFER_SIZE = const(512)  # Default bytes to allocate for the buffer (re-evaluate size later)

    # Basic singleton lookup table for proof-of-concept (TODO - improve later)
    _UART_LOOKUP: dict[int, "UART"] = {}

    def __new__(cls, uid, *args, **kwargs):
        """Override of instance creation, used to return singleton"""
        if uid in cls._UART_LOOKUP:
            print("singleton found :3")
            return cls._UART_LOOKUP[uid]
        return super().__new__(cls)

    def __init__(
        self,
        uid,  # Custom mp type ID_T (means int | str)
        baudrate: int = 9600,
        bits: int = 8,
        parity: int | None = None,
        stop: int = 1,
        tx: Pin | None = None,
        rx: Pin | None = None,
        txbuf: int | None = None,
        rxbuf: int | None = None,
        timeout: int | None = None,
        timeout_char: int | None = None,
        invert: int | None = None,
        add_to_lookup: bool = False,
    ):
        """Creates UART object with given ID and initialize it.

        :param add_to_lookup: Decides whether or not this UART instance will be
            added to the :attr:`_UART_LOOKUP` table as a singleton for this id
        """
        if getattr(self, "_is_singleton_instance", False):
            return  # Maybe call regular init here

        self._id = uid
        # buf_size = rxbuf or self.BUFFER_SIZE
        self._read_buf = bytearray(0)
        self._callbacks: dict[str, machine.Callable] = {}  # type: ignore[name-defined]

        if add_to_lookup:
            self._UART_LOOKUP[uid] = self
            self._is_singleton_instance = add_to_lookup
            self.init(
                baudrate, bits, parity, stop, tx, rx, txbuf, rxbuf, timeout, timeout_char, invert
            )

    def init(
        self,
        baudrate: int = 9600,
        bits: int = 8,
        parity: int | None = None,
        stop: int = 1,
        tx: Pin | None = None,
        rx: Pin | None = None,
        txbuf: int | None = None,
        rxbuf: int | None = None,
        timeout: int | None = None,
        timeout_char: int | None = None,
        invert: int | None = None,
    ):
        """Initialize the UART, not sure what this needs to do for stub"""
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
        """deinit, might need to disable smth"""
        pass

    def any(self):
        """Return integer for number of characters that can be read without blocking.

        If a callback is registered for the 'any' event then that will be used,
        otherwise return length of the current read buffer.
        """
        cb = self._callbacks.get("any")
        if cb:
            return cb()
        return len(self._read_buf)

    def read(self, nbytes=None) -> bytes | None:
        """Read from buffer, consuming bytes read and returning them.

        If a callback is registered for the 'read' event then delegate to that,
        otherwise consume from the read buffer.
        Return None if buffer is empty, simulating timeout

        TODO - change this once properly implementing output buffer
        NOTE - This can fail with a timeout which might need simulating, returns None
        """

        cb = self._callbacks.get("read")
        if cb:
            return cb(nbytes)

        if not self._read_buf:
            # Could put timeout stuff later here if needed
            return None

        if nbytes is None:
            data = bytes(self._read_buf)
            self._read_buf = bytearray(0)
            return data

        data = bytes(self._read_buf[:nbytes])
        self._read_buf = self._read_buf[nbytes:]
        return data

    def readinto(self, buf: bytearray, nbytes=None):
        """Read bytes into buf. Returns num bytes stored or None on timeout.

        TODO - once again, make this use the output buffer
        """

        read_bytes = bytes(self._read_buf)
        max_bytes = min(nbytes or len(buf), len(buf), len(read_bytes))
        buf[0:max_bytes] = read_bytes
        return max_bytes

    def readline(self) -> bytes | None:
        """Read line and return the read line as a bytes object, or None on timeout

        TODO - redo with the proper buffer type
        TODO - find out if the returned string includes the newline char
        """

        if b"\n" in self._read_buf:
            index = self._read_buf.find(b"\n")
            line = bytes(self._read_buf[0:index])
            self._read_buf = self._read_buf[index + 1 :]
            return line
        return None

    def write(self, buf):
        """Write to the output buffer by calling the ``write`` event callback
        and appending the response to the read buffer.

        Returns the length of supplied buffer.
        """
        cb = self._callbacks.get("write")
        if cb:
            byte_buf = bytes(buf, "utf-8")  # Input can be string, convert to be safe
            resp = cb(byte_buf)
            if resp:
                self._read_buf += bytearray(resp)
            return len(byte_buf)
        return len(buf)

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

    def set_event_callback(self, event, fn):
        """Set a callback for a specific event to control operation without
        needing to define an entire class.

        Supported events are:
        - ``'write'`` -- ``fn(buf: bytes) -> bytes``
          Called on ``write()``; return result stored in ``_read_buf``.
          It's also worth nothing that some user code will pass a string into
          this function so it's safer to make sure the buf gets converted to a bytes obj
          (TODO - maybe add a control for how this gets added to the buf)

        - ``'read'`` -- ``fn(nbytes: int|None) -> bytes``
          Called on ``read()``; uses fn return val rather than ``_read_buf``

        - ``'any'`` -- ``fn() -> int``
          Called on ``any()``; overrides checking based on buffer
        """
        self._callbacks[event] = fn

    def clear_event_callback(self, event):
        """Clear the callback for a specific event.
        See :meth:`set_event_callback` for event types
        """
        del self._callbacks[event]

    def clear_all_callbacks(self):
        """Clears all event callbacks"""
        self._callbacks.clear()

    def push_response(self, buf: bytes):
        """Queue bytes onto the read buffer, appending to the end"""
        self._read_buf += bytearray(buf)
