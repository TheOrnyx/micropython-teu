"""Tests for testing our Pin implementation.

Just testing that basic operations work as expected and operation mostly matches board.
"""

import time

import unittest
from teu import fake_machine
from teu.fake_machine import Pin

# pylint: disable=protected-access, invalid-name
# pyright: reportCallIssue=false


class TestPinFunctionality(unittest.TestCase):
    """Test class for testing various edge cases and functionalities of our Pin implementation.

    A mix of testing that specific implementations of features work as expected (and are
    bug-free), and testing that operation mostly matches what we would get on-board
    """

    def setUp(self):
        """Setup method for the test class, just resets the pin registry between tests as
        testing individual implementations rather than as a system."""
        self.addCleanup(fake_machine.Pin.reset_registry)

    def test_value_buffering(self):
        """Test that the pin value buffering when writing in ``Pin.IN`` mode works properly.
        Also tests some of the Pin mode stuff as well."""
        p1 = Pin(2, mode=Pin.IN)
        self.assertIsNone(p1._buf_val)
        p1.value(1)
        self.assertEqual(p1._cur_value, 0)  # Should still be 0
        self.assertEqual(p1._buf_val, 1)
        p1.init(mode=Pin.OUT)  # Now value should be set
        self.assertEqual(p1(), 1)
        self.assertIsNone(p1._buf_val)
        p1(0)

        # Check that providing a value with IN mode buffers value
        p1.init(mode=Pin.IN, value=1)
        self.assertEqual(p1(), 0)
        self.assertEqual(p1._buf_val, 1)
        p1.init(mode=Pin.OUT)
        self.assertEqual(p1(), 1)
        p1(0)

        # Check that providing a value argument on init overrides buffer
        p1 = Pin(2, mode=Pin.IN)
        p1.on()
        self.assertEqual(p1._buf_val, 1)
        p1.init(mode=Pin.OUT, value=0)
        self.assertEqual(p1.value(), 0)
        self.assertIsNone(p1._buf_val)

    def test_irq_functionality(self):
        """Just test that the IRQ implementation works all good and underlying object stays the
        same.

        Since the interrupts are scheduled with ``micropython.schedule()`` they can be a bit
        finnicky if evaluating too many too quickly, so a few sections will be padded with a
        ``time.sleep(0)`` to force the scheduled events to run."""
        was_called = False

        def test_callback(pin):
            nonlocal was_called
            was_called = True

        p1 = Pin(4, mode=Pin.OUT)
        self.assertEqual(p1._irq.trigger(), 0)

        # Test with both rising and falling
        irq = p1.irq(test_callback)
        self.assertEqual(irq.trigger(), Pin.IRQ_FALLING | Pin.IRQ_RISING)
        self.assertFalse(was_called)
        p1.value(1)  # Rising
        time.sleep(0)  # Force event to run
        self.assertTrue(was_called)
        was_called = False
        p1(0)  # Falling
        time.sleep(0)
        self.assertTrue(was_called)

        # Test just falling
        was_called = False
        irq2 = p1.irq(test_callback, trigger=Pin.IRQ_FALLING)
        self.assertIs(irq, irq2)  # Should be same object
        self.assertEqual(p1._irq.trigger(), Pin.IRQ_FALLING)
        p1(1)  # Shouldn't activate interrupt
        p1(1)  # Repeat to be safe
        time.sleep(0)
        self.assertFalse(was_called)
        p1(0)
        time.sleep(0)
        self.assertTrue(was_called)

        # Test that a trigger event of 0 forces interrupt to never run
        was_called = False
        irq = p1.irq(test_callback, trigger=0)
        self.assertEqual(p1._irq.trigger(), 0)
        p1(1)
        time.sleep(0)
        p1(0)
        time.sleep(0)
        self.assertFalse(was_called)
        irq()
        time.sleep(0)
        self.assertTrue(was_called)

        # Test that we can update the trigger event in the IRQ directly
        irq.trigger(Pin.IRQ_RISING)
        self.assertEqual(p1._irq.trigger(), Pin.IRQ_RISING)
        was_called = False
        p1(1)
        time.sleep(0)
        self.assertTrue(was_called)

        # Test that blank IRQ return returns existing object
        irq2 = p1.irq()
        self.assertIs(irq2, irq)

        # Test that constructing new IRQ uses same object
        irq3 = p1.irq(lambda p: None)
        self.assertIs(irq3, irq)

    def test_irq_extra(self):
        """Just an extra IRQ check that checks with a bit more involved example"""
        times_called = 0

        def test_callback(p):
            nonlocal times_called
            times_called += 1

        p = Pin(3, mode=Pin.OUT)
        irq = p.irq(test_callback, trigger=Pin.IRQ_RISING)
        self.assertIs(irq, p._irq)

        for _i in range(10):
            p.value(0)
            time.sleep(0)
            p.value(1)
            time.sleep(0)

        self.assertEqual(times_called, 10)

    def test_constructor_accepts_pins(self):
        """Check whether providing a Pin instance to the constructor returns the same object."""
        p1 = Pin(4)
        p2 = Pin(p1)
        self.assertIs(p2, p1)
        self.assertEqual(p2._mode, Pin.IN)
        p3 = Pin(Pin(p2), mode=Pin.OUT)
        self.assertIs(p3, p1)
        self.assertEqual(p1._mode, Pin.OUT)

    def test_bad_init_raises(self):
        """Test that bad init values (in constructor or init()) cause an error to be raised"""
        bad_val = 999  # guaranteed not to be in any of the allowed mode/pull/drive lists

        cases = [
            ("bad mode", {"mode": bad_val}),
            ("bad pull", {"pull": bad_val}),
            ("bad drive", {"drive": bad_val}),
            ("bad mode and pull", {"mode": bad_val, "pull": bad_val}),
            ("bad mode and drive", {"mode": bad_val, "drive": bad_val}),
            ("bad pull and drive", {"pull": bad_val, "drive": bad_val}),
            ("bad mode, pull and drive", {"mode": bad_val, "pull": bad_val, "drive": bad_val}),
        ]

        def test_raises(p: Pin | None, p_id=4, mode=-1, pull=-1, value=None, drive=-1):
            """Little helper that just initializes a pin with args and checks it throws"""
            with self.assertRaises(ValueError):
                if p is None:
                    Pin(p_id, mode=mode, pull=pull, value=value, drive=drive)
                else:
                    p.init(mode=mode, pull=pull, value=value, drive=drive)

        for description, bad_kwargs in cases:
            with self.subTest(msg=f"constructor - {description}", **bad_kwargs):
                test_raises(None, **bad_kwargs)

            with self.subTest(f"init() - {description}", **bad_kwargs):
                valid_pin = Pin(4, mode=Pin.IN, pull=Pin.PULL_UP, drive=Pin.DRIVE_0)
                test_raises(valid_pin, **bad_kwargs)

    def test_init_only_sets_assigned(self):
        """Test that init() won't set arguments that aren't provided."""
        p = Pin(4, mode=Pin.OUT)
        self.assertEqual(p._mode, Pin.OUT)
        p.init(pull=Pin.PULL_UP)
        self.assertEqual(p._mode, Pin.OUT)
        self.assertEqual(p._pull, Pin.PULL_UP)
        # TODO - add more maybe

    def test_multiton_returns(self):
        """Test that the multiton registry works properly and returns the same object for the
        same ID"""
        p1 = Pin(5)
        p2 = Pin(6)
        self.assertIsNot(p1, p2)
        p3 = Pin(5, mode=Pin.OUT)
        self.assertIs(p1, p3)
        self.assertEqual(p1._mode, Pin.OUT)

        # Test that attempting to use a string ID throws, just as it's not implemented yet
        # TODO - change this if String ID's get implemented
        with self.assertRaises(ValueError):
            Pin("X1")


if __name__ == "__main__":
    unittest.main()
