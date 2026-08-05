"""Tests for testing the UART test doubles.
Contains a mix of example usages and testing of functionality and accuracy.
"""

import unittest
import fake_machine

# pylint: disable=protected-access


class TestUartFunctionality(unittest.TestCase):
    """Class for testing the functionality and edge cases of the UART test doubles.

    TODO - implement more tests
    """

    def setUp(self):
        """Just adds a cleanup for clearing the registry, tests leak otherwise."""
        self.addCleanup(fake_machine.UART.reset_registry)

    def test_unknown_ids_raise(self):
        """Test that unknown ID's will cause an exception"""
        fake_machine.UART(1)
        with self.assertRaises(ValueError):
            fake_machine.UART(3)

        # Check it doesn't raise when ignoring, probs not using but good to make sure it works.
        fake_machine.UART(12, override_id_checks=True)

    def test_default_pin_ids(self):
        """Test the default pin assignments work properly"""
        # Checking UART(1)
        def_1_tx = fake_machine.Pin(5)
        def_1_rx = fake_machine.Pin(4)
        uart1 = fake_machine.UART(1)
        self.assertIs(uart1.tx, def_1_tx)
        self.assertIs(uart1.rx, def_1_rx)

        # Checking UART(2)
        def_2_tx = fake_machine.Pin(17)
        def_2_rx = fake_machine.Pin(16)
        uart2 = fake_machine.UART(2)
        self.assertIs(uart2.tx, def_2_tx)
        self.assertIs(uart2.rx, def_2_rx)

    def test_stub_kwargs_are_passed(self):
        """Not much to check here, just want to make sure that when create_stub accepts
        constructor args (like baudrate, or tx) that they get set properly.

        Not sure what the usecase for this feature is tbh, but it's there so might as well test.
        """
        p = fake_machine.Pin(20)
        u = fake_machine.UART.create_stub(1, constant_response="Swag", tx=p, txbuf=300)
        self.assertIs(u.tx, p)
        self.assertEqual(u.txbuf, 300)

    def test_uart_pin_values(self):
        """Test that the pin values work properly, with -1 for unassigned and None for
        unchanged."""
        p = fake_machine.Pin(20)
        u1 = fake_machine.UART(1, tx=fake_machine.Pin(20))
        u1_tx = u1.tx
        self.assertIs(p, u1_tx)
        u2 = fake_machine.UART(1, tx=None)  # Shouldn't change value
        self.assertIs(u2, u1)
        self.assertIs(u2.tx, p)
        u2.init(tx=-1)  # Should make pin unassigned
        self.assertIs(u2.tx, None)

    def test_reinitialization_only_sets_provided_args(self):
        """Test that re-initializing a UART object only sets provided arguments."""
        u1 = fake_machine.UART(1, baudrate=900)
        self.assertEqual(u1.baudrate, 900)
        u2 = fake_machine.UART(1)
        self.assertIs(u2, u1)
        self.assertEqual(u1.baudrate, 900)
        u2.init(bits=7)
        self.assertEqual(u1.baudrate, 900)
        # TODO - test more attributes

    def test_readline(self):
        """Test the UART.readline function and edgecases for it"""
        uart = fake_machine.UART(1)
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
        uart = fake_machine.UART.create_stub(1, initial_buffer_contents=lines_buf)

        for index, line in enumerate(uart):
            expected = lines[index].encode("utf-8")
            self.assertEqual(expected, line, "Lines don't match")

        self.assertEqual(0, uart.any(), "Uart should be empty after iteration")

    def test_stream_usage(self):
        """Test that the UART object can be used as a stream object."""

        # No mappings, will just echo back
        stub = fake_machine.UART.create_stub(1)
        print("hello uart", file=stub)
        data = stub.get_written_data()
        self.assertEqual(b"hello uart\n", data)  # print also does a write for the newline

        # Test with mappings
        stub = fake_machine.UART.create_stub(1, mappings={b"hello": b"goodbye"})
        print("hello", file=stub)
        data2 = stub.read()
        self.assertEqual(b"goodbye\n", data2)

    def test_default_str(self):
        """Test the default str and repr value of a UART object matches expected board version"""

        def test_str(u, expected):
            """Just a little helper"""
            self.assertEqual(str(u), expected)
            self.assertEqual(repr(u), expected)
            self.assertEqual(str(u), repr(u))

        # NOTE - changing default baudrate here as default baudrate on board seems to be overidden
        # Default with no flow or invert
        expected_regular = (
            "UART(1, baudrate=9600, bits=8, parity=None, stop=1, tx=5, rx=4, rts=-1, "
            "cts=-1, txbuf=256, rxbuf=256, timeout=0, timeout_char=0, irq=0)"
        )
        uart = fake_machine.UART(1)
        test_str(uart, expected_regular)

        # Default with both flow and invert and rts set
        expected_flow_and_invert = (
            "UART(1, baudrate=9600, bits=8, parity=None, stop=1, tx=5, rx=4, rts=12, "
            "cts=-1, txbuf=256, rxbuf=256, timeout=0, timeout_char=0, irq=0, "
            "invert=INV_TX|INV_RX|INV_RTS, flow=RTS|CTS)"
        )
        # Ignore registry to get fresh object
        uart_flow_invert = fake_machine.UART(
            1,
            ignore_registry=True,
            invert=fake_machine.UART.INV_TX
            | fake_machine.UART.INV_RX
            | fake_machine.UART.INV_RTS,
            flow=fake_machine.UART.RTS | fake_machine.UART.CTS,
            rts=fake_machine.Pin(12),
        )
        self.assertIsNot(uart_flow_invert, uart)  # Check they aren't same to be safe
        test_str(uart_flow_invert, expected_flow_and_invert)

    # ------ Tests for specifically the strategies

    def test_strategy_validation(self):
        """Tests that the create_stub factory properly raises an exception when combinations of
        strategies are provided"""
        with self.assertRaises(ValueError):
            fake_machine.UART.create_stub(1, mappings={b"A": b"B"}, response_list=[b"C", b"D"])

        # Test combining a constant_response and a response_callback
        with self.assertRaises(ValueError):
            fake_machine.UART.create_stub(
                1, constant_response=b"Const", response_callback=lambda data, uart: b"Callback"
            )

        # Test combining custom_response with mappings
        with self.assertRaises(ValueError):
            custom_strat = fake_machine.uart.EchoResponseStrategy()
            fake_machine.UART.create_stub(1, custom_response=custom_strat, mappings={b"A": b"B"})

    def test_strict_mapping_raises(self):
        """Test that a `MappingResponseStrategy` in strict mode will raise when an unmapped
        value is provided"""
        stub = fake_machine.UART.create_stub(1, is_strict=True, mappings={"A": "OK"})
        self.assertIsInstance(stub._response_strategy, fake_machine.uart.MappingResponseStrategy)
        stub.write("A")
        self.assertEqual(b"OK", stub.read())

        self.assertRaises(KeyError, stub.write, "Unknown")

    def test_list_response_exhaustion(self):
        """Test the different list exhausted options for the `ListResponseStrategy"""
        # Default is "empty"
        stub = fake_machine.UART.create_stub(1, response_list=["A"])
        self.assertEqual("empty", getattr(stub._response_strategy, "_on_exhausted"))
        stub.write("Nothing")
        self.assertEqual(b"A", stub.read())
        stub.write("Nothings")
        self.assertIsNone(stub.read())  # NOTE - empty buffer returns None

        # repeat_last
        stub = fake_machine.UART.create_stub(
            1, response_list=["B"], list_exhausted_behaviour="repeat_last"
        )
        stub.write("Nothing")
        self.assertEqual(b"B", stub.read())
        stub.write("Nothings")
        self.assertEqual(b"B", stub.read())

        # raise
        stub = fake_machine.UART.create_stub(
            1, response_list=[], list_exhausted_behaviour="raise"
        )
        self.assertIsInstance(stub._response_strategy, fake_machine.uart.ListResponseStrategy)
        self.assertRaises(IndexError, stub.write, "Nop")

    def test_callback_strategy(self):
        """Test that the `CallbackResponseStrategy` works properly."""
        got_called = False

        def callback(data, uart) -> bytes:
            nonlocal got_called
            self.assertEqual(b"Called", data)
            got_called = True
            return b"Callbacked"

        stub = fake_machine.UART.create_stub(1, response_callback=callback)
        self.assertIsInstance(stub._response_strategy, fake_machine.uart.CallbackResponseStrategy)
        stub.write("Called")
        self.assertTrue(got_called, "Callback didn't modify got_called")
        self.assertEqual(b"Callbacked", stub.read())


# ------------------ EXAMPLE USAGE, from first progress presentation ---------------


class ExampleUartUsage(unittest.TestCase):
    """Test cases for showing an example of using the UART stubs and mocks to test a function
    which communicates with a UART object and parses the responses."""

    def setUp(self):
        """Just adds a cleanup for clearing the registry, tests leak otherwise."""
        fake_machine.shadow_builtin_machine()  # Shadow the builtin
        self.addCleanup(fake_machine.UART.reset_registry)

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
        # Local machine import to demonstrate the shadowing
        # pylint: disable=import-outside-toplevel, import-error
        import machine

        serial = machine.UART(1)
        serial.write(b"connect")

        if serial.read() != b"OK":
            return None
        serial.write(b"temp_count")
        exp_count = serial.read()

        if not exp_count or not exp_count.isdigit():
            return None
        exp_count_int = int(exp_count)
        serial.write(b"read_temps")

        if serial.any() == 0:
            return None

        response = serial.read() or b""
        f_temps = response.decode("utf-8").split(",")
        if len(f_temps) != exp_count_int:
            return None

        try:
            c_temps = [ExampleUartUsage.f_to_c(float(f)) for f in f_temps]
            c_temps = [round(c, 2) for c in c_temps]  # Round
            return tuple(c_temps)
        except ValueError:
            return None

    def test_stub_readtemp_valid(self):
        """Valid readtemp usage using a basic stub"""
        stub = fake_machine.UART.create_stub(1)
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
        _stub = fake_machine.UART.create_stub(1, mappings={b"connect": b"Bad"})

        temps = self.example_read_temp()
        self.assertIsNone(temps, "Temps should be None")

    def test_stub_readtemp_fails_when_temp_doesnt_match_count(self):
        """Check fails and returns None when the number of temperatures received doesn't match
        the expected count"""
        stub = fake_machine.UART.create_stub(1)
        stub.set_mappings({b"connect": b"OK", b"temp_count": b"2", b"read_temps": b"95.55"})

        temps = self.example_read_temp()
        self.assertIsNone(temps, "Temps should be None")

    def test_stub_readtemp_fails_when_receiving_garbage_temps(self):
        """Check fails and returns None when the temperatures received are not floats"""
        stub = fake_machine.UART.create_stub(1)
        stub.set_mappings(
            {b"connect": b"OK", b"temp_count": b"2", b"read_temps": b"garbage,horrible"}
        )

        temps = self.example_read_temp()
        self.assertIsNone(temps, "Temps should be None")

    def test_stub_readtemp_fails_when_no_temps(self):
        """Check fails and returns None when there are no temps to read"""
        stub = fake_machine.UART.create_stub(1)
        stub.set_mappings({b"connect": b"OK", b"temp_count": b"0", b"read_temps": b""})

        temps = self.example_read_temp()
        self.assertIsNone(temps, "Temps should be None")


if __name__ == "__main__":
    unittest.main()
