"""test_i2c_lis3dh.py

Off-board UNIX tests for the TinyPICO MicroPython LIS3DH accelerometer driver (lis3dh.py), using
a ``fake_machine.I2CDevice`` on a ``fake_machine.I2C`` bus to mimic the sensor at 0x18.

These test the register reading/parsing and register writing logic of the driver. Sensor data is
loaded into the fake registers as raw bytes and the tests check the driver decodes them into
the correct physical values. Writes the driver makes are captured with the ``memwrite_cb``
callback so the init sequence and the config values can be checked too.

Register overwriting is enabled on the device so that the driver's read-modify-write operations
(``data_rate``, ``range`` and ``set_tap()``) see the effect of earlier writes, like they would on
the real chip. Without it the constructor would read stale register values.

NOTE - the driver reads multi-byte values with bit 7 of the register address set (the LIS3DH
address auto-increment bit), so the data blocks are set at ``OUT_X_L | 0x80`` and
``OUTADC1_L | 0x80`` instead of at the plain datasheet addresses. The fake device just sees the
address the driver sends, and doesn't know about the auto-increment bit.

The last section contains a few tests that simulate faulty input/ hardware conditions the driver
currently doesn't handle. These are marked ``expectedFailure`` and will start reporting
"unexpected success" once the driver is hardened, at which point the decorator can be removed.

AI tools were used to help with creating input data and some calculation logic due to time
constraints preventing in-depth research, all outputs were manually checked and validated
before committing.

Datasheet:
https://www.st.com/resource/en/datasheet/lis3dh.pdf
"""

import struct
import unittest
from teu import fake_machine

from . import lis3dh

LIS_ADDR = 0x18  # Default LIS3DH address (SDO/SA0 pin low)

# LIS3DH registers the tests touch directly.
# Values copied from driver as can't access private members for some reason.
REG_OUTADC1_L = 0x08  # ADC1 low byte, ADC2 and ADC3 follow it in 2 byte steps
REG_WHOAMI = 0x0F
REG_TEMPCFG = 0x1F
REG_CTRL1 = 0x20
REG_CTRL3 = 0x22
REG_CTRL4 = 0x23
REG_CTRL5 = 0x24
REG_OUT_X_L = 0x28  # Start of the 6 byte X, Y, Z block (little-endian int16s)
REG_CLICKCFG = 0x38
REG_CLICKSRC = 0x39
REG_CLICKTHS = 0x3A
REG_TIMELIMIT = 0x3B
REG_TIMELATENCY = 0x3C
REG_TIMEWINDOW = 0x3D

AUTO_INCREMENT = 0x80  # Bit 7 of the address, set by the driver for multi-byte reads

# Raw counts per 1g the driver divides by for each range (copied from the driver). They are
# ~2.4% off the datasheet sensitivities, so these tests check the per-range selection logic.
RANGE_DIVIDERS = (
    (lis3dh.RANGE_2_G, 16380),
    (lis3dh.RANGE_4_G, 8190),
    (lis3dh.RANGE_8_G, 4096),
    (lis3dh.RANGE_16_G, 1365),
)


class TestLIS3DHWithFake(unittest.TestCase):
    """Test class for the LIS3DH driver using ``fake_machine.I2C`` and a
    ``fake_machine.I2CDevice`` to mimic the hardware."""

    def setUp(self):
        """Create the bus and the device, fill it with sane default registers, and start
        recording writes.

        The driver is created inside each test (with ``_make_driver()``) since its constructor
        reads/writes registers and some tests need to check those or pass constructor arguments.
        """
        fake_machine.I2C.reset_registry()
        self.addCleanup(fake_machine.I2C.reset_registry)

        self.i2c = fake_machine.I2C(0)
        self.dev = fake_machine.I2CDevice(LIS_ADDR, self.i2c)
        self.dev.allow_register_overwriting()

        # Record tuple of (memaddr, data) for every register write.
        # So tests can assert that specific register writes took place.
        self.writes = []
        self.dev.set_write_callbacks(
            memwrite_cb=lambda dev, reg, buf: self.writes.append((reg, bytes(buf)))
        )

        # Device ID, and all the single-byte config registers the driver reads or writes. They
        # have to exist for the fake to allow reading and overwriting them.
        self.dev.set_single_reg(REG_WHOAMI, 0x33)
        for reg in (
            REG_TEMPCFG,
            REG_CTRL1,
            REG_CTRL3,
            REG_CTRL4,
            REG_CTRL5,
            REG_CLICKCFG,
            REG_CLICKSRC,
            REG_CLICKTHS,
            REG_TIMELIMIT,
            REG_TIMELATENCY,
            REG_TIMEWINDOW,
        ):
            self.dev.set_single_reg(reg, 0x00)

        self._set_accel_data()  # All-zero acceleration and ADC readings
        self._set_adc_data()

    # ------ Test helpers

    def _make_driver(self, **kwargs):
        """Create the driver, then forget the writes the constructor made so tests only see
        the writes from the method they are testing."""
        lis = lis3dh.LIS3DH_I2C(self.i2c, **kwargs)
        self.writes.clear()
        return lis

    def _set_accel_data(self, x=0, y=0, z=0):
        """Load the 6-byte acceleration block from raw signed ints. The LIS3DH outputs each axis
        as a little-endian 16-bit integer (the driver sets BLE to 0 in CTRL4)."""
        data = struct.pack("<hhh", x, y, z)
        self.dev.set_reg_block(REG_OUT_X_L | AUTO_INCREMENT, data)

    def _set_adc_data(self, adc1=0, adc2=0, adc3=0):
        """Load the 6-byte ADC1, ADC2, ADC3 block from raw signed ints (little-endian)."""
        data = struct.pack("<hhh", adc1, adc2, adc3)
        self.dev.set_reg_block(REG_OUTADC1_L | AUTO_INCREMENT, data)

    def _assert_xyz_almost(self, actual, expected, delta=1e-3):
        """Check a 3-item tuple is made of floats almost equal to the `expected` values.
        Avoids potential floating point precision problems in assertions.
        """
        self.assertEqual(len(actual), 3)
        for a, e in zip(actual, expected):
            self.assertAlmostEqual(a, e, delta=delta)

    # ------ Constructor tests

    def test_init_raises_on_wrong_whoami(self):
        """Test that the constructor raises a RuntimeError when the WHO_AM_I register isn't
        0x33, and does it before writing anything to the device."""
        self.dev.set_single_reg(REG_WHOAMI, 0x00)
        with self.assertRaises(RuntimeError):
            lis3dh.LIS3DH_I2C(self.i2c)
        self.assertEqual(self.writes, [])

    def test_init_write_sequence(self):
        """Test that the constructor writes the expected config registers, in order.

        Reboot (CTRL5 0x80), enable XYZ axes (CTRL1 0x07), set 400Hz in the upper nibble of CTRL1
        without losing the axis bits (0x77), high-res + BDU (CTRL4 0x88), enable the ADCs
        (TEMPCFG 0x80) and then latch INT1 (CTRL5 0x08, which also clears the reboot bit).
        """
        lis3dh.LIS3DH_I2C(self.i2c)
        self.assertEqual(
            self.writes,
            [
                (REG_CTRL5, b"\x80"),
                (REG_CTRL1, b"\x07"),
                (REG_CTRL1, b"\x77"),
                (REG_CTRL4, b"\x88"),
                (REG_TEMPCFG, b"\x80"),
                (REG_CTRL5, b"\x08"),
            ],
        )

    # ------ data_rate and range property tests

    def test_data_rate_getter_and_setter(self):
        """Test that ``.data_rate`` reads the upper nibble of CTRL1, and that setting it writes
        the new rate to the upper nibble without touching the lower (axis enable) nibble."""
        lis = self._make_driver()
        self.assertEqual(lis.data_rate, lis3dh.DATARATE_400_HZ)  # Set by the constructor

        self.dev.set_single_reg(REG_CTRL1, 0x9F)  # Lower nibble must not leak into the result
        self.assertEqual(lis.data_rate, 0b1001)

        self.dev.set_single_reg(REG_CTRL1, 0x07)
        lis.data_rate = lis3dh.DATARATE_50_HZ
        self.assertEqual(self.writes, [(REG_CTRL1, b"\x47")])
        self.assertEqual(lis.data_rate, lis3dh.DATARATE_50_HZ)

    def test_range_getter_and_setter(self):
        """Test that ``.range`` reads bits 5:4 of CTRL4, and that setting it only changes those
        bits, keeping the BDU and high-res bits (0x88) the constructor set."""
        lis = self._make_driver()
        self.assertEqual(lis.range, lis3dh.RANGE_2_G)  # CTRL4 = 0x88 after the constructor

        self.dev.set_single_reg(REG_CTRL4, 0xC8)  # BLE and BDU bits set, should be ignored
        self.assertEqual(lis.range, lis3dh.RANGE_2_G)
        self.dev.set_single_reg(REG_CTRL4, 0x98)
        self.assertEqual(lis.range, lis3dh.RANGE_4_G)

        self.dev.set_single_reg(REG_CTRL4, 0x88)
        lis.range = lis3dh.RANGE_16_G
        lis.range = lis3dh.RANGE_4_G  # Going back down has to clear the old bits first
        self.assertEqual(self.writes, [(REG_CTRL4, b"\xb8"), (REG_CTRL4, b"\x98")])

    # ------ acceleration and shake tests

    def test_acceleration_default_range(self):
        """Test that ``.acceleration`` parses the little-endian signed raw values and converts to
        m/s^2 at the default +-2g range (16380 counts per g in the driver).

        The raw values have different high and low bytes (0x3FFC, 0xE002) so a byte order mix-up
        gives very different results, and one of them is negative. Also checks the result is
        a named tuple.
        """
        lis = self._make_driver()
        self._set_accel_data(x=16380, y=-8190, z=0)

        accel = lis.acceleration
        g = lis3dh.STANDARD_GRAVITY
        self._assert_xyz_almost(accel, (g, -g / 2, 0.0))
        self.assertIsInstance(accel, lis3dh.AccelerationTuple)
        self.assertAlmostEqual(accel.x, g, delta=1e-3)  # Named tuple field

    def test_acceleration_divider_follows_range(self):
        """Test that ``.acceleration`` divides by the matching counts-per-g for each range.

        A raw value of one divider is exactly 1g (9.806 m/s^2), so X = 1g, Y = -1g and Z = 2g
        at every range.
        """
        lis = self._make_driver()
        g = lis3dh.STANDARD_GRAVITY
        for range_, divider in RANGE_DIVIDERS:
            lis.range = range_
            self._set_accel_data(x=divider, y=-divider, z=2 * divider)
            self._assert_xyz_almost(lis.acceleration, (g, -g, 2 * g))

    def test_shake_reports_false_when_stationary_and_true_when_above_threshold(self):
        """Test that ``.shake()`` compares the magnitude of the averaged acceleration against
        ``shake_threshold`` (default 30 m/s^2).

        At +-8g (4096 counts per g) resting on a table is 1g on Z = 9.8 m/s^2, so no shake. 4g
        on X is 39.2 m/s^2, which is above the default threshold, but not above a raised one.
        """
        lis = self._make_driver()
        lis.range = lis3dh.RANGE_8_G

        self._set_accel_data(z=4096)
        self.assertFalse(lis.shake(total_delay=0))

        self._set_accel_data(x=16384)
        self.assertTrue(lis.shake(total_delay=0))
        self.assertFalse(lis.shake(shake_threshold=50, total_delay=0))

    # ------ ADC tests

    def test_read_adc_raw_parses_each_channel(self):
        """Test that ``.read_adc_raw()`` reads the matching channel registers (0x88, 0x8A, 0x8C
        including auto-increment bit) and parses them as little-endian signed 16-bit ints."""
        lis = self._make_driver()
        self._set_adc_data(adc1=-2, adc2=0x1234, adc3=-32768)
        self.assertEqual(lis.read_adc_raw(1), -2)
        self.assertEqual(lis.read_adc_raw(2), 0x1234)
        self.assertEqual(lis.read_adc_raw(3), -32768)

    def test_read_adc_raw_raises_on_invalid_channel(self):
        """Test that ``.read_adc_raw()`` raises a ValueError when the ADC isn't 1, 2 or 3."""
        lis = self._make_driver()
        for bad_adc in (-1, 0, 4):
            with self.assertRaises(ValueError):
                lis.read_adc_raw(bad_adc)

    def test_read_adc_mv_linear_interpolation(self):
        """Test that ``.read_adc_mV()`` maps raw -32512 to 1800mV, raw 32512 to 900mV, and
        everything in between linearly (so raw 0 is the midpoint, 1350mV)."""
        lis = self._make_driver()
        for raw, expected_mv in ((-32512, 1800.0), (0, 1350.0), (32512, 900.0)):
            self._set_adc_data(adc2=raw)
            self.assertAlmostEqual(lis.read_adc_mV(2), expected_mv, delta=0.01)

    # ------ tap detection tests

    def test_tapped_reads_click_src_interrupt_flag(self):
        """Test that ``.tapped`` (with no int1 pin) is True only when the IA bit (bit 6, 0x40)
        of CLICK_SRC is set, ignoring the other CLICK_SRC bits."""
        lis = self._make_driver()
        for raw, expected in ((0x00, False), (0x3F, False), (0x40, True), (0x7F, True)):
            self.dev.set_single_reg(REG_CLICKSRC, raw)
            self.assertEqual(lis.tapped, expected, "CLICK_SRC = 0x{:02X}".format(raw))

    def test_set_tap_single_writes_config_registers(self):
        """Test that ``.set_tap(1, ...)`` turns on the INT1 click output in CTRL3 (keeping the
        bits already set), then writes the single-tap config (0x15), the threshold with the
        latch bit set (0x80 | 40), and the default timing values, in that order."""
        lis = self._make_driver()
        self.dev.set_single_reg(REG_CTRL3, 0x10)
        lis.set_tap(1, 40)
        self.assertEqual(
            self.writes,
            [
                (REG_CTRL3, b"\x90"),
                (REG_CLICKCFG, b"\x15"),
                (REG_CLICKTHS, b"\xa8"),
                (REG_TIMELIMIT, b"\x0a"),
                (REG_TIMELATENCY, b"\x14"),
                (REG_TIMEWINDOW, b"\xff"),
            ],
        )

    def test_set_tap_double_with_custom_timing(self):
        """Test that ``.set_tap(2, ...)`` writes the double-tap config (0x2A), and that the
        keyword-only timing arguments are written to their registers (TIMELIMIT, TIMELATENCY,
        TIMEWINDOW) rather than the defaults."""
        lis = self._make_driver()
        lis.set_tap(2, 20, time_limit=5, time_latency=6, time_window=7)
        self.assertEqual(
            self.writes,
            [
                (REG_CTRL3, b"\x80"),
                (REG_CLICKCFG, b"\x2a"),
                (REG_CLICKTHS, b"\x94"),
                (REG_TIMELIMIT, b"\x05"),
                (REG_TIMELATENCY, b"\x06"),
                (REG_TIMEWINDOW, b"\x07"),
            ],
        )

    def test_set_tap_disable_clears_interrupt_and_config(self):
        """Test that ``.set_tap(0, ...)`` turns off the INT1 click output in CTRL3 (keeping the
        other bits), zeroes CLICK_CFG, and then returns without writing the other registers."""
        lis = self._make_driver()
        self.dev.set_single_reg(REG_CTRL3, 0x90)
        lis.set_tap(0, 0)
        self.assertEqual(self.writes, [(REG_CTRL3, b"\x10"), (REG_CLICKCFG, b"\x00")])

    def test_set_tap_custom_click_cfg_overrides_tap_mode(self):
        """Test that a ``click_cfg`` value is written to CLICK_CFG instead of the one picked by
        ``tap``, and that it also lets an otherwise invalid ``tap`` value through."""
        lis = self._make_driver()
        lis.set_tap(1, 40, click_cfg=0x01)
        self.assertIn((REG_CLICKCFG, b"\x01"), self.writes)

        self.writes.clear()
        lis.set_tap(3, 40, click_cfg=0x02)  # Would raise without click_cfg
        self.assertIn((REG_CLICKCFG, b"\x02"), self.writes)

    def test_set_tap_raises_on_invalid_tap_or_threshold(self):
        """Test that ``.set_tap()`` raises a ValueError for a tap mode outside 0-2 (with no
        ``click_cfg``) and a threshold outside 0-127, and writes nothing to the device."""
        lis = self._make_driver()
        for tap, threshold in ((3, 40), (-1, 40), (1, 128), (1, -1)):
            with self.assertRaises(ValueError):
                lis.set_tap(tap, threshold)
        self.assertEqual(self.writes, [])

    # ------ device_check test

    def test_device_check_matches_whoami(self):
        """Test that ``.device_check()`` returns True when WHO_AM_I is 0x33, and False (after
        printing the unknown device ID) when it isn't, such as if the device changed after the
        constructor check."""
        lis = self._make_driver()
        self.assertTrue(lis.device_check())

        self.dev.set_single_reg(REG_WHOAMI, 0x00)
        self.assertFalse(lis.device_check())

    # ------ Fault tests, the driver currently doesn't handle these

    @unittest.expectedFailure
    def test_range_setter_rejects_invalid_value(self):
        """Test that setting ``.range`` to a value outside 0-3 raises a ValueError.

        NOTE - this currently fails as the setter does ``ctl4 |= range_value << 4`` with no
        validation or masking of the input value, so ``range = 4`` quietly sets bit 6 of CTRL4
        which is the BLE (big-endian) bit.

        The chip then outputs big-endian data while ``.acceleration`` still unpacks it as
        little-endian, so every reading afterwards is garbage with no error. Test is marked
        expectedFailure.
        """
        print(
            "Marked expected failure as range setter doesn't validate its input, so range = 4 "
            "sets the BLE (big-endian) bit in CTRL4 and corrupts all later readings."
        )
        lis = self._make_driver()
        with self.assertRaises(ValueError):
            lis.range = 4

    @unittest.expectedFailure
    def test_set_tap_validates_timing_before_writing(self):
        """Test that calling ``.set_tap()`` with an out-of-range ``time_limit`` (or any of the
        time params) raises a ValueError before it has changed any registers.

        NOTE - this currently fails as the timing values aren't validated before being written,
        causing a fail fail when ``bytes([value])`` in the register write helper hits a value
        over 255 which can't be converted by the bytes constructor.

        By then CTRL3, CLICK_CFG and CLICK_THS have already been written, so a ValueError is
        raised but the chip is left half-configured with tap interrupts enabled. Test is marked
        expectedFailure.
        """
        print(
            "Marked expected failure as set_tap() can write CTRL3, CLICK_CFG and CLICK_THS before "
            "an invalid time_limit raises from failing to convert to bytes, leaving the interrupt"
            " half-configured."
        )
        lis = self._make_driver()
        with self.assertRaises(ValueError):
            lis.set_tap(1, 40, time_limit=300)
        self.assertEqual(self.writes, [])

    @unittest.expectedFailure
    def test_tapped_honours_int1_pin_level(self):
        """Test that ``.tapped`` returns False when an int1 pin is given and reads low,
        without trusting CLICK_SRC.

        NOTE - this currently fails as the driver was ported from CircuitPython,
        where ``digitalio`` pins have a ``.value`` property, and checks ``not
        self._int1.value``. But on MicroPython ``machine.Pin.value`` is a method, so it gets
        evaluated as a bound method which is always truthy and the pin check never triggers.
        The pin passed in is ignored. Test is marked as expectedFailure to reflect this.
        """
        print(
            "Marked expected failure as tapped checks int1.value (CircuitPython style "
            "property) rather than calling int1.value() like machine.Pin, so the pin is ignored."
        )
        lis = self._make_driver(int1=fake_machine.Pin(2, value=0))
        self.dev.set_single_reg(REG_CLICKSRC, 0x40)  # Will make the function return true
        tapped = lis.tapped
        self.assertFalse(tapped)  # Expect pin read as 0 causing return False, but falls through


if __name__ == "__main__":
    unittest.main()
