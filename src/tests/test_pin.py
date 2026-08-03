"""Tests for testing our Pin implementation.

Just testing that basic operations work as expected and operation mostly matches board.
"""

# FIXME - needed while we transition the package name
# mypy: disable-error-code="attr-defined, call-arg, call-overload"

# NOTE - the machine import gives a pylint import-error for some reason, but would work at runtime
import unittest
from machine import Pin  # pylint: disable=import-error

# pylint: disable=protected-access


class TestPinFunctionality(unittest.TestCase):
    """Test class for testing various edge cases and functionalities of our Pin implementation.

    A mix of testing that specific implementations of features work as expected (and are
    bug-free), and testing that operation mostly matches what we would get on-board
    """

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
