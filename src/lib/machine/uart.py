"""uart.py

MicroPython file for the UART stubs and mocks, classes are reexported
in main machine module __init__

"""

from micropython import const
import machine


class UART:
    """Basic fake UART stub class.

    Stubs existing constants and methods, supplies utilities for basic
    stubs and can be extended to implement more complex fakes.

    """

    # Module-specific constants
    RTS = const(0x1)
    CTS = const(0x2)
    IRQ_RXIDLE = const(0x1000)
    IRQ_RX = const(1 << 0)  # In the IDF files, first item of enum
    IRQ_BREAK = const(1 << 1)

    # Custom constants
    BUFFER_SIZE = const(512)  # Default bytes to allocate for the buffer (re-evaluate size later)

    # Multiton lookup registry for UART instances
    _UART_REGISTRY: dict[int, "UART"] = {}

    # Instance level attribute typehints, needed for type checkers to behave
    id_: int  # TODO - technically not an int but works for now
    _read_buf: bytearray
    _in_registry: bool
    _write_mappings: dict[bytes, bytes]

    def __new__(
        cls,
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
        """Override of instance creation, used to return existing instance if uid matches an
        item in the `_UART_REGISTRY`.

        Performs initialization logic here as returned object implicitly receives an __init__
        call.

        :param ignore_registry: If True then creates a new instance, even if one with the same
          id exists in the registry.
        :param add_to_registry: If True then adds the created instance to the registry.
        """
        if uid in cls._UART_REGISTRY and not ignore_registry:
            print("Using singleton UART")
            return cls._UART_REGISTRY[uid]

        # Create new instance
        uart = super().__new__(cls)
        uart.id_ = uid
        uart._read_buf = bytearray(0)
        uart._write_mappings = {}

        # The regular attribute initialization
        uart.baudrate = baudrate
        uart.bits = bits
        uart.parity = parity
        uart.stop = stop
        uart.tx = tx
        uart.rx = rx
        uart.txbuf = txbuf
        uart.rxbuf = rxbuf
        uart.timeout = timeout
        uart.timeout_char = timeout_char
        uart.invert = invert

        uart._in_registry = add_to_registry
        if add_to_registry:
            cls._UART_REGISTRY[uid] = uart

        return uart

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

    def __init__(self, uid, *args, **kwargs):
        """Unused, __init__ logic performed in __new__"""
        pass

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


        NOTE - This can fail with a timeout which might need simulating, returns None
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

    def readline(self) -> bytes | None:
        """Read line and return the read line as a bytes object, or None on timeout"""

        if b"\n" not in self._read_buf:
            return None

        index = self._read_buf.find(b"\n") + 1  # Include newline
        buf = bytearray(index)
        self.readinto(buf, nbytes=index)
        return bytes(buf)

    def write(self, buf) -> int:
        """Write buffer contents to device and return length written.

        Default stub behaviour just puts buffer contents into the read buffer.
        If a mapping for the provided input is set then will write the
        corresponding output to the read buffer.
        """
        byte_buf = bytes(buf, "utf-8")  # To be safe convert it to bytes
        response = self._write_mappings.get(
            byte_buf, byte_buf
        )  # If not found we just write input
        self._read_buf += response
        return len(response)

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

    @staticmethod
    def create_mock(uid, replace_existing: bool = True, assert_reads: bool = False) -> "UARTMock":
        """Create an instance of the `UARTMock` class.
        Put this in the UART class to make it easier to access but may move later.

        :param uid: The id for the UART device.
        :param replace_existing: Whether to replace an existing UART device with the same id in
        the registry.
        :param assert_reads: Whether or not to assert read expectations, false by default for now
        as not fully implemented.
        """
        mock = UARTMock(uid, ignore_registry=replace_existing, add_to_registry=True)
        mock.assert_reads = assert_reads
        return mock


class UARTMock(UART):
    """Mockable version of `UART`, provides methods for asserting expected inputs and setting
    outputs.

    Maintains a list of ordered registered expectations for write and read operations.
    Write expectations specify the expected input `bytes` for the call and the bytes to
    queue in the read buffer.
    Read expectations specify the expected number of bytes to be read.

    When user code calls functions `write` or `read` it will check if the next expectation is for
    the relevant function and that the inputs/ output match, if they do then they'll return the
    expectation, otherwise they'll raise an exception.

    Read expectations can be disabled.

    TODO - add support for the other methods
    TODO - maybe switch to using a namedtuple or dataclass over dict entries for expectations
    TODO - maybe switch to a custom exception type instead of assertions
    """

    def __init__(self, uid, assert_reads=True, **extra_args):
        """Create a new UARTMock object.

        :param assert_reads: controls whether mock checks for read expectations
        """
        super().__init__(uid, **extra_args)
        self.assert_reads = assert_reads
        self._expectations: list[dict] = []  # List of expectations

    def write(self, buf: bytes) -> int:
        """Assert expected method call with input and add expected response to read buffer."""
        b_buf = bytes(buf, "utf-8") if not isinstance(buf, bytes) else buf
        assert self._expectations, "UARTMock.write called when no expectations remain"

        expectation = self._expectations.pop(0)
        assert (
            expectation["method"] == "write"
        ), f"UARTMock.write called when next expectation is {expectation['method']}"
        assert (
            expectation["expected_in"] == b_buf
        ), f"UARTMock.write called with {b_buf!r} instead of {expectation['expected_in']!r}"
        resp = expectation["response"]
        self._read_buf += resp
        return len(resp)

    def readinto(self, buf: bytearray, nbytes=None) -> int | None:
        """Assert expected read call (if enabled) with expected number of bytes read

        Using this as the main overridden read as the others call readinto implicitly.
        """
        byte_count = super().readinto(buf, nbytes)

        if self.assert_reads:
            assert self._expectations, "UARTMock.read called when no expectations remain"
            expectation = self._expectations.pop(0)
            assert (
                expectation["method"] == "read"
            ), f"UARTMock read called when next expectation is {expectation['method']}"
            exp_bytes = expectation["expected_bytes"]
            assert (
                expectation["expected_bytes"] == byte_count
            ), f"UARTMock read received {byte_count} bytes, expected {exp_bytes}"
        return byte_count

    def expect_write_then_queue(self, expect_in: bytes, response: bytes) -> None:
        """Add an expected write with `expect_in` to queue `response`"""
        self._expectations.append(
            {
                "method": "write",
                "expected_in": expect_in,
                "response": response,
            }
        )

    def expect_read(self, expected_bytes) -> None:
        """Add an expected read which should read `expected_bytes`"""
        self._expectations.append(
            {
                "method": "read",
                "expected_bytes": expected_bytes,
            }
        )

    def clear_expectations(self) -> None:
        """Clear expectations list"""
        self._expectations = []

    def validate(self) -> None:
        """Validate that all expectations ran"""
        assert (
            not self._expectations
        ), f"UARTMock validation called when {len(self._expectations)} expectations still remain"
