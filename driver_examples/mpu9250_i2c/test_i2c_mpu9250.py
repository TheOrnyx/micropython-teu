"""test_i2c_mpu9250.py

Off-board UNIX tests for the  MPU-9250 driver (mpu9250.py), which is built from the MPU-6500
(mpu6500.py) accelerometer/gyro/temperature driver and the AK8963 (ak8963.py) magnetometer
driver.

These test the register reading/parsing logic of the drivers by using ``fake_machine.I2CDevice``
objects to mimic the MPU (0x68) and the AK8963 (0x0C) on a ``fake_machine.I2C`` bus. Sensor data
is loaded into the fake registers as raw bytes, and the tests check the driver decodes them into
the correct physical values. Writes the drivers make to the devices are captured with the
``memwrite_cb`` callback so the init sequences and config values can be checked too.

The last section contains a few tests that simulate faulty input/ hardware conditions the drivers
currently don't handle. These are marked ``expectedFailure`` (like the modem driver test) and
will start reporting "unexpected success" once the driver is hardened, at which point the
decorator can be removed.

AI tools were used to help with creating input data and some calculation logic due to time
constraints preventing in-depth research, all outputs were manually checked and validated
before committing.

Manuals:
https://cdn.sparkfun.com/assets/learn_tutorials/5/5/0/MPU-9250-Register-Map.pdf
https://www.mouser.com/datasheet/2/400/PS-MPU-9250A-01-v1.1-1313803.pdf
"""

import math
import struct
import unittest
import teu
from teu import fake_machine

# Shadow the builtin machine module so the drivers' `from machine import I2C, Pin` gets the fakes
teu.shadow_builtins()

from . import mpu6500
from . import ak8963
from . import mpu9250
from .mpu9250 import MPU9250

MPU_ADDR = 0x68  # Default MPU-6500 address
AK_ADDR = 0x0C  # Default AK8963 address (reached via the MPU's I2C bypass)

# MPU registers the tests touch directly.
# Values copied from driver since can't reference the private members for some reason.
MPU_GYRO_CONFIG = 0x1B
MPU_ACCEL_CONFIG = 0x1C
MPU_INT_PIN_CFG = 0x37
MPU_DATA_START = 0x3B  # ACCEL_XOUT_H, then 14 sequential bytes up to GYRO_ZOUT_L (0x48)
MPU_PWR_MGMT_1 = 0x6B
MPU_WHO_AM_I = 0x75

# AK8963 registers the tests touch directly
AK_WIA = 0x00
AK_DATA_START = 0x03  # HXL, then 6 data bytes (0x03-0x08), followed directly by ST2 at 0x09
AK_CNTL1 = 0x0A
AK_ASAX = 0x10  # ASAX, ASAY, ASAZ sensitivity adjustment values at 0x10-0x12

AK_ST2_HOFL = 0x08  # Magnetic sensor overflow bit in ST2


class TestMPU9250WithFake(unittest.TestCase):
    """Test class for the MPU-9250, MPU-6500 and AK8963 drivers using ``fake_machine.I2C`` and
    two ``fake_machine.I2CDevice``s to mimic the hardware."""

    def setUp(self):
        """Create the bus and both devices, initialize and fill them with sane default
        registers for the readings and config regs, and start recording writes.

        The drivers are created inside each test since their constructors read/write registers
        and several tests need different constructor arguments."""
        fake_machine.I2C.reset_registry()
        self.addCleanup(fake_machine.I2C.reset_registry)

        self.i2c = fake_machine.I2C(0)
        self.mpu_dev = fake_machine.I2CDevice(MPU_ADDR, self.i2c)
        self.ak_dev = fake_machine.I2CDevice(AK_ADDR, self.i2c)

        # Record tuple of (memaddr, data) for every register write.
        # So tests can assert that specific register writes took place.
        self.mpu_writes = []
        self.ak_writes = []
        self.mpu_dev.set_write_callbacks(
            memwrite_cb=lambda dev, reg, buf: self.mpu_writes.append((reg, bytes(buf)))
        )
        self.ak_dev.set_write_callbacks(
            memwrite_cb=lambda dev, reg, buf: self.ak_writes.append((reg, bytes(buf)))
        )

        # Defaults that let every driver construct successfully, and all-zero sensor data.
        # Needed since the __init__ writes and reads from the registers for the initial config.
        self.mpu_dev.set_single_reg(MPU_WHO_AM_I, 0x70)
        self.mpu_dev.set_single_reg(MPU_INT_PIN_CFG, 0x00)
        self._set_mpu_data()  # Init the MPU readings and ST2 registers

        # Set AK device ID and initial magnetometer values
        self.ak_dev.set_single_reg(AK_WIA, 0x48)  # Device ID
        self.ak_dev.set_reg_block(AK_ASAX, bytes((128, 128, 128)))  # 128 = no adjustment (1.0)
        self._set_mag_data()  # Init the MAG readings registers

    # ------ Test helpers

    def _set_mpu_data(self, accel=(0, 0, 0), temp=0, gyro=(0, 0, 0)):
        """Load the 14-byte MPU data block (accel XYZ, temp, gyro XYZ) from raw signed ints.
        The MPU-6500 outputs each value as a big-endian 16-bit integer."""
        data = struct.pack(
            ">hhhhhhh", accel[0], accel[1], accel[2], temp, gyro[0], gyro[1], gyro[2]
        )
        self.mpu_dev.set_reg_block(MPU_DATA_START, data)

    def _set_mag_data(self, xyz=(0, 0, 0), st2=0):
        """Load the AK8963 data registers from raw signed ints, plus the ST2 register that the
        driver reads straight after. The AK8963 outputs little-endian 16-bit values, opposite to
        the MPU."""
        data = struct.pack("<hhh", xyz[0], xyz[1], xyz[2]) + bytes((st2,))
        self.ak_dev.set_reg_block(AK_DATA_START, data)

    def _assert_xyz_almost(self, actual, expected, delta=1e-4):
        """Check a 3-item tuple is made of floats almost equal to the `expected` values.
        Avoids potential floating point precision problems in assertions.
        """
        self.assertEqual(len(actual), 3)
        for a, e in zip(actual, expected):
            self.assertAlmostEqual(a, e, delta=delta)

    # ------ MPU6500 constructor tests

    def test_mpu6500_init_resets_then_wakes_device(self):
        """Test that the ``MPU6500`` constructor resets the chip (0x80 to PWR_MGMT_1) and then
        clears the sleep bit (0x00), in that order."""
        mpu6500.MPU6500(self.i2c)
        pwr_writes = [w for w in self.mpu_writes if w[0] == MPU_PWR_MGMT_1]
        self.assertEqual(pwr_writes, [(MPU_PWR_MGMT_1, b"\x80"), (MPU_PWR_MGMT_1, b"\x00")])

    def test_mpu6500_accepts_known_whoami_values(self):
        """Test that the ``MPU6500`` constructor accepts each WHO_AM_I value it lists (MPU6500,
        MPU6250 SIP and MPU6700) and that ``.whoami`` returns the register value."""
        for who in (0x70, 0x71, 0x90):
            self.mpu_dev.set_single_reg(MPU_WHO_AM_I, who)
            self.assertEqual(mpu6500.MPU6500(self.i2c).whoami, who)

    def test_mpu6500_raises_on_unknown_whoami(self):
        """Test that the ``MPU6500`` constructor raises a RuntimeError when WHO_AM_I isn't a
        known ID, and does it before writing anything to the device."""
        self.mpu_dev.set_single_reg(MPU_WHO_AM_I, 0xFF)
        with self.assertRaises(RuntimeError):
            mpu6500.MPU6500(self.i2c)
        self.assertEqual(self.mpu_writes, [])

    def test_mpu6500_full_scale_selection_sets_config_and_scaling(self):
        """Test that choosing a non-default full-scale range writes the matching value to the
        ACCEL_CONFIG/GYRO_CONFIG registers and that readings use the matching sensitivity.

        At +-8g there are 4096 LSB/g, at +-1000dps there are 32.8 LSB/(deg/s).

        Tests that the provided accel and gyro arguments are written to the device and also are
        used for the output calculations.
        """
        mpu = mpu6500.MPU6500(
            self.i2c,
            accel_fs=mpu6500.ACCEL_FS_SEL_8G,
            gyro_fs=mpu6500.GYRO_FS_SEL_1000DPS,
            accel_sf=mpu6500.SF_G,
            gyro_sf=mpu6500.SF_DEG_S,
        )
        self.assertIn((MPU_ACCEL_CONFIG, b"\x10"), self.mpu_writes)
        self.assertIn((MPU_GYRO_CONFIG, b"\x10"), self.mpu_writes)

        self._set_mpu_data(accel=(4096, 2048, -4096), gyro=(328, -164, 0))
        self._assert_xyz_almost(mpu.acceleration, (1.0, 0.5, -1.0))
        self._assert_xyz_almost(mpu.gyro, (10.0, -5.0, 0.0))

    # ------ MPU6500 reading tests

    def test_mpu6500_acceleration_default_units(self):
        """Test that ``.acceleration`` parses the big-endian signed raw values and converts to
        m/s^2 by default (16384 LSB/g at the default +-2g range).

        The raw values have different high and low bytes (0x4000, 0xE000) so a byte order mix-up
        gives very different results.
        """
        mpu = mpu6500.MPU6500(self.i2c)
        self._set_mpu_data(accel=(16384, -8192, 0))
        self._assert_xyz_almost(mpu.acceleration, (9.80665, -4.903325, 0.0))

    def test_mpu6500_gyro_default_units(self):
        """Test that ``.gyro`` parses the raw values and converts to rad/s by default (131
        LSB/(deg/s) at the default +-250dps range), including negative values."""
        mpu = mpu6500.MPU6500(self.i2c)
        self._set_mpu_data(gyro=(131, -262, 1310))  # 1, -2 and 10 deg/s
        self._assert_xyz_almost(mpu.gyro, (math.radians(1), math.radians(-2), math.radians(10)))

    def test_mpu6500_temperature_parsing(self):
        """Test that ``.temperature`` converts the raw reading using 333.87 LSB/degC.

        Raw value of 3360 gives ~31.0 degC with the driver's formula, which removes the 21 LSB
        offset from the raw value, then divides, then adds 21 degC back.
        """
        mpu = mpu6500.MPU6500(self.i2c)
        self._set_mpu_data(temp=3360)
        self.assertAlmostEqual(mpu.temperature, 31.0, delta=0.01)

    def test_mpu6500_calibrate_discards_old_offset_and_returns_gyro_average(self):
        """Test that ``.calibrate()`` throws away any existing offset, averages the gyro
        readings and stores the result so that a following ``.gyro`` read is ~zero.

        The fake registers are static, so every sample is identical and the average must equal
        the reading. A garbage offset is passed to the constructor to check it doesn't leak
        into the calibration.
        """
        mpu = mpu6500.MPU6500(self.i2c, gyro_offset=(1.0, 1.0, 1.0))
        self._set_mpu_data(gyro=(131, -262, 1310))  # 1, -2 and 10 deg/s
        expected = (math.radians(1), math.radians(-2), math.radians(10))

        offset = mpu.calibrate(count=4, delay=0)
        self._assert_xyz_almost(offset, expected)
        self._assert_xyz_almost(mpu.gyro, (0.0, 0.0, 0.0))

    # ------ AK8963 constructor tests

    def test_ak8963_raises_on_unknown_whoami(self):
        """Test that the ``AK8963`` constructor raises a RuntimeError if the WIA register isn't
        0x48, and does so before writing to the device."""
        self.ak_dev.set_single_reg(AK_WIA, 0x00)
        with self.assertRaises(RuntimeError):
            ak8963.AK8963(self.i2c)
        self.assertEqual(self.ak_writes, [])

    def test_ak8963_init_mode_sequence(self):
        """Test that the ``AK8963`` constructor goes fuse-ROM mode (0x0F) to read the ASA
        values, then power-down (0x00), then into the final mode (continuous 8Hz + 16-bit =
        0x12), as the datasheet requires mode changes to go via power-down."""
        ak8963.AK8963(self.i2c)
        self.assertEqual(
            self.ak_writes,
            [(AK_CNTL1, b"\x0f"), (AK_CNTL1, b"\x00"), (AK_CNTL1, b"\x12")],
        )

    def test_ak8963_sensitivity_adjustment_from_asa_registers(self):
        """Test that ``.adjustement`` is calculated from the factory ASA registers using
        ``0.5 * (ASA - 128) / 128 + 1``, e.g. 192 gives 1.25, 64 gives 0.75, 128 gives 1.0."""
        self.ak_dev.set_reg_block(AK_ASAX, bytes((192, 64, 128)))
        mag = ak8963.AK8963(self.i2c)
        self._assert_xyz_almost(mag.adjustement, (1.25, 0.75, 1.0))

    # ------ AK8963 reading tests

    def test_ak8963_magnetic_16bit_applies_adjustment(self):
        """Test that ``.magnetic`` parses the little-endian raw values, applies the ASA
        adjustment for each axis, and scales by 0.15uT per digit in 16-bit mode.

        X = 1000 * 1.25 * 0.15, Y = -2000 * 0.75 * 0.15, Z = 400 * 1.0 * 0.15
        """
        self.ak_dev.set_reg_block(AK_ASAX, bytes((192, 64, 128)))
        mag = ak8963.AK8963(self.i2c)
        self._set_mag_data((1000, -2000, 400))
        self._assert_xyz_almost(mag.magnetic, (187.5, -225.0, 60.0))

    def test_ak8963_magnetic_14bit_scale(self):
        """Test that ``output=OUTPUT_14_BIT`` uses 0.6uT per digit, and that the mode written
        to CNTL1 has the 16-bit output bit cleared (0x02), so only mode was written."""
        mag = ak8963.AK8963(self.i2c, output=ak8963.OUTPUT_14_BIT)
        self.assertEqual(self.ak_writes[-1], (AK_CNTL1, b"\x02"))

        self._set_mag_data((100, -50, 10))
        self._assert_xyz_almost(mag.magnetic, (60.0, -30.0, 6.0))

    def test_ak8963_magnetic_applies_offset_before_scale(self):
        """Test that the hard iron ``offset`` is subtracted first and the soft iron ``scale`` is
        multiplied in after, and not the other way around.

        Adjusted values are (187.5, -225.0, 60.0) so the result is
        ((187.5 - 10) * 2, (-225 + 25) * 1, (60 - 0) * 0.5).
        """
        self.ak_dev.set_reg_block(AK_ASAX, bytes((192, 64, 128)))
        mag = ak8963.AK8963(self.i2c, offset=(10, -25, 0), scale=(2, 1, 0.5))
        self._set_mag_data((1000, -2000, 400))
        self._assert_xyz_almost(mag.magnetic, (355.0, -200.0, 30.0))

    def test_ak8963_calibrate_computes_hard_and_soft_iron_corrections(self):
        """Test that ``.calibrate()`` returns the midpoint of each axis range as the offset, and
        the soft iron scale as the average half-range divided by each axis half-range.

        The fake registers are static but calibration needs a changing field, so the driver's
        6-byte data read function is swapped for an iterator of raw samples.

        With count=2 calibrate takes 3 samples (1 initial + 2 in the loop). Raw values are
        converted at 0.15uT/digit, giving ranges of X -30..60, Y -15..45 and Z -60..30 uT. So
        offsets are 15, 15, -15 and the half-ranges are 45, 30, 45 (average 40), so the scales
        are 40/45, 40/30, 40/45.
        """
        mag = ak8963.AK8963(self.i2c)
        samples = iter([(400, 100, -400), (-200, 300, 0), (100, -100, 200)])
        mag._register_three_shorts = lambda register: next(samples)

        offset, scale = mag.calibrate(count=2, delay=0)
        self._assert_xyz_almost(offset, (15.0, 15.0, -15.0))
        self._assert_xyz_almost(scale, (40 / 45, 40 / 30, 40 / 45))

    # ------ MPU9250 tests

    def test_mpu9250_init_enables_i2c_bypass_keeping_other_bits(self):
        """Test that the ``MPU9250`` constructor sets the I2C bypass bit (bit 1) in INT_PIN_CFG
        so the AK8963 is reachable, without clearing the other bits that were already set.

        Starting value 0x30 gets OR'd with 0x2 (bypass bit) and gives 0x32.
        """
        self.mpu_dev.set_single_reg(MPU_INT_PIN_CFG, 0x30)
        MPU9250(self.i2c)
        cfg_writes = [w for w in self.mpu_writes if w[0] == MPU_INT_PIN_CFG]
        self.assertEqual(cfg_writes, [(MPU_INT_PIN_CFG, b"\x32")])

    def test_mpu9250_raises_oserror_when_ak8963_missing(self):
        """Test that ``MPU9250`` lets the bus OSError through when the magnetometer doesn't
        answer, rather than carrying on without it."""
        del self.i2c.devices[AK_ADDR]  # Unplug the AK8963 from the fake bus
        with self.assertRaises(OSError):
            MPU9250(self.i2c)

    def test_mpu9250_properties_delegate_to_sub_drivers(self):
        """Test that each ``MPU9250`` property returns the value from the matching sub-driver:
        acceleration/gyro/temperature/whoami from the MPU6500, magnetic from the AK8963."""
        imu = MPU9250(self.i2c)
        self._set_mpu_data(accel=(16384, 0, 0), temp=3360, gyro=(131, 0, 0))
        self._set_mag_data((1000, 0, 0))

        self._assert_xyz_almost(imu.acceleration, (9.80665, 0.0, 0.0))
        self._assert_xyz_almost(imu.gyro, (math.radians(1), 0.0, 0.0))
        self.assertAlmostEqual(imu.temperature, 31.0, delta=0.01)
        self._assert_xyz_almost(imu.magnetic, (150.0, 0.0, 0.0))  # 1000 * 1.0 * 0.15
        self.assertEqual(imu.whoami, 0x70)

    # ------ Fault tests, the drivers currently don't handle these

    @unittest.expectedFailure
    def test_mpu6500_rejects_invalid_full_scale_selection(self):
        """Test that an invalid ``accel_fs`` raises a ValueError straight away.

        NOTE - this currently fails as ``_accel_fs()`` (and ``_gyro_fs()``) only return a
        sensitivity for the 4 known values, so anything else returns None. The constructor
        still writes the bad value to the chip and stores ``_accel_so = None``, meaning the
        first ``.acceleration`` read dies with a confusing TypeError (``value / None``) much
        later than the actual mistake. Test is marked expectedFailure.
        """
        print(
            "Marked expected failure as MPU6500 constructor doesn't handle unknown accel_fs "
            "values and returns None, meaning a later call to .acceleration will raise "
            "TypeError at division."
        )
        with self.assertRaises(ValueError):
            mpu6500.MPU6500(self.i2c, accel_fs=0b00100000)

    @unittest.expectedFailure
    def test_ak8963_calibrate_survives_axis_with_no_variation(self):
        """Test that ``AK8963.calibrate()`` copes when an axis never changes, like a stuck
        sensor, a dead axis, or the board not being rotated during calibration.

        NOTE - this currently fails with a ZeroDivisionError as the soft iron scale divides
        the average half-range by each axis half-range (``avg_delta / avg_delta_x``), which is
        0 when the readings on that axis are all the same. The static fake registers give
        exactly this case. Test is marked expectedFailure.
        """
        print(
            "Marked expected failure as the calibrate method doesn't protect against "
            "DivideByZero errors when readings are 0."
        )

        mag = ak8963.AK8963(self.i2c)
        offset, scale = mag.calibrate(count=3, delay=0)
        self.assertEqual(len(offset), 3)
        self.assertEqual(len(scale), 3)

    @unittest.expectedFailure
    def test_ak8963_magnetic_flags_sensor_overflow(self):
        """Test that ``.magnetic`` doesn't quietly return data when the AK8963 reports the
        magnetic sensor overflowed.

        NOTE - this currently fails as the driver reads ST2 only to release the data latch and
        throws away the HOFL bit, which if 1 means the magnetic sensor has overflowed and data
        read is invalid and should be discarded. The driver doesn't handle the readings being
        invalid.

        A RuntimeError is assumed here to match the constructor validation, but real
        implementation could do something else (like return None). Test is marked expectedFailure.
        """
        print(
            "Marked expected failure as driver has no handling of ST2 HOFL magnetic overflow "
            "bit being 1, which specifies that data is invalid and should be discarded."
        )
        mag = ak8963.AK8963(self.i2c)
        self._set_mag_data((1000, -2000, 400), st2=AK_ST2_HOFL)
        with self.assertRaises(RuntimeError):
            _ = mag.magnetic

    @unittest.expectedFailure
    def test_mpu6500_gyro_sensitivity_matches_datasheet_for_every_range(self):
        """Test that the gyro uses the datasheet sensitivity at each full-scale range (131,
        65.5, 32.8 and 16.4 LSB/(deg/s)), by feeding in a raw value worth 10 deg/s at each one.

        NOTE - this currently fails at +-500dps as the driver has ``_GYRO_SO_500DPS = 62.5``
        instead of 65.5 (each range halves the sensitivity: 131 / 2 = 65.5), so every 500dps
        reading comes out ~5% too high (10.48 instead of 10.0). Test is marked expectedFailure.

        Might not be the most accurate as I'm pretty sure readings can be a bit variable anyway
        but just a difference that was noticed.
        """
        print(
            "Marked expected failure as driver has invalid SO value for 500DPS, datasheet "
            "specifies 65.5 (half of 131), but driver has 62.5. So invalid reading at +-500dps."
        )
        ranges = (
            (mpu6500.GYRO_FS_SEL_250DPS, 131),
            (mpu6500.GYRO_FS_SEL_500DPS, 65.5),
            (mpu6500.GYRO_FS_SEL_1000DPS, 32.8),
            (mpu6500.GYRO_FS_SEL_2000DPS, 16.4),
        )
        for fs_sel, lsb_per_dps in ranges:
            mpu = mpu6500.MPU6500(self.i2c, gyro_fs=fs_sel, gyro_sf=mpu6500.SF_DEG_S)
            raw = round(lsb_per_dps * 10)
            self._set_mpu_data(gyro=(raw, -raw, 0))
            self._assert_xyz_almost(mpu.gyro, (10.0, -10.0, 0.0), delta=0.01)

    @unittest.expectedFailure
    def test_ak8963_single_measure_mode_is_triggered_on_each_read(self):
        """Test that with ``MODE_SINGLE_MEASURE`` the driver writes the mode to CNTL1 again to
        trigger a new measurement when ``.magnetic`` is read (0x01 mode | 0x10 16-bit = 0x11).

        NOTE - this currently fails. In single measurement mode the AK8963 reads a single
        sample and then drops back to power-down by itself, so a new measurement needs CNTL1
        writing again each time, otherwise the same data will be read.

        The driver only writes it in the constructor, meaning every read after the first
        returns the same stale sample, and no util methods to request a new reading. Test is
        marked expectedFailure.
        """
        print(
            "Marked expected failure as driver supports SINGLE_MEASURE mode but doesn't write "
            "the mode to CNTL1 on each read. So every read in this mode will return same value."
        )
        mag = ak8963.AK8963(self.i2c, mode=ak8963.MODE_SINGLE_MEASURE)
        self.ak_writes.clear()  # Ignore the writes made by the constructor
        _ = mag.magnetic
        _ = mag.magnetic
        self.assertIn((AK_CNTL1, b"\x11"), self.ak_writes)


if __name__ == "__main__":
    unittest.main()
