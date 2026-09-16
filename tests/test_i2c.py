"""test_i2c.py - Tests for the fake I2C bus and I2CDevice implementations.

Tests the expected functionality and brief features of the implementations, to prevent bugs and
ensure they work.
"""

import unittest
from teu import fake_machine
from teu.fake_machine.i2c import I2CDevice

# pylint: disable=protected-access, invalid-name

TEST_ADDR = 0x08  # Address for our test device

DEFAULT_FREQ = 400000
DEFAULT_TIMEOUT = 50000


class TestI2CFunctionality(unittest.TestCase):
    """Test the functionality and features of the ``fake_machine.I2CDevice``."""

    def setUp(self):
        # Clean-up registry to avoid leaking
        fake_machine.I2C.reset_registry()
        self.addCleanup(fake_machine.reset_registries)

        # Create bus and device and register to avoid boilerplate at start of each test
        self.i2c = fake_machine.I2C(0)
        self.device = fake_machine.I2CDevice(TEST_ADDR, self.i2c)

    def test_device_added_to_bus(self):
        """Test that the I2CDevice got added to the bus correctly"""
        # Test the device created in setUp one first
        self.assertEqual(1, len(self.i2c.devices))
        self.assertEqual([TEST_ADDR], self.i2c.scan())
        self.assertIs(self.device, list(self.i2c.devices.values())[0])

        # Test adding another device
        device2 = fake_machine.I2CDevice(0x09, self.i2c)
        self.assertEqual(2, len(self.i2c.devices))
        self.assertEqual([TEST_ADDR, 0x09], sorted(self.i2c.scan()))  # Sorted for order
        self.assertEqual([self.device, device2], list(self.i2c.devices.values()))

    def test_adding_same_addr_raises(self):
        """Test that attempting to add a device with the same address as another registered
        device raises a ValueError"""
        with self.assertRaises(ValueError):
            device2 = fake_machine.I2CDevice(TEST_ADDR, self.i2c)

    def test_out_of_range_addr_raises(self):
        """Test that creating an I2CDevice with an address outside of the accepted value range
        of [0x08, 0x77] raises a ValueError.
        """
        with self.assertRaises(ValueError):
            fake_machine.I2CDevice(0x07, self.i2c)

        # 0x77 is in range so should pass
        fake_machine.I2CDevice(0x77, self.i2c)

        with self.assertRaises(ValueError):
            fake_machine.I2CDevice(0x78, self.i2c)

    def test_accessing_unknown_device_raises(self):
        """Test that attempting to read or write to an unknown device raises an OsError."""
        with self.assertRaises(OSError):
            self.i2c.readfrom_into(0x09, bytearray())

        with self.assertRaises(OSError):
            self.i2c.writeto(0x09, bytearray())

    def test_set_reg_block(self):
        """Test that setting a register block with `set_reg_block()` works properly."""
        start_reg = 0x2
        expected = b"\x01\x02\x03\x04\x05"
        self.device.set_reg_block(start_reg, expected)

        self.assertEqual(len(self.device.registers), 5)

        for i, b in enumerate(expected):
            index = start_reg + i
            self.assertIn(index, self.device.registers)
            self.assertEqual(self.device.registers[index], bytes((b,)))

    def test_basic_device_memory_read(self):
        """Test that we can set up a basic I2CDevice with a register block that we can read
        from."""
        self.assertEqual([TEST_ADDR], self.i2c.scan())
        expected = b"\x05\x04\x03\x02\x01"  # Reversed to shake things up
        self.device.set_reg_block(0x5, expected)

        # Sequential access from start
        result = self.i2c.readfrom_mem(TEST_ADDR, 0x5, 5)
        self.assertEqual(result, expected)

        # Read from middle
        result = self.i2c.readfrom_mem(TEST_ADDR, 0x8, 2)
        self.assertEqual(result, b"\x02\x01")

        # Read single
        result = self.i2c.readfrom_mem(TEST_ADDR, 0x7, 1)
        self.assertEqual(result, b"\x03")

        # Full read with readfrom_mem_into
        res = bytearray(5)
        self.i2c.readfrom_mem_into(TEST_ADDR, 0x5, res)
        self.assertEqual(res, expected)

    def test_device_memory_read_with_differing_reg_sizes(self):
        """Test that reading the registers of an I2CDevice works properly with varying sized
        registers.

        If we have a bank of registers with byte lengths [2, 2, 1] and we read 5 bytes that
        should read from all 3.
        """
        start_addr = 0x3
        dat1, dat2, dat3 = (b"\x01\x02", b"\x03\x04", b"\x05")
        self.device.set_reg_list(start_addr, [dat1, dat2, dat3])

        # Full read
        self.assertEqual(self.i2c.readfrom_mem(TEST_ADDR, start_addr, 5), dat1 + dat2 + dat3)

        # Read first register
        self.assertEqual(self.i2c.readfrom_mem(TEST_ADDR, start_addr, 2), dat1)

        # Read first 3 bytes (first reg and half of second)
        #
        # NOTE - this functionality might change as currently we raise when overwriting and
        #  only writing part of a register, but not sure if should be the same for reading.
        self.assertEqual(self.i2c.readfrom_mem(TEST_ADDR, start_addr, 3), b"\x01\x02\x03")

    def test_out_of_range_reg_reads_raise(self):
        """Test that the I2CDevice raises correctly when reading from non-existent registers,
        either randomly or sequentially by requesting more bytes than stored."""
        data = b"\x01\x02\x03\x04\x05"
        self.device.set_reg_block(0x4, data)

        # Check normal read is fine
        result = self.i2c.readfrom_mem(TEST_ADDR, 0x4, len(data))
        self.assertEqual(result, data)

        # Check raises when sequential read where we request 6 bytes but data reg block only has
        # 5 bytes available.
        with self.assertRaises(ValueError):
            self.i2c.readfrom_mem(TEST_ADDR, 0x4, 6)

        # Check raises KeyError when trying to read from register than doesn't exist
        with self.assertRaises(KeyError):
            self.i2c.readfrom_mem(TEST_ADDR, 0xF, 1)

    def test_non_register_read(self):
        """Test that we can set a non-register read on an I2CDevice."""
        expected = b"expect"
        self.device.set_read_response(expected)
        self.assertEqual(self.device.read_response, expected)

        # Regular
        result = self.i2c.readfrom(TEST_ADDR, 6)
        self.assertEqual(result, expected)

        # Get part
        result = self.i2c.readfrom(TEST_ADDR, 3)
        self.assertEqual(result, expected[:3])

    def test_non_register_read_raises_when_not_enough_data(self):
        """Test that a read on a non-register-based device raises an exception when the number
        of bytes requested is larger than available."""
        self.device.set_read_response(b"\x01\x02\x03")

        with self.assertRaises(ValueError):
            self.i2c.readfrom(TEST_ADDR, 8)

    def test_regular_write_callback(self):
        """Test that the I2CDevice basic write callback works properly"""
        written_data = bytearray()
        used_device: I2CDevice | None = None

        def write_cb(device: I2CDevice, data):
            # Callback for write, could also modify device here
            nonlocal written_data, used_device
            written_data[:] = data
            used_device = device

        self.device.set_write_callbacks(write_cb=write_cb)
        expected = b"\x01\x02\x03\x04"

        # Regular write
        self.i2c.writeto(TEST_ADDR, expected)
        self.assertEqual(written_data, expected)
        self.assertIs(used_device, self.device)

        # Writing a vector with writevto
        written_data = bytearray()
        used_device = None
        expected = b"\x01\x02\x03\x04\x05\x06"
        vector = [expected[:3], expected[3:5], expected[5:6]]
        self.i2c.writevto(TEST_ADDR, vector)
        self.assertEqual(written_data, expected)
        self.assertIs(used_device, self.device)

    def test_response_modifying_write_callback(self):
        """Small test/ example to check that a write callback could set a read_response."""
        new_response = b"respondin"

        def write_cb(device: I2CDevice, data):
            nonlocal new_response
            device.set_read_response(new_response)

        self.device.set_write_callbacks(write_cb=write_cb)
        self.i2c.writeto(TEST_ADDR, b"NA")
        self.assertEqual(self.device.read_response, new_response)
        self.assertEqual(self.i2c.readfrom(TEST_ADDR, len(new_response)), new_response)

    def test_echoing_write_callback(self):
        """Test that a basic echoing write callback works, another example like above."""
        # Can use lambda instead of defining a function (but python lambdas suck unfortunately)
        self.device.set_write_callbacks(write_cb=(lambda dev, dat: dev.set_read_response(dat)))

        expected = b"\x01\x02\x04\x05\x06"
        self.i2c.writeto(TEST_ADDR, expected)
        self.assertEqual(self.i2c.readfrom(TEST_ADDR, len(expected)), expected)

        # Check it changes with another write
        expected = b"response2"
        self.i2c.writeto(TEST_ADDR, expected)
        self.assertEqual(self.i2c.readfrom(TEST_ADDR, len(expected)), expected)

    def test_regular_mem_write_callback(self):
        """Test that a write callback for the writeto_mem works."""
        written_data = bytearray()
        used_addr = 0

        def memwrite_cb(device: I2CDevice, memaddr, data):
            nonlocal written_data, used_addr
            written_data[:] = data
            used_addr = memaddr

        self.device.set_write_callbacks(memwrite_cb=memwrite_cb)
        expected = b"\x01\x02\x03\x04\x05\x04"

        # Regular write
        self.i2c.writeto_mem(TEST_ADDR, 0x2, expected)
        self.assertEqual(written_data, expected)
        self.assertEqual(used_addr, 0x2)

    def test_mem_write_with_overwrite(self):
        """Test basics of overwriting register values with a writeto_mem."""
        start_data = b"\x01\x02\x03\x04\x05"
        base_memaddr = 0x3
        self.device.set_reg_block(base_memaddr, start_data)
        self.device.allow_register_overwriting()
        self.assertEqual(
            self.i2c.readfrom_mem(TEST_ADDR, base_memaddr, len(start_data)), start_data
        )

        # Replacing whole block
        new_data = b"house"
        self.i2c.writeto_mem(TEST_ADDR, base_memaddr, new_data)
        self.assertEqual(self.i2c.readfrom_mem(TEST_ADDR, base_memaddr, len(new_data)), new_data)

        # Replacing part of block (first 3 bytes to become "moose")
        self.i2c.writeto_mem(TEST_ADDR, base_memaddr, b"moo")
        self.assertEqual(self.i2c.readfrom_mem(TEST_ADDR, base_memaddr, len(new_data)), b"moose")

        # Replacing end of block (last 2 bytes to become "moon!")
        self.i2c.writeto_mem(TEST_ADDR, base_memaddr + 3, b"n!")
        self.assertEqual(self.i2c.readfrom_mem(TEST_ADDR, base_memaddr, len(new_data)), b"moon!")

    def test_mem_write_with_overwrite_raises_on_too_much_data(self):
        """Test that the writeto_mem with register overwriting raises a ValueError if
        attempting to write more bytes than is available in the bank of registers."""
        reg_data = b"\x01\x02\x03\x04\x05"
        bad_data = b"\x07\x06\x05\x04\x03\x02\x01"
        base_memaddr = 0x3
        self.device.set_reg_block(base_memaddr, reg_data)
        self.device.allow_register_overwriting()

        with self.assertRaises(ValueError):
            self.i2c.writeto_mem(TEST_ADDR, base_memaddr, bad_data)

    def test_mem_write_with_overwrite_raises_on_not_enough_data(self):
        """Test that a writeto_mem call with register overwriting raises a ValueError if buf
        runs out of data while the current register isn't fully written.

        Basically if we run out of buf data on a 2-byte register where one byte has been
        written but we don't have enough data to write the second byte.
        """
        # Set an initial block of 1-byte registers (cuz want to test transaction)
        start_data = b"\x01\x02\x03\x04"
        start_memaddr = 0x3
        self.device.set_reg_block(start_memaddr, start_data)

        # Add a 3-byte final register
        reg_addr = start_memaddr + len(start_data)
        self.device.set_single_reg(reg_addr, b"\x05\x06\x07")

        self.device.allow_register_overwriting()
        bad_data = b"\x01\x02\x03\x04\x05"  # Only fills 1/3 bytes of final reg
        with self.assertRaises(ValueError):
            self.i2c.writeto_mem(TEST_ADDR, start_memaddr, bad_data)

    def test_multiton_returns_same(self):
        """Test that the multiton works for I2C and when another I2C is created with the same
        ID it returns the same object."""
        # Bus at id=0 already defined.
        self.assertEqual(len(fake_machine.I2C._I2C_REGISTRY), 1)

        i2c2 = fake_machine.I2C()  # No args should default to ID=0
        self.assertIs(i2c2, self.i2c)

        i2c3 = fake_machine.I2C(1)
        self.assertIsNot(i2c3, self.i2c)
        i2c4 = fake_machine.I2C(1)
        self.assertIs(i2c4, i2c3)
        self.assertEqual(len(fake_machine.I2C._I2C_REGISTRY), 2)

    def test_allowed_ids(self):
        """Test that only 0 and 1 are allowed IDs for I2C, others should raise"""
        # ID=0 and ID=1 should pass (ID=0 already tested by every other test)
        bus2 = fake_machine.I2C(1)

        # ID = 2 will fail
        with self.assertRaises(ValueError):
            fake_machine.I2C(2)

    def test_default_pin_assignment(self):
        """Test that when the I2C buses are created they get assigned the default Pins.

        * ID_0 = (18, 19)
        * ID_! = (25, 26)
        """
        # ID=0 already defined but creating again to make sure reinit doesn't break anything
        id0_scl, id0_sda = fake_machine.Pin(18), fake_machine.Pin(19)
        id1_scl, id1_sda = fake_machine.Pin(25), fake_machine.Pin(26)

        bus0 = fake_machine.I2C()
        self.assertIs(bus0.scl, id0_scl)
        self.assertIs(bus0.sda, id0_sda)

        bus1 = fake_machine.I2C(1)
        self.assertIs(bus1.scl, id1_scl)
        self.assertIs(bus1.sda, id1_sda)

    def test_default_freq_timeout_vals(self):
        """Test the default values for freq and timeout are set."""
        bus = fake_machine.I2C(1)
        self.assertEqual(bus.freq, DEFAULT_FREQ)
        self.assertEqual(bus.timeout, DEFAULT_TIMEOUT)

    def test_bus_reinit_only_sets_provided_args(self):
        """Test that I2C instances that get reinitialized with the constructor only update the
        provided args."""
        new_freq, new_timeout = 300000, 40000
        bus = fake_machine.I2C(1)  # Previous test tests default vals so can skip

        # Freq
        fake_machine.I2C(1, freq=new_freq)  # timeout should stay same
        self.assertEqual(bus.freq, new_freq)
        self.assertEqual(bus.timeout, DEFAULT_TIMEOUT)
        self.assertIs(bus.sda, fake_machine.Pin(26))

        # Timeout
        fake_machine.I2C(1, timeout=new_timeout)
        self.assertEqual(bus.freq, new_freq)
        self.assertEqual(bus.timeout, new_timeout)

        # Pin (scl has same logic as sda so only checking one)
        new_sda = fake_machine.Pin(6)
        fake_machine.I2C(1, sda=6)
        self.assertEqual(bus.freq, new_freq)
        self.assertEqual(bus.timeout, new_timeout)
        self.assertIs(bus.sda, new_sda)
        self.assertIs(bus.scl, fake_machine.Pin(25))

    def test_default_str_output(self):
        """Test that the str output of the default I2C matches board.

        Board default output is ``I2C(0, scl=18, sda=19, freq=400000, timeout=50000)``
        """
        expected = "I2C(0, scl=18, sda=19, freq=400000, timeout=50000)"
        self.assertEqual(str(self.i2c), expected)
        self.assertEqual(repr(self.i2c), expected)

        # and also make sure it can change
        expected = "I2C(0, scl=18, sda=19, freq=500, timeout=50000)"
        fake_machine.I2C(0, freq=500)
        self.assertEqual(str(self.i2c), expected)


class TestSoftI2CFunctionality(unittest.TestCase):
    """Tests for ``fake_machine.SoftI2C``.

    TODO - add more tests in future once SoftI2C fully implemented.
    """

    def setUp(self):
        # Clean-up registry to avoid leaking
        fake_machine.SoftI2C.reset_instance()
        self.addCleanup(fake_machine.reset_registries)

    def test_softi2c_singleton(self):
        """Test that the SoftI2C singleton works."""
        self.assertIsNone(fake_machine.SoftI2C._INSTANCE)
        i2c = fake_machine.SoftI2C(12, 14)
        self.assertIsInstance(i2c, fake_machine.SoftI2C)
        self.assertIs(i2c.sda, fake_machine.Pin(14))
        i2c2 = fake_machine.SoftI2C()
        self.assertIs(i2c2, i2c)
        self.assertIs(i2c2.sda, fake_machine.Pin(14))

    def test_basic_softi2c_device(self):
        """Test that a basic device can be registered on the SoftI2C bus"""
        i2c = fake_machine.SoftI2C()
        device = fake_machine.I2CDevice(0x9, i2c)
        device.set_single_reg(0x2, b"\x02\x03")
        self.assertEqual(i2c.readfrom_mem(0x9, 0x2, 2), b"\x02\x03")
