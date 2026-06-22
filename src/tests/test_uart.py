"""Tests for testing the UART test doubles.
Contains a mix of example usages and testing of functionality and accuracy.
"""

import unittest
from lib import machine  # pylint: disable=import-error


class TestUartFunctionality(unittest.TestCase):
    """Class for testing the functionality and edge cases of the UART test doubles.

    TODO - implement more tests
    """

    def test_readline(self):
        """Test the UART.readline function and edgecases for it"""
        uart = machine.UART(1)
        self.assertIsNone(uart.readline(), "Empty readline should return None")

        # No newline returning whole buffer
        uart.write(b"no newline")  # basic write should just echo
        self.assertEqual(b"no newline", uart.readline())

        # Newline working
        uart.write(b"line1\nline2")
        self.assertEqual(b"line1\n", uart.readline())
        self.assertEqual(b"line2", uart.readline())

        # Newline called with size
        uart.write(b"onetwo\n")
        self.assertEqual(b"one", uart.readline(3))
        self.assertEqual(b"two\n", uart.readline(-1))  # -1 should be maxlen

    def test_iterator_usage(self):
        """Test the UART device can be used as an iterator and it works properly"""

        lines = ["line one\n", "another line\n", "a third line for fun\n", "one more for four!"]
        lines_buf = "".join(lines).encode("utf-8")
        uart = machine.UART.create_stub(1, initial_buffer_contents=lines_buf)

        for index, line in enumerate(uart):
            expected = lines[index].encode("utf-8")
            self.assertEqual(expected, line, "Lines don't match")

        self.assertEqual(0, uart.any(), "Uart should be empty after iteration")

    def test_stream_usage(self):
        """Test that the UART object can be used as a stream object."""

        # No mappings, will just echo back
        stub = machine.UART.create_stub(1)
        print("hello uart", file=stub)
        data = stub.get_written_data()
        self.assertEqual(b"hello uart\n", data)  # print also does a write for the newline

        # Test with mappings
        stub = machine.UART.create_stub(1, mappings={b"hello": b"goodbye"})
        print("hello", file=stub)
        data = stub.read()
        self.assertEqual(b"goodbye\n", data)


class ExampleUartUsage(unittest.TestCase):
    """Test cases for showing an example of using the UART stubs and mocks to test a function
    which communicates with a UART object and parses the responses."""

    @staticmethod
    def f_to_c(fahrenheit: float) -> float:
        "F to C"
        return (fahrenheit - 32.0) * 5.0 / 9.0

    @staticmethod
    def example_read_temp() -> tuple | None:
        """An example of code that might send a command to a UART object to get temperature
        readings in Fahrenheit and parse the response, converting from Fahrenheit to Celsius.

        Expected command flow:
        'connect'->'OK',
        'temp_count'->'[number of temperature readings]',
        'read_temps'->'[comma separated Fahrenheit float temp values]' (E.g: `b'97.5, 87.4'`)

        :returns: a tuple of Celsius float readings rounded to 2 decimal places on success or
        None on failure.

        Failure is caused by unexpected response or inaccurate reading count, such as
        expecting 3 temps and receiving 4
        """
        serial = machine.uart.UART(1)
        serial.write(b"connect")

        if serial.read() != b"OK":
            return None
        serial.write(b"temp_count")
        exp_count = serial.read()

        if not exp_count or not exp_count.isdigit():
            return None
        exp_count = int(exp_count)
        serial.write(b"read_temps")

        if serial.any() == 0:
            return None

        response = serial.read() or b""
        f_temps = response.decode("utf-8").split(",")
        if len(f_temps) != exp_count:
            return None

        try:
            c_temps = [ExampleUartUsage.f_to_c(float(f)) for f in f_temps]
            c_temps = [round(c, 2) for c in c_temps]  # Round
            return tuple(c_temps)
        except ValueError:
            return None

    def test_stub_readtemp_valid(self):
        """Valid readtemp usage using a basic stub"""
        stub = machine.UART.create_stub(1)
        stub.set_mappings(
            {b"connect": b"OK", b"temp_count": b"3", b"read_temps": b"97.50, 84.30, 96.40"}
        )
        expected = (36.39, 29.06, 35.78)

        temps = self.example_read_temp()
        self.assertIsNotNone(temps, "Temps shouldn't be None")
        self.assertEqual(3, len(temps or []), "Wrong number of temps")
        self.assertEqual(expected, temps, "Received temps doesn't match expected")

    def test_stub_readtemp_fails_when_invalid_connect_response(self):
        "Check fails and returns None when invalid connect response"
        _stub = machine.UART.create_stub(1, mappings={b"connect": b"Bad"})

        temps = self.example_read_temp()
        self.assertIsNone(temps, "Temps should be None")

    def test_stub_readtemp_fails_when_temp_doesnt_match_count(self):
        """Check fails and returns None when the number of temperatures received doesn't match
        the expected count"""
        stub = machine.UART.create_stub(1)
        stub.set_mappings({b"connect": b"OK", b"temp_count": b"2", b"read_temps": b"95.55"})

        temps = self.example_read_temp()
        self.assertIsNone(temps, "Temps should be None")

    def test_stub_readtemp_fails_when_receiving_garbage_temps(self):
        """Check fails and returns None when the temperatures received are not floats"""
        stub = machine.UART.create_stub(1)
        stub.set_mappings(
            {b"connect": b"OK", b"temp_count": b"2", b"read_temps": b"garbage,horrible"}
        )

        temps = self.example_read_temp()
        self.assertIsNone(temps, "Temps should be None")

    def test_stub_readtemp_fails_when_no_temps(self):
        """Check fails and returns None when there are no temps to read"""
        stub = machine.UART.create_stub(1)
        stub.set_mappings({b"connect": b"OK", b"temp_count": b"0", b"read_temps": b""})

        temps = self.example_read_temp()
        self.assertIsNone(temps, "Temps should be None")


class UartMockTests(unittest.TestCase):
    """Uart mock tests"""

    def test_uartmock_valid_write(self):
        "Valid test without reads"
        mock = machine.UART.create_mock(1)
        mock.expect_write_then_queue(b"Exp-A", b"Resp-A")
        mock.expect_write_then_queue(b"Exp-Bee", b"Resp-Bee")

        real = machine.UART(1)  # Multiton should return the mock
        self.assertIs(real, mock, "Not the same")

        real.write(b"Exp-A")
        self.assertEqual(6, real.any(), "Wrong written length")
        self.assertEqual(b"Resp-A", real.read(), "Invalid response")

        real.write(b"Exp-Bee")
        self.assertEqual(8, real.any(), "Wrong written length")
        self.assertEqual(b"Resp-Bee", real.read(), "Invalid response")

        mock.validate()

    def test_uartmock_write_should_fail_with_wrong_arg(self):
        "Fails when expecting different arg than provided"
        mock = machine.UART.create_mock(1)
        mock.expect_write_then_queue(b"Exp-A", b"Resp-A")

        real = machine.UART(1)
        with self.assertRaises(AssertionError):
            real.write(b"Wrong-message")

    def test_uartmock_valid_read(self):
        "Valid mock read test"
        mock = machine.UART.create_mock(1, assert_reads=True)
        mock.expect_write_then_queue(b"Exp-A", b"Resp-A")
        mock.expect_read(5)

        real = machine.UART(1)

        real.write(b"Exp-A")
        self.assertEqual(6, real.any(), "Wrong written length")
        self.assertEqual(b"Resp-", real.read(5), "Invalid response")

        with self.assertRaises(AssertionError):
            real.read()

    def test_uartmock_read_fails_when_wrong_bytes(self):
        "Fails when expecting different received bytes when reading"
        mock = machine.UART.create_mock(1, assert_reads=True)
        mock.expect_write_then_queue(b"Exp-A", b"Resp")
        mock.expect_read(6)

        real = machine.UART(1)

        real.write(b"Exp-A")
        self.assertEqual(4, real.any(), "Wrong written length")

        with self.assertRaises(AssertionError):
            real.read()


if __name__ == "__main__":
    unittest.main()
