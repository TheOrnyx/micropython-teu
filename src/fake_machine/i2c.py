"""
i2c.py

Module that provides the custom I2C test fake classes, reexported in fake_machine
"""

import errno
from micropython import const
from .utils import buffer_to_bytes
from .pin import Pin

TYPE_CHECKING = False
if TYPE_CHECKING:
    # Needed for linting tools
    from typing import Callable  # pylint: disable=unused-import

_MIN_ADDR = const(0x08)  # Minimum address value (inclusive)
_MAX_ADDR = const(0x77)  # Maximum address value (inclusive)


class I2CDevice:
    """Configurable utility class for use with the ``fake_machine.I2C`` class. Represents a
    device on an I2C bus at a specific address and is the main class to use when testing I2C
    device driver logic.

    The device can be written to and read from using the same methods present on the I2C bus,
    responses to these will be configurable by the test author using utility methods.

    Both register-based I2C devices and the less-common non-register-based devices are supported:

    Register data is stored as a dictionary of the register address to the data contained in
    the register as a ``bytes`` object. This means reading can occur either randomly or
    sequentially by reading nbytes from a register. Register data can be set with
    ``.set_single_reg()`` for single registers of varying size, and ``.set_reg_block()`` for a
    range of 1=byte registers using a single input.

    Data that is read for a non-register device (using ``.readfrom()`` rather than
    ``.readfrom_mem()``) will use a basic `read_response` bytes response which can be set with
    ``.set_read_response()``.

    Most of the read and write operations for this device currently raise a ``ValueError`` when
    attempting to read or write more bytes than available, even though some devices would allow
    these operations by doing things like wrapping. Despite this not being

    TODO - decide how to better handle reads and writes larger than available data,
    some devices do stuff like wrapping but considering it better to raise for tests. Maybe
    just add a basic ``raise_on_range_limits`` attribute or something in future.

    TODO - allow regular read operations to act as memory reads with a configuration setting.

    TODO - maybe allow using strings in input since might be buffer objects.

    TODO - document subclassing this, what methods to override.
    """

    def __init__(self, addr: int, i2c_bus: "I2C", add_to_bus=True) -> None:
        """Initialize a new ``I2CDevice`` with a specific address and register it with the
        provided i2c_bus.

        :param addr: The devices address between ``0x08`` and ``0x77`` inclusive, used by the bus
          to address this device.
        :param i2c_bus: The ``I2C`` bus that this device belongs to.
        :param add_to_bus: Add this device to the i2c_bus if True, useful if you want to
          separate instantiation and registration.
        :raises ValueError: If addr out of range.

        TODO - add read_response and maybe reg block to the constructor.
        """
        if addr not in range(_MIN_ADDR, _MAX_ADDR + 1):
            raise ValueError(f"Provided address {addr} not in range 0x08 <= addr <= 0x77")

        self.addr = addr
        self.i2c = i2c_bus

        # NOTE - could switch to OrderedDict if we need the order to remain
        self.registers: dict[int, bytearray] = {}  # The register dict
        self.read_response = bytearray()  # The response to use for regular writes
        self.mem_writes_overwrite_registers = False  # Whether writeto_mem can modify regs

        # Write callbacks, one for regular writeto(), one for register writeto_mem()
        self.write_cb: Callable[["I2CDevice", bytes], None] | None = None
        self.memwrite_cb: Callable[["I2CDevice", int, bytes], None] | None = None
        if add_to_bus:
            self.i2c.add_device(self)

    def readfrom_mem_into(self, memaddr, buf: bytearray, addrsize=8) -> None:
        """Read ``len(buf)`` bytes from the devices registers starting from `memaddr` into `buf`.

        Delegates to ``.get_reg_data()``.

        :param memaddr: The register address to start reading from.
        :param buf: The buffer to read into, length determines how many bytes to read.
        :param addrsize: The address size in bits, currently unused in fake.
        :raises KeyError: if `memaddr` isn't in the registers.
        :raises ValueError: if attempting to read more bytes than is sequentially in the register
          set.
        """
        read_data = self.get_reg_data(memaddr, len(buf))
        buf[:] = read_data

    def readfrom_mem(self, memaddr, nbytes, addrsize=8) -> bytes:
        """Read `nbytes` from this devices registers starting from `memaddr` and return as a
        ``bytes``.

        Delegates to ``.get_reg_data()``.
        """
        read_data = self.get_reg_data(memaddr, nbytes)
        return read_data

    def readfrom_into(self, buf, stop=True) -> None:
        """Read ``len(buf)`` bytes from this device into buf by reading from the
        `read_response` response data.

        Delegates to ``.get_read_data()``.

        :param buf: The buffer to read into. Number of bytes read will be length.
        :param stop: Normally causes STOP condition to be generated at end of transfer, ignoring
          here.
        :raises ValueError: If attempting to read more bytes than available in `read_response`.

        TODO - implement other ways to handle larger reads besides raising
        """
        data = self.get_read_data(len(buf))
        buf[:] = data

    def readfrom(self, nbytes, stop=True) -> bytes:
        """Read `nbytes` from this device, just reads `nbytes` from the `read_response`.

        Delegates to ``.get_read_data()``.

        :param nbytes: The number of bytes to read from the response.
        :raises ValueError: If attempting to read more bytes than available.
        """
        buf = self.get_read_data(nbytes)
        return buf

    def writeto(self, buf, stop=True) -> int:
        """Write data in `buf` to this device and return number of bytes written.

        Will run the write callback if set.
        """
        if self.write_cb is not None:
            self.write_cb(self, buf)

        return len(buf)

    def writeto_mem(self, memaddr, buf, addrsize=8) -> None:
        """Write data in `buf` to the registers starting at `memaddr`.

        This will run the `memwrite_cb` callback if set.

        The device can also be configured to have this overwrite the registers by calling
        ``.allow_register_writing()``, in which case the call will start from the register at
        `memaddr` and write `buf` data using ``._overwrite_reg_block()``.

        :raises KeyError: If overwriting register data and the reg at `memaddr` doesn't exist.
        :raises ValueError: If overwriting register data and the size of `buf` is larger than
          register block being written to, or not enough data to fully fill final register.

        TODO - maybe see about validating memaddr even if not overwriting, not doing currently
        for ease of testing but could be good to enforce to make tests more strict.
        """
        if self.mem_writes_overwrite_registers:
            self._overwrite_reg_block(memaddr, buf)

        if self.memwrite_cb is not None:
            self.memwrite_cb(self, memaddr, buf)

    def writevto(self, vector, stop=True) -> int:
        """Write the bytes for each item contained in `vector` to this device and return bytes
        written.

        On-board this seems to just be writing a list of buffer protocol objects so this
        function will turn the vector contents into one long buffer and call ``.writeto()``
        with that.

        :param vector: The list or tuple of buffer protocol items to write.
        """
        combined_buf = bytearray()
        for buf in vector:
            bytes_buf = buffer_to_bytes(buf)
            combined_buf += bytes_buf
        return self.writeto(combined_buf, stop)

    # --------- Test configuration utilities

    def get_reg_data(self, start_reg: int, nbytes: int) -> bytes:
        """Read this devices register data starting at register address `start_reg`.

        Starts from the register at address `start_reg` and reads each sequential register
        until `nbytes` have been read.

        :param start_reg: The address of the register to start reading data from.
        :param nbytes: The number of bytes of data to read from the register set starting from
          `start_reg`..
        :returns: The register data as a ``bytes`` object.
        :raises KeyError: If `start_reg` is not in the register set
        :raises ValueError: If `nbytes` is larger than the amount of sequential register data we
          can read.

        TODO - decide how we should deal with nbytes longer than register amount, some devices
        wrap. Currently will just raise as better for testing.
        """
        if start_reg not in self.registers:
            raise KeyError(
                f"Error: I2CDevice {self.addr:#04x} has no configured register at address "
                f"{start_reg:#04x}"
            )

        # Walk the registers and append their data till we've read nbytes or no next register
        read_data = bytearray()
        offset = 0
        # TODO - check if any devices can have non-continuous register addresses
        while start_reg + offset in self.registers and len(read_data) < nbytes:
            # TODO - maybe add a raise if can only read part of the register before hitting nbytes
            #  like in _overwrite_reg_block
            read_data += self.registers[start_reg + offset]
            offset += 1

        if len(read_data) < nbytes:  # Raise if out of registers and not read nbytes
            raise ValueError(
                f"Error: I2CDevice read requested {nbytes} but could only read {len(read_data)} "
                f"bytes. Please configure the full register block for this test."
            )

        result = self._pad_or_trim_buffer(read_data, nbytes, b"\xff")
        return bytes(result)

    def set_single_reg(
        self,
        reg_addr: int,
        data: int | bytes | bytearray,
        int_nbytes=1,
        endianness="big",
        signed=False,
    ) -> None:
        """Set the data for a single register at `reg_addr` which can be read back with a
        ``.readfrom_mem(reg_addr)``/ ``.readfrom_mem_into(reg_addr)`` call.

        Created register gets added to the `registers` dict with the key being the `reg_addr`
        and the value being the created ``bytearray``.

        The length of the register being set will be the length of `data` if it is a ``bytes``/
        ``bytearray``, so registers larger than 8-bits (like the ADS1115 ADC which has a 16-bit
        conversion register) can be supported.

        Alternatively, `data` can be passed as an ``int`` which will be converted to a
        ``bytes`` object of size `int_nbytes` with the provided `endianess` and `signed`. Just in
        case it helps with testing.

        :param reg_addr: The address of this register in the device.
        :param data: The data in the register to be read.
        :param int_nbytes: Used when `data` is an ``int`` to convert to a ``bytes`` object.
        :param endianness: Used when `data` is ``int`` to decide bytes conversion endianness.
        :raises ValueError: If `data` is an int and bytes conversion fails.

        TODO - maybe make int be separate method and rename this
        TODO - also could make endianess apply to the data written
        """
        reg_data = data
        if isinstance(data, int):  # Convert to bytes
            try:
                reg_data = data.to_bytes(int_nbytes, endianness, signed=signed)
            except OverflowError as e:
                raise ValueError(
                    f"Failed to convert data int value {data} to bytes object: {str(e)}"
                )
        self.registers[reg_addr] = bytearray(reg_data)

    def set_reg_block(self, start_addr: int, reg_data: bytes | bytearray) -> None:
        """Set a range of sequential 1-byte register values from a single buffer, starting at
        `start_addr`. One for each byte in `reg_data`.

        If `start_addr` was 0 and `reg_data` was ``b'\\x01\\x02\\x03'`` then the resulting
        register block would be ``{0: b'\\x01', 1: b'\\x02', 2: b'\\x03'}``. So when a
        ``I2C.readfrom_mem(dev_addr, 0, 3)`` occurs those 3 bytes will be read.

        Useful to set up a block of registers which can either be accessed sequentially or
        randomly without needing multiple declarations.

        If wanting to set a register block with varying sizes in one call use the
        ``.set_reg_list([...])`` method.

        :param start_addr: The memaddr to start defining the block of registers from.
        :param reg_data: a ``bytes``/``bytearray`` buffer containing the set of data to be
          assigned to the created registers. Number of registers created will be `
          `len(reg_data)``.
        """
        for i, b in enumerate(reg_data):
            # Have to use tuple otherwise gets interpreted as "x byte long buffer"
            self.registers[start_addr + i] = bytearray((b,))

    def set_reg_list(self, start_addr: int, reg_list: list | tuple) -> None:
        """Set a range of sequential varying-sized registers from a list, starting at
        `start_addr`. One register for each buffer in the `reg_list`.

        Useful for setting up multiple different sized registers at once instead of doing
        multiple calls to ``.set_single_reg()``.

        :param start_addr: The memaddr to start defining the block of registers from.
        :param reg_list: A list or tuple containing ``bytes``/``bytearray`` objects, a register
          will be made for each item in the list.
        """
        for i, data in enumerate(reg_list):
            self.registers[start_addr + i] = bytearray(data)

    def _overwrite_reg_block(self, start_addr: int, buf: bytes) -> None:
        """Overwrite the block of registers starting at `start_addr` by populating them with
        the data stored in `buf`.

        Currently, this implementation is a bit strict on writes. If the device runs out of
        bytes from `buf` while still writing to a register (imagine we're writing to a 2-byte
        register, but `buf` only has enough remaining bytes to fill the first byte) it will
        raise a ValueError.

        :param start_addr: The register memaddr to start writing to.
        :param buf: The data buffer to fill register contents with.
        :raises KeyError: If `start_addr` isn't a register that's been set.
        :raises ValueError: If length of `buf` is larger than the register block.
        :raises ValueError: If reach end of `buf` and final register is only partly filled, `buf`
          data should be enough to fill any walked registers entirely.
        """
        if start_addr not in self.registers:
            raise KeyError(
                f"Error: I2CDevice {self.addr:#04x} has no configured register at address "
                f"{start_addr:#04x}"
            )

        offset = 0
        bytes_written = 0
        while start_addr + offset in self.registers and bytes_written < len(buf):
            reg = self.registers[start_addr + offset]  # Same object in memory
            if bytes_written + len(reg) > len(buf):  # Not enough of buf to fill whole register
                raise ValueError(
                    "Error: buffer provided to I2CDevice register overwrite only has enough "
                    "data to partially fill final register."
                )
            reg[: len(reg)] = buf[bytes_written : bytes_written + len(reg)]
            offset += 1
            bytes_written += len(reg)

        if bytes_written < len(buf):  # Raise if not enough registers to fill with buf data
            raise ValueError(
                f"Error: I2CDevice only had enough registers in block to write {bytes_written} "
                f"bytes, but buf contains {len(buf)} bytes"
            )

    def get_read_data(self, nbytes: int) -> bytes:
        """Read `nbytes` from the regular non-register `read_response` read data and return as
        ``bytes``.

        :param nbytes: The number of bytes to read from `read_response`.
        :raises ValueError: If trying to read more bytes than `read_response` contains.

        TODO - see about better handling of larger reads than raising.
        """
        if nbytes > len(self.read_response):
            raise ValueError(
                f"Error: attempted to read {nbytes} bytes from I2CDevice when read_response "
                f"only contains {len(self.read_response)} bytes."
            )
        response = bytes(self.read_response[:nbytes])
        return response

    def set_read_response(self, contents: bytes | bytearray) -> None:
        """Set the response data to be stored in the `read_response`, which will be read in
        non-register based read calls to ``.readfrom()``/ ``.readfrom_into()``.

        :param contents: A bytes or bytearray object containing the new read response data.
        """
        self.read_response = bytearray(contents)

    def set_write_callbacks(
        self,
        write_cb: Callable[["I2CDevice", bytes], None] | None = None,
        memwrite_cb: Callable[["I2CDevice", int, bytes], None] | None = None,
    ) -> None:
        """Set the custom callbacks that run when a write operation on this device occurs.
        There are two callbacks: `write_cb` for regular ``.writeto()`` calls, and `memwrite_cb`
        for memory ``.writeto_mem()`` calls.

        The callable takes in the I2CDevice being written to, and the data being written. The
        memory write callback takes in the `memaddr` too. Useful for tests where a device needs
        to change its responses on write.

        To remove the callbacks use the ``.reset_write_callbacks()`` method.

        :param write_cb: Callable in form ``Callable[[I2CDevice, bytes], None]``
        :param memwrite_cb: Callable in form ``Callable[["I2CDevice", int, bytes], None]``
        """
        self.write_cb = write_cb if write_cb is not None else self.write_cb
        self.memwrite_cb = memwrite_cb if memwrite_cb is not None else self.memwrite_cb

    def reset_write_callbacks(self) -> None:
        """Reset both the write callbacks so they will no longer be called on writes.

        Shouldn't be needed too often but might be useful.
        """
        self.write_cb = None
        self.memwrite_cb = None

    def allow_register_overwriting(self, allow_overwrite=True) -> None:
        """Controls whether calls to ``.writeto_mem()`` will overwrite the register contents (
        doesn't by default).

        Useful for tests where the same register block might be read, written to, and then read
        again. But likely not too useful for most tests.

        :param allow_overwrite: New value for `mem_writes_overwrite_registers`, leave unset for
          True
        """
        self.mem_writes_overwrite_registers = allow_overwrite

    def reset_device(self) -> None:
        """Reset this I2CDevice by clearing the register dict, the read_response, the write
        callbacks and the register overwriting."""
        self.reset_write_callbacks()
        self.mem_writes_overwrite_registers = False
        self.read_response = bytearray()
        self.registers.clear()

    def __repr__(self) -> str:
        """Return a basic string representation of this device, just containing address and bus
        ID."""
        bus_id = self.i2c.id_ if self.i2c else -1
        return f"I2CDevice(addr=0x{self.addr:X}, i2c_bus={bus_id})"

    @classmethod
    def _pad_or_trim_buffer(cls, buf: bytearray, length, pad_val: bytes = b"\xff") -> bytearray:
        """Pad or trim provided bytearray `buf` to desired `length` nbytes.

        :param buf: The buffer to trim or pad to desired length.
        :param length: The desired number of bytes that `buf` should be.
        :param pad_val: The byte character to pad `buf` with if padding.
        :returns: Padded or trimmed bytearray buffer
        """
        if len(buf) >= length:
            return buf[:length]

        pad_amnt = length - len(buf)
        return buf + (pad_val * pad_amnt)


# -------------- I2C Bus Class Stuff ---------


class I2C:
    """Test fake implementation of the ESP32 ports ``machine.I2C``.

    This class represents the basic I2C bus, with matching API to the board version. Accepts
    configured instances of the ``I2CDevice`` class which are used to represent the devices
    present on the bus.

    Ideally subclassing this type shouldn't be necessary as test authors should use custom
    ``I2CDevice`` objects.

    Interestingly the ESP32 version of ``machine.I2C`` doesn't actually support quite a few of
    the I2C operations. In the ESP32 C code the I2C type is defined with a protocol struct
    which stores function pointers for I2C operations, and the ESP32 only defines ``transfer``
    which is used for the memory reads and writes. See ``extmod/machine_i2c.c`` to see the
    wrapper functions for the API methods checking the protocol and
    ``ports/esp32/machine_i2c.c`` for the type definition near the bottom.

    This means that the following methods aren't implemented on the ESP32s ``machine.I2C`` and
    cause OSErrors to be raised:

    * ``I2C.init()``
    * ``I2C.start()``    - SoftI2C exclusive
    * ``I2C.stop()``     - SoftI2C exclusive
    * ``I2C.write()``    - SoftI2C exclusive (regular uses writeto)
    * ``I2C.readinto()`` - SoftI2C exclusive (regular uses readfrom_into)

    TODO - implement the softi2c as a subclass
    """

    # Allowed I2C IDs, on ESP32 only 0 and 1 are allowed
    ALLOWED_IDS = (0, 1)

    # Default Pin assignments for the I2C ID's as a dict id -> (SCL, SDA)
    _DEFAULT_PINS = {0: (18, 19), 1: (25, 26)}

    # Multiton registry
    _I2C_REGISTRY: dict[int, "I2C"] = {}

    def __new__(cls, id_=0, **kwargs):
        """Overridden __new__ to implement multiton logic and return busses with the same ID.

        Works similarly to the other classes ``__new__`` methods. It checks if `id_` already
        has an entry in the `_I2C_REGISTRY` and returns that instance if so, otherwise it
        creates a new instance and adds that to the registry before returning.

        This also performs validation on the provided ID, since on the ESP32 only I2C with ID 0
        and 1 are allowed. Raises ValueError if provided ID isn't one of these.

        The multiton allows test code to configure the I2C bus with devices and have
        code-under-test use the same bus without the need for dependency injection.

        TODO - support the legacy softi2c construction which occurs when ID is -1 or ID is
        unset but other arguments are passed.
        """
        if id_ not in cls.ALLOWED_IDS:
            raise ValueError(f"I2C({id_}) doesn't exist")

        if id_ in cls._I2C_REGISTRY:
            return cls._I2C_REGISTRY[id_]

        i2c = super().__new__(cls)
        cls._I2C_REGISTRY[id_] = i2c
        return i2c

    def __init__(self, id_=0, scl=None, sda=None, freq=-1, timeout=-1) -> None:
        """Create a new I2C bus and initialize the attributes.

        To support the multiton instances this method has a re-initialization guard so on first
        initialization the object is created and the main attributes set to defaults, then the
        reinit runs to set any provided arguments. Then on future calls the guard will be
        skipped and only the reinit will run, so pins, freq, and timeout can be changed.

        :param id_: The ID for this bus, limited to specific values on ESP32.
        """
        # Re-initialization guard, on first init set the core attributes
        if not getattr(self, "_initialized", False):
            def_scl, def_sda = self._get_default_pins(id_)
            self.id_ = id_
            self.scl = def_scl
            self.sda = def_sda
            self.freq = 400000
            self.timeout = 50000

            # Extra test attributes
            self.devices: dict[int, I2CDevice] = {}  # Addr -> Instance
            self._initialized = True  # Guard

        self._reinit(scl, sda, freq, timeout)  # Run the reinit to set provided args

    def init(self, scl=None, sda=None, freq=400000, timeout=50000) -> None:
        """Normally does re-initialization but ESP32 port does not support this so just raises.

        In the ESP32 MP C code the I2C implementation only maps the ``transfer`` in the protocol.

        :raises OsError: As operation not supported on board
        """
        raise OSError("I2C operation not supported")

    def deinit(self) -> None:
        """Deinit the bus, only returns None on board.

        Currently just going to return None but could be used to reset the bus later.
        """
        return None

    def scan(self) -> list[int]:
        """Scan for devices registered on this bus between addresses `0x08 <= addr <= 0x77` and
        return a list of their addresses.

        Will just return a list of the ``I2CDevice`` objects that are registered in the range,
        not that devices should be able to be created outside the range.
        """
        device_addresses = [
            addr for addr in self.devices if addr in range(_MIN_ADDR, _MAX_ADDR + 1)
        ]
        return device_addresses

    def readfrom_into(self, addr, buf, stop=True) -> None:
        """Read data from the I2CDevice registered at `addr` into `buf`, amount of data read
        will be the length of `buf`.

        Base instances of ``I2CDevice`` will perform this by reading from an internal
        `read_response` payload.

        :param addr: The address of the device to write to.
        :param buf: The buffer to read device data into, length of buffer is nbytes to read.
        :param stop: Whether to generate a STOP condition when done, unused.
        """
        self._validate_addr(addr)
        device = self.devices[addr]
        device.readfrom_into(buf, stop)

    def readfrom(self, addr, nbytes, stop=True) -> bytes:
        """Read `nbytes` of data from the I2CDevice registered at `addr`."""
        self._validate_addr(addr)
        device = self.devices[addr]
        read_data = device.readfrom(nbytes, stop)
        return read_data

    def readfrom_mem_into(self, addr, memaddr, buf: bytearray, addrsize=8) -> None:
        """Read len(buf) bytes from the I2CDevice registered at `addr` starting from the
        register at `memaddr` and store them in `buf`.
        """
        self._validate_addr(addr)
        device = self.devices[addr]
        device.readfrom_mem_into(memaddr, buf)

    def readfrom_mem(self, addr, memaddr, nbytes, addrsize=8) -> bytes:
        """Read `nbytes` of data from the I2C Device at `addr`, starting from the register at
        `memaddr`.
        """
        self._validate_addr(addr)
        device = self.devices[addr]
        read_data = device.readfrom_mem(memaddr, nbytes, addrsize)
        return read_data

    def writeto_mem(self, addr, memaddr, buf, addrsize=8) -> None:
        """Write data in `buf` to the registers in I2CDevice at `addr`, starting from register
        at `memaddr`.
        """
        self._validate_addr(addr)
        device = self.devices[addr]
        device.writeto_mem(memaddr, buf, addrsize)

    def writeto(self, addr, buf, stop=True) -> int:
        """Write the bytes from `buf` to the I2CDevice registered at `addr`. Return number of
        bytes written"""
        self._validate_addr(addr)
        device = self.devices[addr]
        return device.writeto(buf, stop)

    def writevto(self, addr, vector, stop=True) -> int:
        """Write the `vector` of buffers to the I2CDevice at `addr`. Return total number of
        bytes written

        :param vector: A list or tuple of buffer protocol objects.
        """
        self._validate_addr(addr)
        device = self.devices[addr]
        return device.writevto(vector, stop)

    def start(self) -> None:
        """Generate a START condition on bus, unimplemented on base I2C, raises OSError."""
        raise OSError("I2C operation not supported")

    def stop(self) -> None:
        """Generate a STOP condition on bus, unimplemented on base I2C, raises OSError."""
        raise OSError("I2C operation not supported")

    def readinto(self, buf, nack=True) -> None:
        """Read bytes from bus into buf. Unimplemented on base I2C, raises OSError."""
        raise OSError("I2C operation not supported")

    def write(self, buf) -> int:
        """Write bytes from buf to bus. Unimplemented on base I2C, raises OSError."""
        raise OSError("I2C operation not supported")

    def __repr__(self) -> str:
        """Repr override for string representation.

        Replicates board output which just outputs like
        ``I2C(0, scl=18, sda=19, freq=400000, timeout=50000)``
        """
        scl_id = self.scl.pin_id if self.scl else -1  # Pins shouldn't be none but just to be safe
        sda_id = self.sda.pin_id if self.sda else -1
        freq, timeout = self.freq, self.timeout
        return f"I2C({self.id_}, scl={scl_id}, sda={sda_id}, freq={freq}, timeout={timeout})"

    # ----------- Extra test and util methods (not on board) ---

    def _reinit(self, scl=None, sda=None, freq=-1, timeout=-1) -> None:
        """Perform a 're-initialization' by setting the attributes to the provided arguments.
        Used by the ``__init__`` to support changing the bus attributes via constructor calls,
        as regular init not supported.

        Only values that are provided will be set, if the argument is the default sentinel
        value ( None for pins, -1 for others) then it will remain as the previous value.
        """
        self.scl = Pin(scl) if scl is not None else self.scl
        self.sda = Pin(sda) if sda is not None else self.sda
        self.freq = freq if freq is not -1 else self.freq
        self.timeout = timeout if timeout is not -1 else self.timeout

    @classmethod
    def reset_registry(cls) -> None:
        """Reset the multiton registry by clearing the `_I2C_REGISTRY` dict."""
        cls._I2C_REGISTRY.clear()

    def add_device(self, device: I2CDevice, replace_existing=False) -> None:
        """Add a new ``I2CDevice`` device to this I2C bus at the devices address.

        :raises ValueError: If a device with the same address is already registered and
          ``replace_existing`` is False
        """
        if device.addr in self.devices and not replace_existing:
            raise ValueError(
                f"Error: I2CDevice with address {device.addr} already in registered devices. "
                f"Pass replace_existing=True if wanting to replace"
            )
        self.devices[device.addr] = device

    def _validate_addr(self, addr) -> None:
        """Validate that the provided addr exists in the registered devices, raise if not. Used
        to simplify validation in the operation methods.

        :raises OSError: If addr is not registered on this bus. Uses errno.ENODEV for code.
        """
        if addr not in self.devices:
            raise OSError(errno.ENODEV)

    @classmethod
    def _get_default_pins(cls, id_):
        """Get the default pins for the provided `id_` from the `_DEFAULT_PINS` and return as a
        tuple ``(SCL, SDA)``.

        If ID is unknown then return None tuple, shouldn't occur in actual code.
        """
        if id_ not in cls._DEFAULT_PINS:
            return None, None

        scl, sda = cls._DEFAULT_PINS[id_]
        return Pin(scl), Pin(sda)


class SoftI2C(I2C):
    """Very basic implementation of SoftI2C, extends I2C to support basic operations and stub
    out the API.

    Due to time constraints this will basically be a clone of I2C but with a singleton instance
    rather than a multiton.

    Using a singleton where one instance is created and returned on each further constructor
    call to support code without dependency injection. Ideally in future this would probably be
    replaced with a multiton based on the pin ID's since the board doesn't re-use instances,
    but keeping singleton since I haven't encountered code using multiple SoftI2C buses at once.

    TODO - fully implement this in future, maybe support bitbanging the pins.

    TODO - implement the SoftI2C exclusive ``read()``, ``write()``, ``start()`` and ``stop()``
    methods, skipping now for time. I assume would just require setting up a basic state machine
    for the communication (write address, respond with ACK if device registered, then next write
    will be directed through ``writeto()``, etc)
    """

    # Singleton instance
    _INSTANCE: "SoftI2C | None" = None

    def __new__(cls, *args, **kwargs):
        """Override of __new__ object creation, uses a singleton object which can be reset with
        ``SoftI2C.reset_instance()``.

        Calls ``object.__new__`` instead of ``super().__new__`` to avoid the ID-based registry.
        """
        if cls._INSTANCE is not None:
            return cls._INSTANCE

        i2c = object.__new__(cls)
        cls._INSTANCE = i2c
        return i2c

    def __init__(self, scl=None, sda=None, freq=400000, timeout=50000):
        """SoftI2C constructor, calls the super I2C constructor with ID of -1 to set-up the
        attributes and perform the reinit logic, as SoftI2C doesn't use ID's."""
        super().__init__(id_=-1, scl=scl, sda=sda, freq=freq, timeout=timeout)

    def init(self, scl=None, sda=None, freq=400000, timeout=50000) -> None:
        """SoftI2C reinit, just calls the ``super()._reinit()`` since does the same thing.

        Surprisingly unlike regular I2C this uses default values for `freq` and `timeout`."""
        super()._reinit(scl, sda, freq, timeout)

    def __repr__(self) -> str:
        """Repr override for string representation.

        Replicates board output which just outputs like
        ``SoftI2C(scl=18, sda=19, freq=400000)``
        """
        scl_id = self.scl.pin_id if self.scl else -1  # Pins shouldn't be none but just to be safe
        sda_id = self.sda.pin_id if self.sda else -1
        freq = self.freq
        return f"SoftI2C(scl={scl_id}, sda={sda_id}, freq={freq})"

    @classmethod
    def reset_instance(cls):
        """Reset the _INSTANCE to None, call between tests."""
        cls._INSTANCE = None
