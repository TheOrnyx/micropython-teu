"""
test_sim800l_unix.py - Off-board UNIX tests for the SIM800L modem driver in SIM800L.py.

These test the parsing logic of the driver's ``get_*`` helper methods (plus a few behaviours of
the underlying ``execute_at_command()``) through the ``fake_machine.UART`` test class, by
mimicking the responses a real SIM800L module sends back for each AT command.

"""

import unittest
import teu
from teu import fake_machine

# Shadow builtins immediately
teu.shadow_builtins()

from . import SIM800L


def at_response(command, *info_lines, final="OK"):
    """Build the raw bytes a real SIM800L sends back for `command`.

    (Just a note that double backslashes in this docstring are for the docstring renderer in
    IDE to work, actual result uses single backslash)

    The device echoes the command terminated with ``\\r\\r\\n``, then sends each information
    line followed by ``\\r\\n``, then a blank ``\\r\\n`` line (only when there was information),
    and finally the result code.

    For example ``at_response("AT+CSQ", "+CSQ: 15,0")`` builds
    ``b"AT+CSQ\\r\\r\\n+CSQ: 15,0\\r\\n\\r\\nOK\\r\\n"``.

    Pass ``final="ERROR"`` to mimic the module rejecting the command.
    """
    info = "".join(line + "\r\n" for line in info_lines)
    if info_lines:
        info += "\r\n"
    return (command + "\r\r\n" + info + final + "\r\n").encode("utf-8")


class TestSIM800LDriver(unittest.TestCase):
    """Test class for the SIM800L driver logic using the ``fake_machine.UART`` test class to
    mimic modem responses.

    The Modem constructors ``uart`` argument is used to pass in the fake directly, instead of
    using ``.initialize()`` and then getting the created UART.
    """

    def setUp(self):
        """Reset the UART registry, then create the fake UART and the Modem that uses it."""
        fake_machine.UART.reset_registry()
        self.addCleanup(fake_machine.UART.reset_registry)

        self.uart: fake_machine.UART = fake_machine.UART(1)
        self.modem = SIM800L.Modem(uart=self.uart)

    def assert_raises_with_text(self, exc_type, text, func, *args):
        """Assert that provided func ``func(*args)`` raises `exc_type` and that the message
        contains `text`.

        The driver raises plain ``Exception`` for several different problems, and the fake UART
        raises ``KeyError`` when a command has no mapping. Manually checking the exception
        message stops an unrelated exception from making a test pass by accident.
        """
        try:
            func(*args)
        except exc_type as e:
            self.assertIn(text, str(e))
            return
        raise AssertionError(f"{exc_type.__name__} was not raised")

    # ------ get_info() tests

    def test_get_info_returns_cleaned_response(self):
        """Test that ``get_info()`` sends ATI (CRLF terminated) and returns the response with
        the echo, blank lines and trailing newline all stripped off."""
        self.uart.set_mappings({"ATI\r\n": at_response("ATI", "SIM800 R11.08")})
        self.assertEqual(self.modem.get_info(), "SIM800 R11.08")
        self.assertEqual(self.uart.get_written_data(), b"ATI\r\n")

    # ------ get_signal_strength() tests

    def test_get_signal_strength_converts_to_ratio(self):
        """Test that ``get_signal_strength()`` divides the +CSQ value by the max of 30, including
        at the minimum and maximum values."""
        for csq, expected in ((15, 0.5), (0, 0.0), (30, 1.0)):
            self.uart.set_mappings(
                {"AT+CSQ\r\n": at_response("AT+CSQ", "+CSQ: {},0".format(csq))}
            )
            self.assertEqual(self.modem.get_signal_strength(), expected)

    def test_get_signal_strength_raises_on_non_numeric_value(self):
        """Test that ``get_signal_strength()`` raises a ValueError when the signal value in
        the response can't be converted to an int.

        Probably not the most helpful test but shows how the driver could break if a fault was
        present in the response, as they attempt a straight ``int(data)`` conversion without a
        try catch.
        """
        self.uart.set_mappings({"AT+CSQ\r\n": at_response("AT+CSQ", "+CSQ: bad,0")})
        self.assertRaises(ValueError, self.modem.get_signal_strength)

    def test_get_signal_strength_raises_on_modem_error(self):
        """Test that a generic ERROR response from the modem raises a ``GenericATError`` from
        ``.get_signal_strength()``"""
        self.uart.set_mappings({"AT+CSQ\r\n": at_response("AT+CSQ", final="ERROR")})
        self.assertRaises(SIM800L.GenericATError, self.modem.get_signal_strength)

    # ------ get_current_network() tests

    def test_get_current_network_returns_operator_name(self):
        """Test that ``get_current_network()`` returns the operator name from the +COPS
        response with the surrounding quotes removed."""
        self.uart.set_mappings({"AT+COPS?\r\n": at_response("AT+COPS?", '+COPS: 0,0,"Spark NZ"')})
        self.assertEqual(self.modem.get_current_network(), "Spark NZ")

    def test_get_current_network_none_when_not_registered(self):
        """Test that ``get_current_network()`` returns None when the +COPS response contains
        no operator, which is what the modem sends when not registered to a network."""
        self.uart.set_mappings({"AT+COPS?\r\n": at_response("AT+COPS?", "+COPS: 0")})
        self.assertIsNone(self.modem.get_current_network())

    # ------ get_ip_addr() tests

    def test_get_ip_addr_returns_address(self):
        """Test that ``.get_ip_addr()`` parses the IP address out of a +SAPBR bearer response."""
        self.uart.set_mappings(
            {"AT+SAPBR=2,1\r\n": at_response("AT+SAPBR=2,1", '+SAPBR: 1,1,"10.20.30.40"')}
        )
        self.assertEqual(self.modem.get_ip_addr(), "10.20.30.40")

    def test_get_ip_addr_ignores_leftover_data_before_response(self):
        """Test that ``.get_ip_addr()`` still finds the address when unrelated data (like a URC
        left in the buffer) comes before the +SAPBR response. As they specifically parse the
        last command response item."""
        self.uart.set_mappings(
            {
                "AT+SAPBR=2,1\r\n": at_response(
                    "AT+SAPBR=2,1", "+CIEV: 1", '+SAPBR: 1,1,"10.1.2.3"'
                )
            }
        )
        self.assertEqual(self.modem.get_ip_addr(), "10.1.2.3")

    def test_get_ip_addr_none_when_bearer_has_no_address(self):
        """Test that ``.get_ip_addr()`` returns None (rather than the string) when the modem
        reports the placeholder address 0.0.0.0, meaning the bearer isn't connected."""
        self.uart.set_mappings(
            {"AT+SAPBR=2,1\r\n": at_response("AT+SAPBR=2,1", '+SAPBR: 1,3,"0.0.0.0"')}
        )
        self.assertIsNone(self.modem.get_ip_addr())

    def test_get_ip_addr_raises_on_wrong_field_count(self):
        """Test that ``.get_ip_addr()`` raises when the +SAPBR response doesn't have the three
        expected comma-separated fields."""
        self.uart.set_mappings({"AT+SAPBR=2,1\r\n": at_response("AT+SAPBR=2,1", "+SAPBR: 1,3")})
        self.assert_raises_with_text(Exception, "Cannot parse", self.modem.get_ip_addr)

    def test_get_ip_addr_raises_on_malformed_address(self):
        """Test that ``.get_ip_addr()`` raises when the address field doesn't have four
        dot-separated parts."""
        self.uart.set_mappings(
            {"AT+SAPBR=2,1\r\n": at_response("AT+SAPBR=2,1", '+SAPBR: 1,1,"10.1.2"')}
        )
        self.assert_raises_with_text(Exception, "Cannot parse", self.modem.get_ip_addr)

    # ------ scan_networks() test

    def test_scan_networks_parses_network_list(self):
        """Test that ``.scan_networks()`` turns the +COPS=? response into a list of dicts and
        skips the trailing supported-mode groups like ``(0-4)`` that aren't networks."""
        # Reference operators result taken from existing SIM800L driver test.
        operators = (
            '(2,"vodafone","voda IT","22210"),'
            '(3,"TELECOM ITALIA MOBILE","TIM","22201"),'
            '(3,"Wind Telecom SpA","I WIND","22288")'
        )
        self.uart.set_mappings(
            {
                "AT+COPS=?\r\n": at_response(
                    "AT+COPS=?",
                    f"+COPS: {operators},,(0-4),(0-2)",
                )
            }
        )
        expected = [
            {"name": "vodafone", "shortname": "voda IT", "id": "22210"},
            {"name": "TELECOM ITALIA MOBILE", "shortname": "TIM", "id": "22201"},
            {"name": "Wind Telecom SpA", "shortname": "I WIND", "id": "22288"},
        ]
        self.assertEqual(self.modem.scan_networks(), expected)

    # ------ execute_at_command() tests

    def test_execute_at_command_raises_on_unknown_command(self):
        """Test that ``execute_at_command()`` raises for a command name that isn't in its
        commands dictionary."""
        self.assert_raises_with_text(
            Exception, "Unknown command", self.modem.execute_at_command, "notacommand"
        )

    def test_execute_at_command_raises_on_timeout(self):
        """Test that ``execute_at_command()`` raises a timeout exception when the modem never
        responds. The empty mapped response makes the fake UART's ``readline()`` return None.

        This test will take a few seconds to run due to the sleeps for the timeout.
        """
        self.uart.set_mappings({"ATI\r\n": ""})
        self.assert_raises_with_text(Exception, "Timeout", self.modem.get_info)

    # ----- misc tests

    def test_connect_raises_when_not_initialized(self):
        """Test that the ``.connect()`` method raises an Exception when the modem isn't
        initialized."""
        self.assert_raises_with_text(
            Exception, "Modem is not initialized, cannot connect", self.modem.connect, "APN"
        )

    def test_connect_return_none_when_connected(self):
        """Test that the ``.connect()`` method returns None if the modem is already connected
        (``.get_ip_addr()`` returns valid IP addr)"""
        self.modem.initialized = True  # to avoid raise at start
        self.uart.set_mappings(
            {"AT+SAPBR=2,1\r\n": at_response("AT+SAPBR=2,1", '+SAPBR: 1,1,"10.20.30.40"')}
        )
        self.assertIsNone(self.modem.connect("APN"))


if __name__ == "__main__":
    unittest.main()
