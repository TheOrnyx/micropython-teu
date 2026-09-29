"""test_uart_strategies.py - Test class for testing the functionality of just the
``fake_machine.UART`` ResponseStrategy classes, check the functionality works."""

import unittest
from teu import fake_machine


class TestUartStrategies(unittest.TestCase):
    """Test class for testing UART ResponseStrategy classes."""

    def setUp(self):
        """Just adds a cleanup for clearing the registry, tests can leak otherwise."""
        self.addCleanup(fake_machine.UART.reset_registry)

    def test_list_response_cycle_mode(self):
        """Test that the ``ListResponseStrategy` works properly in the 'cycle' mode.
        Should go back to the start of the list when reaching the end."""
        input_list = [b"1", b"2", b"3", b"4"]

        uart = fake_machine.UART(1)
        uart.set_response_list(input_list, on_exhaust="cycle")

        # Run over list twice, should cycle once
        for i in range(8):
            uart.write("")
            self.assertEqual(uart.read(), input_list[i % 4])

        # Next read should give first item again
        uart.write("")
        self.assertEqual(uart.read(), input_list[0])

    def test_set_list_response(self):
        """Test that ``UART.set_list_response`` works properly."""
        # Start with mappings so can confirm set_list_response changes response type
        resp_list = [b"A", b"B", b"C"]
        uart = fake_machine.UART.create_stub(1, mappings={"A": "B"})
        self.assertIsInstance(uart._response_strategy, fake_machine.uart.MappingResponseStrategy)
        uart.set_response_list(resp_list)
        self.assertIsInstance(uart._response_strategy, fake_machine.uart.ListResponseStrategy)
        uart.write("")
        self.assertEqual(uart.read(), b"A")

        # Check that we can change on_exhaust without modifying response_list
        uart.set_response_list(on_exhaust="repeat_last")
        resps = getattr(uart._response_strategy, "_responses")
        exhausted = getattr(uart._response_strategy, "on_exhausted")
        self.assertEqual(exhausted, "repeat_last")
        self.assertEqual(resps, resp_list)

    def test_set_list_response_raises_when_updating_nonlist_response(self):
        """Test that ``UART.set_list_response`` raises a TypeError when you try to update the
        on_exhausted for a non-list response strategy"""
        uart = fake_machine.UART(1)
        with self.assertRaises(TypeError):
            uart.set_response_list(on_exhaust="repeat_last")

    def test_add_responses_to_list_works(self):
        """Test that ``UART.add_response_to_list()`` works as expected"""
        uart = fake_machine.UART(1)
        uart.set_response_list(["A", "B"])
        resps = getattr(uart._response_strategy, "_responses")
        self.assertEqual(resps, [b"A", b"B"])
        uart.add_responses_to_list([b"C"])
        resps = getattr(uart._response_strategy, "_responses")
        self.assertEqual(resps, [b"A", b"B", b"C"])

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
        # Start with empty
        stub = fake_machine.UART.create_stub(
            1, response_list=["A"], list_exhausted_behaviour="empty"
        )
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
