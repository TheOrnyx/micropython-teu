"""test_i2c_ds1307.py - Test file for testing a DS1307 RTC driver using an I2CDevice to mimick
the device"""

import unittest
import fake_machine
from micropython import const

# pylint: disable=protected-access, invalid-name

TEST_ADDR = 0x08  # Address for our test device

DS1307_ADDR = 0x68  # Default I2C address of the DS1307

DATETIME_REG = const(0)  # 0x00-0x06, start of the sequential 7-byte datetime block
SECONDS_REG = const(0)
MINUTES_REG = const(1)
HOURS_REG = const(2)
WEEKDAY_REG = const(3)
DATE_REG = const(4)
MONTH_REG = const(5)
YEAR_REG = const(6)
CHIP_HALT = const(128)  # CH chip halt stored in top bit of seconds
CONTROL_REG = const(7)  # 0x07


class DS1307:
    """Driver for the DS1307 RTC.

    Slightly modified version of the driver used in the Quilty environment project, with added
    methods that read the individual registers, so can show more examples of the random
    register access with the ``I2CDevice``.
    """

    def __init__(self, i2c, addr=DS1307_ADDR):
        self.i2c: fake_machine.I2C = i2c  # Type hinted for editor completion
        self.addr = addr
        self.weekday_start = 1
        self._halt = False

    def _dec2bcd(self, value):
        """Convert decimal to binary coded decimal (BCD) format"""
        return (value // 10) << 4 | (value % 10)

    def _bcd2dec(self, value):
        """Convert binary coded decimal (BCD) format to decimal"""
        return ((value >> 4) * 10) + (value & 0x0F)

    def datetime(self, datetime=None):
        """Get or set datetime"""
        if datetime is None:
            buf = self.i2c.readfrom_mem(self.addr, DATETIME_REG, 7)
            return (
                self._bcd2dec(buf[6]) + 2000,  # year
                self._bcd2dec(buf[5]),  # month
                self._bcd2dec(buf[4]),  # day
                self._bcd2dec(buf[3] - self.weekday_start),  # weekday
                self._bcd2dec(buf[2]),  # hour
                self._bcd2dec(buf[1]),  # minute
                self._bcd2dec(buf[0] & 0x7F),  # second
                0,  # subseconds
            )
        buf = bytearray(7)
        buf[0] = self._dec2bcd(datetime[6]) & 0x7F  # second, msb = CH, 1=halt, 0=go
        buf[1] = self._dec2bcd(datetime[5])  # minute
        buf[2] = self._dec2bcd(datetime[4])  # hour
        buf[3] = self._dec2bcd(datetime[3] + self.weekday_start)  # weekday
        buf[4] = self._dec2bcd(datetime[2])  # day
        buf[5] = self._dec2bcd(datetime[1])  # month
        buf[6] = self._dec2bcd(datetime[0] - 2000)  # year
        if self._halt:
            buf[0] |= 1 << 7
        self.i2c.writeto_mem(self.addr, DATETIME_REG, buf)
        return None

    def halt(self, val=None):
        """Power up, power down or check status"""
        if val is None:
            return self._halt
        reg = self.i2c.readfrom_mem(self.addr, DATETIME_REG, 1)[0]
        if val:
            reg |= CHIP_HALT
        else:
            reg &= ~CHIP_HALT
        self._halt = bool(val)
        self.i2c.writeto_mem(self.addr, DATETIME_REG, bytearray([reg]))

    def square_wave(self, sqw=0, out=0):
        """Output square wave on pin SQ at 1Hz, 4.096kHz, 8.192kHz or 32.768kHz,
        or disable the oscillator and output logic level high/low."""
        rs0 = 1 if sqw == 4 or sqw == 32 else 0
        rs1 = 1 if sqw == 8 or sqw == 32 else 0
        out = 1 if out > 0 else 0
        sqw = 1 if sqw > 0 else 0
        reg = rs0 | rs1 << 1 | sqw << 4 | out << 7
        self.i2c.writeto_mem(self.addr, CONTROL_REG, bytearray([reg]))

    # --------- Added for demo: single-register "random access" getters -----

    def get_seconds(self):
        """Read just the seconds register (masking off the CH/halt bit) and decode it."""
        reg = self.i2c.readfrom_mem(self.addr, SECONDS_REG, 1)[0]
        return self._bcd2dec(reg & 0x7F)

    def get_minutes(self):
        """Read just the minutes register and decode it."""
        reg = self.i2c.readfrom_mem(self.addr, MINUTES_REG, 1)[0]
        return self._bcd2dec(reg)

    def get_hours(self):
        """Read just the hours register and decode it."""
        reg = self.i2c.readfrom_mem(self.addr, HOURS_REG, 1)[0]
        return self._bcd2dec(reg)

    def get_weekday(self):
        """Read just the weekday register and decode it."""
        reg = self.i2c.readfrom_mem(self.addr, WEEKDAY_REG, 1)[0]
        return self._bcd2dec(reg - self.weekday_start)

    def get_date(self):
        """Read just the day-of-month register and decode it."""
        reg = self.i2c.readfrom_mem(self.addr, DATE_REG, 1)[0]
        return self._bcd2dec(reg)

    def get_month(self):
        """Read just the month register and decode it."""
        reg = self.i2c.readfrom_mem(self.addr, MONTH_REG, 1)[0]
        return self._bcd2dec(reg)

    def get_year(self):
        """Read just the year register and decode it (as a full 4-digit year)."""
        reg = self.i2c.readfrom_mem(self.addr, YEAR_REG, 1)[0]
        return self._bcd2dec(reg) + 2000

    def get_control_register(self):
        """Read the raw control register byte (square wave / output configuration)."""
        return self.i2c.readfrom_mem(self.addr, CONTROL_REG, 1)[0]


# ------- Utility functions for getting datetime bytes ---


def _encode_bcd(value):
    """Convert an integer to a single BCD-encoded byte value.

    Copy of the driver version, just to avoid changing it.
    """
    return (value // 10) << 4 | (value % 10)


def datetime_to_reg_bytes(dt, weekday_start=1, halt=False):
    """Convert a ``(year, month, day, weekday, hour, minute, second, subsec)`` datetime tuple
    to a bytes object matching the register block contents.

    Tuple matches the DS1307 datetime tuple, subsec is unused as driver forces to 0 but keeping
    in tuple for output parity.

    Helpful for building the register block byte sequence used with
    ``I2CDevice.set_reg_block()`` in tests, without hand-writing raw byte literals.

    :param dt: The datetime tuple, same layout as ``DS1307.datetime()``.
    :param weekday_start: Same as ``DS1307.weekday_start``, defaults to 1.
    :param halt: Whether to set the CH (clock halt) bit in the seconds byte.
    """
    year, month, day, weekday, hour, minute, second, _subsec = dt
    buf = bytearray(7)
    buf[0] = _encode_bcd(second) & 0x7F
    if halt:
        buf[0] |= 1 << 7
    buf[1] = _encode_bcd(minute)
    buf[2] = _encode_bcd(hour)
    buf[3] = _encode_bcd(weekday + weekday_start)
    buf[4] = _encode_bcd(day)
    buf[5] = _encode_bcd(month)
    buf[6] = _encode_bcd(year - 2000)
    return bytes(buf)


# ------- Demo tests, using the modified DS1307 driver with configured I2CDevices ---


class TestDS1307Example(unittest.TestCase):
    """A handful of example tests demonstrating the DS1307 driver running against a fake
    I2CDevice rather than real hardware."""

    def setUp(self):
        # Clean-up registry to avoid leaking state between tests
        fake_machine.reset_registries()
        self.addCleanup(fake_machine.reset_registries)

        # Create the objects in setUp to avoid creating at start of each test
        self.i2c = fake_machine.I2C(0)
        self.device = fake_machine.I2CDevice(DS1307_ADDR, self.i2c)
        self.rtc = DS1307(self.i2c)

    def test_datetime_read_from_reg_block(self):
        """Set the full 7-byte datetime block with `datetime_to_reg_bytes()` and check the
        driver decodes it correctly via its normal sequential `.datetime()` read."""
        dt = (2024, 3, 14, 3, 9, 41, 22, 0)  # 2024-03-14, weekday=3, 09:41:22
        self.device.set_reg_block(DATETIME_REG, datetime_to_reg_bytes(dt))

        rtc_dt = self.rtc.datetime()
        self.assertIsNotNone(rtc_dt)
        self.assertEqual(rtc_dt, dt)

    def test_individual_register_getters_match_block(self):
        """Set the same register block, but read back the fields by using the random-access
        methods, rather than the `.datetime()`"""
        dt = (2024, 3, 14, 3, 9, 41, 22, 0)
        self.device.set_reg_block(DATETIME_REG, datetime_to_reg_bytes(dt))

        self.assertEqual(self.rtc.get_year(), dt[0])
        self.assertEqual(self.rtc.get_month(), dt[1])
        self.assertEqual(self.rtc.get_date(), dt[2])
        self.assertEqual(self.rtc.get_weekday(), dt[3])
        self.assertEqual(self.rtc.get_hours(), dt[4])
        self.assertEqual(self.rtc.get_minutes(), dt[5])
        self.assertEqual(self.rtc.get_seconds(), dt[6])

    def test_datetime_write_updates_registers(self):
        """Enable register overwriting on the device, write a new datetime through the driver,
        and check it landed correctly by reading individual registers back."""
        # Pre-populate a placeholder block so there's something to overwrite
        self.device.set_reg_block(DATETIME_REG, bytes(7))
        self.device.allow_register_overwriting()

        dt = (2025, 12, 25, 3, 8, 30, 0, 0)
        self.rtc.datetime(dt)

        self.assertEqual(self.rtc.get_year(), dt[0])
        self.assertEqual(self.rtc.get_month(), dt[1])
        self.assertEqual(self.rtc.get_date(), dt[2])
        self.assertEqual(self.rtc.get_weekday(), dt[3])
        self.assertEqual(self.rtc.get_hours(), dt[4])
        self.assertEqual(self.rtc.get_minutes(), dt[5])
        self.assertEqual(self.rtc.get_seconds(), dt[6])

    def test_halt_sets_ch_bit_on_seconds_register(self):
        """Set the seconds register with `set_single_reg()`, then check that ``.halt(True)``
        performs a read-modify-write that sets the CH bit.
        """
        self.device.set_single_reg(SECONDS_REG, b"\x22")  # 22 seconds, CH bit clear
        self.device.allow_register_overwriting()

        self.assertFalse(self.rtc.halt())  # Cached value starts False
        self.rtc.halt(True)

        self.assertTrue(self.rtc.halt())
        raw_seconds = self.device.registers[SECONDS_REG][0]
        self.assertEqual(raw_seconds, 0x22 | CHIP_HALT)
        # get_seconds() should still decode the un-halted value correctly, since it masks
        # off the CH bit
        self.assertEqual(self.rtc.get_seconds(), 22)


if __name__ == "__main__":
    unittest.main()
