"""class_stubs.py

File for holding the extra stubbed out dummy machine classes. Separate from __init__ as pylint
didn't like the param names shadowing machine methods.

Future work would likely separate these classes into their own files for proper implementation.
"""

from micropython import const
from .pin import Pin

# ------- Stubbed out dummy classes for remaining machine classes ---
#
# These classes will be basic stubbed out API-equal dummy implementations, with basic
# attributes being exposed where applicable, so test authors can control basic responses.
#
# Some basic board operation is replicated but is implemented on a case-by-case basis, but if
# it's easy to implement I'll try replicate it (like different constructor calls)


class Signal:
    """Stubbed out dummy implementation of machine Signal class. Used as an extension of Pin.

    Surprisingly this class doesn't have any custom implementation on the ESP32.

    This basic stub will wrap around the set Pin object and get and set the Pins value for
    value methods. Invert is supported by just returning the opposite of the read Pin value.
    """

    def __init__(self, pin_obj, *args, invert=False, **kwargs) -> None:
        """Signal constructor.

        Can be constructed by either passing a Pin object as the first arg or by passing the
        arguments to create a new Pin object. Both constructions are supported.

        If providing pin arguments here and ``value`` is present in kwargs then it will be set
        with regard to `invert`.
        """
        self.pin = pin_obj if isinstance(pin_obj, Pin) else Pin(pin_obj, *args, **kwargs)
        self.invert = invert
        if "value" in kwargs and invert:
            self.value(kwargs["value"])

    def value(self, x=None) -> int | None:
        """Set pin value if x present, return value otherwise.

        If invert is true then the read value will be inverted and written values will be
        inverted before writing.
        """
        if x is not None:
            x_bool = bool(x)
            self.pin.value(x_bool ^ self.invert)
            return None

        return int(bool(self.pin.value()) ^ self.invert)

    def __call__(self, x=None) -> int | None:
        """Just calls ``.value()``"""
        return self.value(x)

    def on(self):
        """Activate signal, just calls value with 1 currently."""
        self.value(True)

    def off(self):
        """Deactivate signal, just calls value with 0 currently."""
        self.value(False)


class ADC:
    """Basic stubbed out dummy implementation of the machine ADC class."""

    # Constants
    ATTN_0DB = const(0)
    ATTN_2_5DB = const(1)
    ATTN_6DB = const(2)
    ATTN_11DB = const(3)
    WIDTH_9BIT = const(9)
    WIDTH_10BIT = const(10)
    WIDTH_11BIT = const(11)
    WIDTH_12BIT = const(12)

    def __init__(self, gpio_id, sample_ns=-1, atten=-1) -> None:
        """ADC constructor.

        Seems like the ESP32 port only uses Pin ID for the ID rather than supporting channel.

        Not sure if the ESP32 port uses sample_ns but it's an optional keyword only here so
        should be fine.
        """
        self.gpio_id = gpio_id
        self.sample_ns = sample_ns
        self.atten_ = atten
        self.read_val = 0  # Value that gets read from read_u16
        self.uv_val = 0  # Value that gets read from read_uv

    def block(self):
        """Returns the ADCBlock associated with this ADC object.

        For stub implementation just return a new ADCBlock object.
        """
        return ADCBlock(0)

    def init(self, sample_ns=-1, atten=-1):
        """Re-init the ADC, sets provided vals"""
        self.sample_ns = sample_ns if sample_ns != -1 else self.sample_ns
        self.atten_ = atten if atten != -1 else self.atten_

    def read_u16(self) -> int:
        """Return analog reading, for stub just returns ``read_val``."""
        return self.read_val

    def read_uv(self) -> int:
        """Return voltage reading, just return ``uv_val``."""
        return self.uv_val

    def deinit(self) -> None:
        """Deinit the ADC, stub does nothing.

        Another method not in the docs but present on the board because of a macro inclusion
        """

    def __repr__(self):
        return f"ADC(Pin({self.gpio_id}), atten={self.atten_})"

    # --- Legacy methods not in docs

    def atten(self, atten) -> None:
        """Legacy method to set the atten value, just sets atten"""
        self.atten_ = atten

    def read(self) -> int:
        """Legacy method to read the ADC data and return raw value.

        Stub will just return the `read_val`, as code shouldn't be relying on this anyway.
        """
        return self.read_val

    def width(self, width_in) -> None:
        """Legacy method to set the ADC width, stub does nothing."""


class ADCBlock:
    """Basic stubbed out dummy implementation of ADCBlock, which is used to control ADC
    peripherals.

    TODO - fully implement in future work, I believe ADCBlocks map to specific pins and ADC
    objects
    """

    def __init__(self, id_, bits=-1) -> None:
        """ADCBlock constructor.

        On-board it would perform ID validation and raise if an ID was invalid.
        """
        self.id_ = id_
        self.bits = bits

    def init(self, bits=-1):
        """Re-init object, set bits if provided."""
        self.bits = bits if bits != -1 else self.bits

    def connect(self, channel=None, source=None, **kwargs) -> ADC:
        """Connect a channel to the ADC peripheral and return an ADC object representing the
        connection.

        On board this can be called in several ways with either one or both of `channel` and
        `source`, with `channel` as an int for the ADC channel number, and `source` being a Pin
        to sample:
          * ``.connect(channel)`` - Just configures for sampling, I think it uses a default pin
            from the ``madc_obj[]`` array.
          * ``.connect(source)`` - Configures with source pin with default channel
          * ``.connect(channel, source)`` - Configure with channel and source
          * ``.connect(..., **kwargs)`` - Configure with channel and/or source and configure
            resulting ``ADC`` object by passing the kwargs to ``ADC.init()``

        Current stub functionality will just return a new ``ADC`` object with the pin set,
        the basic implementation will also construct the ADC object with appropriate parameters
        like above.
        """
        block_adc = ADC(-1)
        if channel is not None and source is not None:  # Both present, return ADC with pin
            block_adc = ADC(source)
        elif channel is not None and isinstance(channel, int):
            # Only channel, make ADC with -1 pin as defaults not implemented
            # Skip as -1 is starting value
            # block_adc = ADC(-1)
            pass
        elif channel is not None and isinstance(channel, Pin):
            block_adc = ADC(channel.pin_id)

        if kwargs:  # Call init if kwargs provided
            block_adc.init(**kwargs)

        return block_adc

    def __repr__(self):
        return f"ADCBlock({self.id_}, bits={self.bits})"


class DAC:
    """Basic stubbed out dummy implementation of DAC digital to analog converter class.

    Not much to this one."""

    def __init__(self, id_) -> None:
        """Create a new DAC object. ID can be pin or pin id"""
        self.pin = Pin(id_)

    def write(self, value: int):
        """Write 8-bit value to the pin connected to the DAC.

        Currently, will do nothing but confirm that value is 8 bits and raise ValueError if not.
        """
        if value < 0 or value > 255:
            raise ValueError("value out of range")


class PWM:
    """Basic stubbed out dummy implementation of PWM pulse width modulation class.

    This class can either have the main duty be ``duty_u10``, ``duty_u16``, or ``duty_ns``,
    when you use one of the methods to set duty it will convert the input to a u16 value or
    read the u16 value as either u10 or ns. Will replicate the basic conversions.

    The ``duty_ns`` input also takes the ``freq`` into account when setting and getting it.

    TODO - make this properly update the pin value in future.

    TODO - add the more advanced duty functionality in future work with the printing reserving
    last set duty type.
    """

    MAX_16_DUTY = const(65536)
    DEFAULT_FREQ = const(5000)
    DEFAULT_DUTY_U16 = const(32768)

    def __init__(
        self, dest, freq=-1, duty=-1, duty_u16=-1, duty_ns=-1, invert=False, lightsleep=False
    ) -> None:
        """Construct and return a new PWM object.

        Only one of `duty`, `duty_u16`, or `duty_ns` should be specified, but board doesn't
        enforce anything, but prioritises u16 if multiple are set, priority is duty_u16 >
        duty_ns > duty_u10
        """
        self.pin = Pin(dest)
        self.freq_ = freq if freq != -1 else self.DEFAULT_FREQ
        self.duty_u16_ = self.DEFAULT_DUTY_U16
        self.invert = invert
        self.lightsleep = lightsleep
        self.init(freq, duty, duty_u16, duty_ns, invert, lightsleep)

    def init(
        self,
        freq=-1,
        duty=-1,
        duty_u16=-1,
        duty_ns=-1,
        invert: bool | int = -1,
        lightsleep: bool | int = -1,
    ):
        """Re-initialize PWM with provided args.

        Implements the prioritised duty setting (see ``__init__``)
        """
        self.freq_ = freq if freq != -1 else self.freq_
        self.invert = invert if isinstance(invert, bool) else self.invert
        self.lightsleep = lightsleep if isinstance(lightsleep, bool) else self.lightsleep

        # Prioritised duty setting, u16 > ns > u10
        if duty_u16 != -1:
            self.duty_u16(duty_u16)
        elif duty_ns != -1:
            self.duty_ns(duty_ns)
        elif duty != -1:
            self.duty(duty)

    def deinit(self):
        """De-initialize PWM, does nothing currently"""

    def freq(self, value=None) -> int | None:
        """Get or set `freq` based on if value is present.

        NOTE - on board this does some slight conversions based on interfacing with the LEDC, not
        replicating here and just setting value
        """
        if value is None:
            return self.freq_

        self.freq_ = value
        return None

    def duty_u16(self, value=None) -> int | None:
        """Get or set the u16 duty value based on if `value` is present."""
        if value is None:
            return self.duty_u16_

        self.duty_u16_ = value
        return None

    def duty(self, value=None) -> int | None:
        """Either gets or sets duty based on if value is present.

        If value is present then it gets expanded to a u16 value and set, if value is not present
        then the `duty_u16` value will be shrunk to a u10 and returned.
        """
        if value is None:  # Get
            return self.duty_u16_ >> (16 - 10)

        self.duty_u16_ = value << (16 - 10)
        return None

    def duty_ns(self, value=None) -> int | None:
        """Get or set duty value as ns depending on if value is present.

        Replicates board logic by converting input to u16 based on freq when setting,
        and converting u16 to ns based on freq when reading.
        """
        if value is None:
            # GETTER: duty_to_ns
            if self.freq_ == 0:
                return 0  # Prevent divide by 0
            return (self.duty_u16_ * 1000000000 + self.freq_ * (self.MAX_16_DUTY // 2)) // (
                self.freq_ * self.MAX_16_DUTY
            )

        # SETTER: ns_to_duty
        duty = (value * self.MAX_16_DUTY * self.freq_ + 500000000) // 1000000000
        # Replicate C bounds checking
        if value > 0 and duty == 0:
            duty = 1
        elif duty > self.MAX_16_DUTY:
            duty = self.MAX_16_DUTY

        self.duty_u16_ = duty
        return None

    def __repr__(self):
        """String representation of PWM object.

        Lightsleep and invert are only present in the print if they're true, otherwise they're
        absent.

        TODO - implement the last set duty type.
        """
        invert_str: str = ", invert=True" if self.invert else ""
        lightsleep_str: str = ", lightsleep=True" if self.lightsleep else ""
        return f"PWM({self.pin}, duty_u16={self.duty_u16_}{invert_str}{lightsleep_str})"


class SPI:
    """Basic stubbed out dummy implementation of SPI communication class.

    In future this would be implemented similarly to UART/ I2C but with support for things like
    a "chip select" pin to choose the device being written to, or just fake it by programming
    responses.

    Future work would also need the multiton stuff, re-init logic with proper default values,
    and ID validation with default pin assignment.

    For the current basic stub the `read_buf` can be set to control what gets read, obviously
    future implementation would implement something similar to UART read response strategies.

    ``SoftSPI`` will just be a subclass of this for now but a proper implementation would be
    good for future.
    """

    MSB = const(0)
    LSB = const(1)

    def __init__(
        self,
        id_,
        baudrate=1000000,
        polarity=0,
        phase=0,
        bits=8,
        firstbit=0,
        sck=None,
        mosi=None,
        miso=None,
    ) -> None:
        """Construct and initialize a new SPI object.

        TODO - future work needs default pin assignments
        TODO - in future this would need the proper re-init logic and guards etc.
        """
        self.id_ = id_
        self.baudrate = baudrate
        self.polarity = polarity
        self.phase = phase
        self.bits = bits
        self.firstbit = firstbit
        # Since default pin assignment not implemented use 0
        self.sck = Pin(sck) if sck is not None else Pin(0)
        self.mosi = Pin(mosi) if mosi is not None else Pin(0)
        self.miso = Pin(miso) if miso is not None else Pin(0)

        # Buffer to read from
        self.read_buf = bytearray()

    def init(
        self,
        baudrate=-1,
        polarity=-1,
        phase=-1,
        bits=-1,
        firstbit=-1,
        sck=None,
        mosi=None,
        miso=None,
    ):
        """Re-initialize the SPI bus with provided params.

        Basic implementation will only set provided objects.
        """
        self.baudrate = baudrate if baudrate != -1 else self.baudrate
        self.polarity = polarity if polarity != -1 else self.polarity
        self.phase = phase if phase != -1 else self.phase
        self.bits = bits if bits != -1 else self.bits
        self.firstbit = firstbit if firstbit != -1 else self.firstbit

        self.sck = Pin(sck) if sck is not None else self.sck
        self.mosi = Pin(mosi) if mosi is not None else self.mosi
        self.miso = Pin(miso) if miso is not None else self.miso

    def deinit(self):
        """Turn off the bus. Does nothing"""

    def read(self, nbytes, write=0x00) -> bytes:
        """Read `nbytes` from the bus while continuously writing single byte `write`. Returns
        bytes read.

        Basic implementation will just read from the `read_buf`, if `nbytes` is larger than
        buffer size then just read the bytes available in `read_buf`. Not technically accurate
        but fine for a stub.
        """
        read_len = min(nbytes, len(self.read_buf))
        read_data = bytes(self.read_buf[:read_len])
        return read_data

    def readinto(self, buf, write=0x00) -> None:
        """Read ``len(buf)`` bytes from the bus into `buf` while continously writing single
        byte `write`.

        Delegates to ``.read()``, meaning just reads from `read_buf` and if nbytes is larger
        than read_buf len then the read data will be placed at the start of `buf` and rest will
        be padded.
        """
        read_data = self.read(len(buf), write)
        buf[: len(read_data)] = read_data

    def write(self, buf) -> None:
        """Write data in `buf` to bus, just returns None."""
        return None

    def write_readinto(self, write_buf, read_buf) -> None:
        """Write the bytes from `write_buf` while reading data into `read_buf`. Both buffers
        must have same length.

        Currently, will just call ``.write()`` with the write_buf ``.readinto()`` with the
        read_buf, future work would need better implementation obviously, probably character by
        character.
        """
        if len(write_buf) != len(read_buf):
            raise ValueError("buffers must be the same length")

        self.write(write_buf)
        self.readinto(read_buf)

    def __repr__(self):
        return (
            f"SPI(id={self.id_}, baudrate={self.baudrate}, polarity={self.polarity}"
            f", phase={self.phase}, bits={self.bits}, firstbit={self.firstbit}"
            f", sck={self.sck.pin_id}, mosi={self.mosi.pin_id}, miso={self.miso.pin_id}"
        )


class SoftSPI(SPI):
    """Basic stubbed out dummy of SoftSPI, represents software bit-banging implementation of
    SPI (much like SoftI2C).

    This basic implementation will just be a subclass of SPI with slightly different init
    defaults and repr. Future work would fully implement this based on proper SPI implementation.
    """

    def __init__(
        self,
        baudrate=500000,
        polarity=0,
        phase=0,
        bits=8,
        firstbit=0,
        sck=None,
        mosi=None,
        miso=None,
    ) -> None:
        """Construct a SoftSPI object, just calls super init."""
        # fmt: off
        super().__init__(
            id_=-1, baudrate=baudrate, polarity=polarity, phase=phase, bits=bits,
            firstbit=firstbit, sck=sck, mosi=mosi, miso=miso
            )
        # fmt: on

    def __repr__(self):
        return (
            f"SoftSPI(baudrate={self.baudrate}, polarity={self.polarity}"
            f", phase={self.phase}, firstbit={self.firstbit}, sck={self.sck.pin_id}"
            f", mosi={self.mosi.pin_id}, miso={self.miso.pin_id}"
        )


# NOTE - seems like I2CTarget is not available on the base ESP32 boards due to hardware
#  limitations, so not implementing.


class I2S:
    """Basic stubbed out dummy implementation of I2S Inter-IC sound bus class.

    This class seems quite complex so am just gonna implement the basic API methods with stuff
    like ``.read()`` returning an empty bytes as not sure what a response would even look like.

    Future work would involve properly implementing the multiton for this as well as the
    """

    # Class constants
    RX = const(1)
    TX = const(2)
    STEREO = const(1)
    MONO = const(0)

    # pylint: disable-next=redefined-builtin
    def __init__(self, id_, sck, ws, sd, mode, bits, format, rate, ibuf):
        """Construct an I2S object with given ID and attributes.

        Unlike most hardware classes I think that all the parameters are required to be
        provided for a valid call. It also does validation on basically all of the parameters
        so future work would need to replicate that.
        """
        self.id_ = id_
        self.ibuf = ibuf
        self.rate = rate
        self.format_ = format
        self.bits = bits
        self.mode = mode
        self.sd = Pin(sd)
        self.ws = Pin(ws)
        self.sck = Pin(sck)

    # pylint: disable-next=redefined-builtin
    def init(self, sck, ws, sd, mode, bits, format, rate, ibuf) -> None:
        """Re-init the I2S object.

        Based on the C code it seems like this requires all the arguments to be present like
        with the __init__.

        TODO - future work will involve the value validation here
        """
        self.ibuf = ibuf
        self.rate = rate
        self.format_ = format
        self.bits = bits
        self.mode = mode
        self.sd = sd
        self.ws = ws
        self.sck = sck

    def deinit(self) -> None:
        """Deinit the bus, does nothing."""

    def readinto(self, buf) -> int:
        """Read audio samples into `buf` and return number of bytes read.

        At the moment this will just do nothing and return 0.
        """
        return 0

    def write(self, buf) -> int:
        """Write audio samples in `buf` and return number of bytes written.

        Stub does nothing and just returns 0.
        """
        return 0

    def irq(self, handler) -> None:
        """Set an IRQ callback `handler` which gets called when buffer gets emptied when
        writing, or becomes full when reading.

        Currently, this will do nothing.
        """

    def shift(self, *, buf, bits, shift) -> None:
        """Bitwise shift all audio samples in `buf`.

        Once again, currently does nothing.
        """

    def __repr__(self):
        """String representation of I2S object.

        The string output for this on-board is quite horrible, each attribute is separated with
        a newline for some reason, future work would involve making this accurate.
        """
        sck_id = self.sck.pin_id
        sd_id = self.sd.pin_id
        ws_id = self.ws.pin_id
        return (
            f"I2S(id={self.id_},\nsck={sck_id},\nws={ws_id},\nsd={sd_id},\nmode={self.mode},\n"
            f"bits={self.bits}, format={self.format_},\nrate={self.rate}, ibuf={self.ibuf})"
        )


# NOTE - looks like CAN is also not available on the ESP32, so skipping that.


class RTC:
    """Basic stubbed out dummy implementation of the RTC (real-time clock) class.

    Basic stub functionality will allow setting and reading a datetimetuple and a memory
    bytearray, future work could either simulate an actual RTC or allow programming a set of
    read responses.

    The methods ``.deinit()``, ``.now()``, ``.alarm()``, ``.alarm_left()``, ``.alarm_cancel()``,
    and ``.irq()`` not available on the ESP32.
    """

    def __init__(self):
        """Creates the RTC object, sets a default stub datetime and memory bytearray.

        Interestingly the ESP32 version doesn't support any parameters here.
        """
        # Default to Jan 1st, 2026, 00:00:00
        # (year, month, day, weekday, hours, minutes, seconds, microseconds)
        year, month, day = 2026, 1, 1
        weekday = self._calculate_weekday(year, month, day)
        self._datetime = (year, month, day, weekday, 0, 0, 0, 0)
        self.mem_buf = bytearray()

    def _calculate_weekday(self, year, month, day):
        """Helper to calculate the day of the week using Sakamoto's algorithm, to avoid
        reliance on ``time`` module (since will be replacing it and don't want to cause any
        problems).

        https://www.geeksforgeeks.org/dsa/tomohiko-sakamotos-algorithm-finding-day-week/

        Returns an integer 0-6 representing Monday-Sunday.
        """
        # A magic lookup table for month offsets
        t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]

        if month < 3:
            year -= 1

        dow = (year + year // 4 - year // 100 + year // 400 + t[month - 1] + day) % 7
        return (dow + 6) % 7

    def datetime(self, datetimetuple=None):
        """Either get or set date and time of RTC based on if `datetimetuple` provided.

        Stub functionality will either return the stored datetimetuple or set it to the
        provided `datetimetuple` if present.

        Tuple format is:
        ``(year, month, day, weekday, hours, minutes, seconds, microseconds)``
        """
        if datetimetuple is not None:
            self._datetime = datetimetuple
            return None

        return self._datetime

    def init(self, datetime):
        """Initialize the RTC.

        Sets the stored stub datetime, calculates weekday for the stored tuple.

        datetime in format of:
        ``(year, month, day, hour, minute, second, microsecond, tzinfo)``
        but `tzinfo` unused.
        """
        year, month, day, hour, minute, second, microsecond, _ = datetime

        # Calculate weekday and store
        weekday = self._calculate_weekday(year, month, day)
        self._datetime = (year, month, day, weekday, hour, minute, second, microsecond)

    def memory(self, data=None) -> bytes | None:
        """Either write `data` to device memory or read device memory if `data` is absent.

        This will either replace the contents of `mem_buf` if `data` is present or will read
        the contents of `mem_buf`. This seems to match the board implementation where only
        written data is read and writing seems to overwrite whole data.
        """
        if data is not None:
            self.mem_buf[:] = data
            return None

        return bytes(self.mem_buf)


class Timer:
    """Basic stubbed out dummy implementation of the Timer class.

    For simplicity this won't have any functionality besides basic period calculations for
    storing and printing, future work could expand this to allow a basic simulation of a
    virtual timer.

    Future work would also require a multiton registry and ID validation.
    """

    # Timer mode constants
    ONE_SHOT = const(0)
    PERIODIC = const(1)

    VIRTUAL_TIMER_FREQ_HZ = const(1000000)

    def __init__(
        self,
        id_=-1,
        *,
        mode=1,
        callback=None,
        period=0xFFFFFFFF,
        tick_hz=1000,
        freq=None,
        hard=False,
    ):
        """Construct and initialize timer.

        On the ESP32 the default ID is -1 which is for virtual timer.

        This init logic is likely not be entirely accurate, the init sequence for the Timers
        seems to calculate period based on either the `freq` or `period` args, will try
        replicate the basic calculations but future work would verify this.

        Also, interestingly the ESP32 port also has a `tick_hz` parameter which isn't mentioned
        in the docs. Seems to be used to calculate the period when freq isn't supplied.
        """
        self.id_ = id_
        self.mode = mode
        self.callback = callback
        self.period = 0
        self.init(
            mode=mode, callback=callback, period=period, tick_hz=tick_hz, freq=freq, hard=hard
        )

    def init(self, mode=1, callback=None, period=0xFFFFFFFF, tick_hz=1000, freq=None, hard=False):
        """Initialize the timer.

        Replicates the basic period calculation logic which uses `freq` if set, otherwise uses
        `period`, the timer freq (which for software timers is `VIRTUAL_TIMER_FREQ_HZ`) and
        `tick_hz`. Will just use the virtual timer freq for this but future work would need to
        support hardware timer freqs.

        Also replicates raising a ValueError if hard is true (as board does).
        """
        if hard:
            raise ValueError("hard Timers are not implemented")
        self.mode = mode
        self.callback = callback

        if freq is not None:
            self.period = int(self.VIRTUAL_TIMER_FREQ_HZ / freq)
        else:
            self.period = int((period * self.VIRTUAL_TIMER_FREQ_HZ) / tick_hz)

    def deinit(self):
        """Deinit the Timer, does nothing."""

    def value(self) -> int:
        """Get the value of the timer, I think just the period counter.

        Another method not in the docs but available on the ESP32. For dummy just return 0.
        """
        return 0

    def __repr__(self):
        """String representation of Timer.

        Interestingly the ESP32 port has a bug in their Timer print implementation that gets
        the modes inverted, so when you're ONE_SHOT it prints PERIODIC and vice versa.
        Implementing a correct version here as I assume this will be fixed eventually.

        I'm also not sure why the board version gives period=0 for default with no args but
        other calculations work as expected.
        """
        period = int(self.period / (self.VIRTUAL_TIMER_FREQ_HZ / 1000))  # Converted to ms
        mode = "ONE_SHOT" if self.mode == 0 else "PERIODIC"
        return f"Timer({self.id_}, mode={mode}, period={period}"


class Counter:
    """Basic stubbed out dummy implementation of pulse counting Counter class.

    On the ESP32 this class is implemented in python (suprisingly) as a basic shim around the
    ``esp32.PCNT`` class. The board implementation subclasses a parent class ``_CounterBase``
    which is also subclassed by ``Encoder`` so they are quite similar.

    This basic implementation will not use PCNT (both for simplicity and because the ``esp32``
    stubs aren't implemented yet) and will just return a `val` attribute.

    Future work could implement this around the PCNT stub or properly implement a simulated
    pulse counter.

    Also, the ESP32 port does not have the ``Counter.cycles()`` or ``Counter.irq()`` methods.
    """

    # Constants (IRQ constants not on ESP32)
    UP = const(1)
    DOWN = const(2)
    RISING = const(1)
    FALLING = const(2)

    def __init__(self, unit_id, src, *args, filter_ns=0, edge=1, direction=1, **kwargs):
        """Create a new counter.

        Initialization might not be the most accurate as the python code is a bit harder to
        read but initialization seems to pass through the ``.__init__()`` of the base
        ``_CounterBase`` parent class which passes the `*args` and `**kwargs` to a
        ``._configure()`` abstract method which does the class-specific initialization. I've
        included the configure params into the regular param list.
        """
        self.unit_id = unit_id
        self.val = 0

    def init(self, *args, **kwargs):
        """Re-init, just calls __init__ like on board"""
        # pylint: disable-next=unnecessary-dunder-call
        self.__init__(self.unit_id, *args, **kwargs)

    def deinit(self):
        """Deinit and stop the counter, does nothing."""

    def value(self, value=None) -> int:
        """Get and optionally set the counter value if `value` is present.

        Will just read the ``self.val`` value and set it if `value` provided, not accurate but
        good for basic stubbing. Actual implementation would need the overflow logic stuff.
        """
        val = self.val
        if value is not None:
            self.val = value
        return val


class Encoder:
    """Basic stubbed out dummy implementation of the quadrature signal Encoder class.

    Like with ``machine.Counter`` this class in the ESP32 port is a basic shim around
    ``esp32.PCNT``. Like with the Counter stub this will just be implemented as a basic
    standalone dummy as PCNT isn't implemented yet, but future work could implement this properly.

    Counter and Encoder are very similar so check Counter for justifications for things.
    """

    def __init__(self, unit_id, phase_a, phase_b, *args, filter_ns=0, phases=1, **kwargs):
        """Create a new encoder.

        Mostly following the param strategy from ``Counter.__init__()``.

        Also recreates board logic of raising ValueError if `phases` isn't one of ``(1, 2,
        4)``, because easy to implement.
        """
        if phases not in (1, 2, 4):
            raise ValueError("phases")

        self.unit_id = unit_id
        self.val = 0
        self.phases_ = phases

    def init(self, *args, **kwargs):
        """Re-init, just calls __init__ like on board"""
        # pylint: disable-next=unnecessary-dunder-call
        self.__init__(self.unit_id, *args, **kwargs)

    def deinit(self):
        """Deinit the encoder, does nothing."""

    def value(self, value=None) -> int:
        """Get and optionally set encoder value.

        Just returns and optionally sets the ``self.val`` if `value` present. Actual
        implementation would need overflow logic.
        """
        val = self.val
        if value is not None:
            self.val = value
        return val

    def phases(self) -> int:
        """Return `phases_`."""
        return self.phases_


class WDT:
    """Basic stubbed out dummy implementation of the Watchdog timer.

    This implementation won't do much (as obviously don't want to reset), but it could be good for
    future work to implement a version that raises or runs a callback when the timer expires,

    TODO - future work, implement some feedback when timer expires
    """

    # pylint: disable-next=redefined-builtin
    def __init__(self, id=0, timeout=5000):
        """Initialize and start new watchdog timer.

        Doesn't start a timer here but creates it
        """
        self.id_ = id
        self.timeout = timeout

    def feed(self) -> None:
        """Feed the watchdog timer, does nothing."""


# NOTE - SD not available on ESP32 so skipping


class SDCard:
    """Basic stubbed out dummy implementation of SDCard block storage class.

    This is a bit of a confusing class so this dummy implementation will likely be pretty basic.

    The docs state that the SDCard class implements a ``vfs.AbstractBlockDev`` protocol. This
    is a documentation only class and isn't real, it only defines a list of methods that must
    be implemented and what they do. Just to implement a proper base I will stub out these
    protocol methods but they won't have any functionality.

    I'm not too sure how the IO system reads devices like this so the AbstractBlockDev methods
    will be implemented with no functionality, this means that attempting to actually use the
    class for IO operations will likely fail, but the main requirement is to be able to import
    without error. Future work would make these methods return proper responses.

    Future work could implement this through a fake filesystem, something kinda like
    ``pyfakefs``. Or could just use a basic bytearray for faked memory.

    Something similar to the example in the docs could be implemented:
    https://docs.micropython.org/en/latest/reference/filesystem.html#esp32
    """

    def __init__(
        self,
        slot=1,
        width=1,
        cd=None,
        wp=None,
        miso=None,
        mosi=None,
        sck=None,
        cs=None,
        freq=20000000,
    ):
        """Initialize SDCard. Just sets some attributes."""
        self.slot = slot

    def deinit(self):
        """Deinit device, does nothing."""

    def info(self):
        """Returns a 2-item tuple of card size and block size.

        Stub just returns (0, 0).
        """
        return 0, 0

    # -- AbstractBlockDev methods
    # TODO - implement properly in future

    def readblocks(self, block_num, buf, offset=0):
        """Read blocks of memory in SDCard into buf.

        Current dummy implementation will do nothing and return 0.
        """
        return 0

    def writeblocks(self, block_num, buf, offset=0):
        """Write blocks of data from buf into SDCard.

        Once again is just a dummy implementation that will do nothing and return 0.
        """
        return 0

    def ioctl(self, op, arg):
        """Control the block device and query parameters.

        Once again, for simplicity this won't have any functionality and will just return 0
        instead of handling any ops.
        """
        return 0


# NOTE - it seems like machine.USBDevice is not available on the ESP32. It might be available
#  on some of the other ESP32 models but not our base version. But check a bit more later.


class TouchPad:
    """Basic stubbed out dummy implementation of the ESP32-specific TouchPad class for reading
    a capacitive touch sensors. Will just return basic read_val.

    Future work could simulate this a tiny bit with a static value and a threshold.
    """

    def __init__(self, pin_id):
        """Create touchpad for pin.

        Future work would put proper validation for the pin (since only specific pins can be used)
        """
        self.pin = Pin(pin_id)
        self.read_val = 0

    def read(self) -> int:
        """Read the value. Just returns the `read_val`"""
        return self.read_val

    def config(self, value) -> None:
        """Configure the threshold for the sensor to be considered touched. Does nothing."""
