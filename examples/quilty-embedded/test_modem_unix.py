"""
test_modem_unix.py - Off-board UNIX tests for the quilty modem driver in drivers/modem.py.

This test was written for the James Quilty Environmental Monitoring embedded software and is
included in the TEU codebase as an example and for future referencing.

These test the logic of the modem driver through the use of the ``fake_machine.UART`` test
class by mimicking modem responses for commands and testing the expected results.

This can be run by copying the ``teu`` module to the ``src/lib/`` folder of the quilty
environmental embedded software and this test into the ``src/test/`` folder, and then running it
with ``unittest.main('test/test_modem_unix')`` from src."""

from lib import unittest
from lib import teu
from lib.teu import fake_machine

# Shadow the builtins immediately to prevent modem_driver from importing builtin machine and time
teu.shadow_builtins()
# fake_machine.shadow_builtin_machine()

from drivers import modem as modem_driver
from services import modem as modem_services
from services import config as config_services


def at_response(*lines):
    """Build the raw bytes for an expected response from a real Modem for a given
    (echo, [itr,] frc, [urc]) sequence, e.g. ``at_response("AT+CSQ", "+CSQ: 15,99", "OK")``.

    `send_command_read()` splits on "\\r\\n", strips, and drops empty items, so joining lines
    with "\\r\\n" (and a trailing one) reproduces expected parsing result.
    """
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


class TestModemWithFake(unittest.TestCase):
    """
    Test class for the modem driver logic using the ``fake_machine.UART`` test class to mimic
    certain responses, including faults.
    """

    def setUp(self):
        """Setup function that runs before each test, queues a UART registry clean. Also
        creates the Modem to test and stores its created UART fake."""

        # Reset registry to ensure nothing leaks between test objects.
        # Technically shouldn't affect much as the driver empties the UART before sending commands
        fake_machine.UART.reset_registry()
        self.addCleanup(fake_machine.UART.reset_registry)

        # Creating the UART and modem in the test setUp saves doing it at the start of tests.
        # Can either create the UART before modem, or create the modem and then customize
        # the UART it created (which will be one of our test doubles)
        #
        # If storing the modems created UART it helps to add a type hint for the fake_machine.UART
        # so editor completions will work
        self.modem = modem_driver.Modem()
        self.uart: fake_machine.UART = self.modem.serial

    # ------ modem.online() tests

    def test_online_true_when_modem_responds_ok(self):
        """Test that the ``modem.online()`` can handle the basic OK AT response from our fake UART"""
        self.uart.set_mappings({"AT\r": at_response("AT", "OK")})
        self.assertTrue(self.modem.online())

    def test_online_false_when_modem_responds_invalid(self):
        """Check that ``modem.online()`` returns false when a modem makes a response that
        doesn't contain OK
        """
        self.uart.response_strategy = fake_machine.uart.ConstantResponseStrategy("BAD")
        self.assertFalse(self.modem.online())

    def test_power_on_skips_pulse_when_already_online(self):
        """Test that ``modem.power_on()`` checks ``modem.online()`` first and returns without
        touching the power pin or waiting for a greeting.
        """
        self.uart.set_mappings({"AT\r": at_response("AT", "OK")})
        self.assertTrue(self.modem.power_on())
        # If online check is successful then read_greeting_text will never write to UART
        self.assertEqual(self.uart.get_written_data(), b"AT\r")

    # ----- Greeting text tests

    def test_read_greeting_text_success(self):
        """Test that driver can read the greeting text properly.

        Calling ``read_greeting_text()`` manually as text appears in the real modems buffer
        automatically after powering on and the method reads from the device without writing,
        so push response directly.
        """
        greeting = modem_driver.Modem.MODEM_GREETING_TEXT.encode("utf-8") + b"\r\n"
        self.uart.push_response(greeting)
        self.assertTrue(self.modem.read_greeting_text(timeout=1))

    def test_read_greeting_text_uses_online_on_failure(self):
        """Test that when ``modem.read_greeting_text()`` fails it falls back to calling
        ``modem.online()`` and returning the response.

        Set a mapping for the OK response to test and check the write_buf to make sure a
        command was sent.
        """
        self.uart.set_mappings({"AT\r": at_response("AT", "OK")})
        self.assertTrue(self.modem.read_greeting_text(timeout=1))
        self.assertEqual(self.uart.get_written_data(), b"AT\r")

    # ------ Testing signal quality and connected functions
    def test_signal_quality_parsing(self):
        """Test that ``modem.signal_quality()`` works properly and parses the response."""
        self.uart.set_mappings({"AT+CSQ\r": at_response("AT+CSQ", "+CSQ: 15,99", "OK")})
        self.assertEqual((15, 99), self.modem.signal_quality())

    def test_connected_with_faked_responses(self):
        """Test that ``modem.connected()`` works with mapped responses.

        This requires setting up responses for 3 different commands:
          + ``modem.registered()``: Uses ``AT+CEREG``
          + ``modem.extended_signal_quality()``: Uses ``AT+CESQ``
          + ``modem.pdp_address()``: Uses ``AT+CGPADDR``

        Good demonstration for needing multiple mappings :p
        """
        self.uart.set_mappings(
            {
                "AT+CEREG?\r": at_response("AT+CEREG?", "+CEREG: 0,1", "OK"),
                "AT+CESQ\r": at_response("AT+CESQ", "+CESQ: 99,99,255,255,20,50", "OK"),
                "AT+CGPADDR\r": at_response("AT+CGPADDR", "+CGPADDR: 1,100.65.227.228", "OK"),
            }
        )
        self.assertTrue(self.modem.connected())

    def test_connected_false_when_not_registered(self):
        """Test that ``modem.connected()`` returns false when +CEREG network registration
        status returns <stat>=0, meaning not registered to a network"""
        self.uart.set_mappings({"AT+CEREG?\r": at_response("AT+CEREG?", "+CEREG: 0,0", "OK")})
        self.assertFalse(self.modem.connected())

    def test_connected_false_when_esq_out_of_range(self):
        """Test that ``modem.connected()`` returns false when the modem is registered with a
        network but the +CESQ extended signal quality command returns rsrq and rsrp values that
        are out of range."""
        self.uart.set_mappings(
            {
                "AT+CEREG?\r": at_response("AT+CEREG?", "+CEREG: 0,1", "OK"),
                "AT+CESQ\r": at_response("AT+CESQ", "+CESQ: 99,99,255,255,99,99", "OK"),
            }
        )
        self.assertFalse(self.modem.connected())

    # ------- Testing MQTT methods -----------------------

    def test_mqtt_profile_reset_succeeds(self):
        """Test that responding properly to the +UMQTTNV reset command returns true"""
        self.uart.set_mappings(
            {"AT+UMQTTNV=0\r": at_response("AT+UMQTTNV=0", "+UMQTTNV: 0,1", "OK")}
        )
        self.assertTrue(self.modem.mqtt_profile_reset())

    @unittest.expectedFailure
    def test_mqtt_profile_set(self):
        """Test the ``modem.mqtt_profile_set()`` works by faking the +UMQTT opcode responses.

        NOTE - this currently will fail as the mqtt_profile_set() method has a bug where the
        'command' variable is reused when building the command so it will always be invalid
        when searching for it in the iterator, test marked as expectedFailure
        """
        print("Expected failure will occur, due to mqtt_profile_set() bug")
        self.uart.set_mappings(
            {
                'AT+UMQTT=0,"client-1"\r': at_response(
                    'AT+UMQTT=0,"client-1"', "+UMQTT: 0,1", "OK"
                ),
                'AT+UMQTT=2,"broker.example.com"\r': at_response(
                    'AT+UMQTT=2,"broker.example.com"', "+UMQTT: 2,1", "OK"
                ),
                "AT+UMQTT=10,60\r": at_response("AT+UMQTT=10,60", "+UMQTT: 10,1", "OK"),
            }
        )
        self.assertTrue(self.modem.mqtt_profile_set("client-1", "broker.example.com"))

    def test_mqtt_login_succeeds(self):
        """Test that the ``modem.mqtt_login()`` method works by faking the +UMQTTC command
        response for opcode 1 (login)
        """
        self.uart.set_mappings(
            {"AT+UMQTTC=1\r": at_response("AT+UMQTTC=1", "+UMQTTC: 1,1", "OK", "+UUMQTTC: 1,0")}
        )
        self.assertTrue(self.modem.mqtt_login())

    def test_mqtt_login_fails_when_false_login_value(self):
        """Test that ``modem.mqtt_login`` returns false when the MQTT_result is 1 (command
        succeeded) but the URC login_result is 1 (login failed, rejected by broker).
        """
        self.uart.set_mappings(
            {"AT+UMQTTC=1\r": at_response("AT+UMQTTC=1", "+UMQTTC: 1,1", "OK", "+UUMQTTC: 1,1")}
        )
        self.assertFalse(self.modem.mqtt_login())

    def test_mqtt_publish_succeeds(self):
        """Test that ``modem.mqtt_publish()`` works by faking a +UMQTTC command response for
        opcode 2 (publish)"""
        cmd = 'AT+UMQTTC=2,0,0,"weather/station1","payload"'
        self.uart.set_mappings({cmd + "\r": at_response(cmd, "+UMQTTC: 2,1", "OK")})
        self.assertTrue(self.modem.mqtt_publish("weather/station1", "payload"))

    # ------- File write tests ---------

    def test_file_write_succeeds(self):
        """Test that ``modem.file_write()`` works and returns true when faking a succesful file
        write by mapping the +UDWNFILE and +UDELFILE commands."""
        data = "file contents"
        self.uart.set_mappings(
            {
                # Don't /need/ UDELFILE cuz it'll time out without but keep it to avoid waiting
                # for the timeout
                'AT+UDELFILE="test.txt"\r': at_response('AT+UDELFILE="test.txt"', "OK"),
                'AT+UDWNFILE="test.txt",{0}\r'.format(len(data)): at_response(
                    'AT+UDWNFILE="test.txt",{0}'.format(len(data)), "OK"
                ),
                # The raw file payload is written directly and read back with a single read()
                # NOTE - would be a good usage for the strict mappings here, making sure the data
                #  gets written
                data: b"OK\r\n",
            }
        )
        self.assertTrue(self.modem.file_write("test.txt", data))

    def test_file_write_raises_on_failure(self):
        """Test that ``modem.file_write()`` raises the expected ModemFileError when response
        doesn't include OK."""
        data = "file contents"
        self.uart.set_mappings(
            {
                'AT+UDELFILE="test.txt"\r': at_response('AT+UDELFILE="test.txt"', "OK"),
                'AT+UDWNFILE="test.txt",{0}\r'.format(len(data)): at_response(
                    'AT+UDWNFILE="test.txt",{0}'.format(len(data)), "OK"
                ),
                data: b"ERROR\r\n",
            }
        )
        with self.assertRaises(modem_driver.Modem.ModemFileError):
            self.modem.file_write("test.txt", data)

    # ------- Temperature tests --------
    #
    # Just a few tests for the ``modem.temperature()`` method, to test its parsing

    def test_temperature_parses_celsius(self):
        """Test that ``modem.temperature()`` properly parses and returns a temperature in
        Celsius from a +UTEMP command.
        """
        self.uart.set_mappings({"AT+UTEMP?\r": at_response("AT+UTEMP?", "+UTEMP: 253,0", "OK")})
        self.assertEqual(25.3, self.modem.temperature())

    def test_temperature_none_when_modem_errors(self):
        self.uart.set_mappings({"AT+UTEMP?\r": at_response("AT+UTEMP?", "ERROR")})
        self.assertIsNone(self.modem.temperature())

    def test_temperature_none_on_unparsable_value(self):
        """Test that when ``modem.temperature()`` receives a non-numeric reading it catches the
        ValueError and returns None"""
        self.uart.set_mappings(
            {"AT+UTEMP?\r": at_response("AT+UTEMP?", "+UTEMP: not-a-number", "OK")}
        )
        self.assertIsNone(self.modem.temperature())

    # -------- Testing dateTime()

    def test_datetime_read_parses_modem_clock(self):
        """Test that ``modem.dateTime()`` can read a datetime UTC string from the modem using the
        +CCLK command, parse and convert it into NZST and returns a proper tuple.

        Datetime is in format of 'yy/MM/dd,hh:mm:ss+TZ'.
        """
        self.uart.set_mappings(
            {"AT+CCLK?\r": at_response("AT+CCLK?", '+CCLK: "26/01/15,10:30:00+00"', "OK")}
        )
        result = self.modem.datetime()
        self.assertIsNotNone(result, "result should not be none")
        year, month, day, hour, minute, second = result[:6]
        self.assertEqual((2026, 1, 15, 22, 30, 0), (year, month, day, hour, minute, second))

    def test_datetime_read_none_when_clock_never_set(self):
        """Test that a modem returning a datetime where the year is '80' (for 2080) makes the
        ``modem.datetime()`` function properly return None, as year 2080 is the
        factory-programmed epoch value which represents that the time hasn't been programmed yet.
        """
        self.uart.set_mappings(
            {"AT+CCLK?\r": at_response("AT+CCLK?", '+CCLK: "80/01/06,00:00:00+00"', "OK")}
        )
        self.assertIsNone(self.modem.datetime())

    def test_datetime_read_none_on_modem_error(self):
        """Test that ``modem.datetime()`` returns None when receiving an error."""
        self.uart.set_mappings({"AT+CCLK?\r": at_response("AT+CCLK?", "ERROR")})
        self.assertIsNone(self.modem.datetime())

    def test_datetime_set_sends_nzst_converted_to_utc(self):
        """Test that setting a datetime using ``modem.datetime()`` properly converts the time
        to UTC and sets it.

        NOTE - this test wouldn't pass on the base UNIX port due to time epoch, but will succeed
        with the custom time module
        """
        # print("Expected failure will occur, due to time epoch")
        self.uart.set_mappings(
            {
                'AT+CCLK="26/03/01,02:30:00+00"\r': at_response(
                    'AT+CCLK="26/03/01,02:30:00+00"', "OK"
                )
            }
        )
        # 2026-03-01 14:30:00 NZST -> 2026-03-01 02:30:00 UTC
        result = self.modem.datetime((2026, 3, 1, 14, 30, 0, 0, 0))
        self.assertIsNone(result)  # None indicates a successful set, not a failure
        self.assertEqual(
            self.uart.get_written_data(), 'AT+CCLK="26/03/01,02:30:00+00"\r'.encode("utf-8")
        )


# ------- Modem send_command_* function tests ----------
class TestModemCommandHelpers(unittest.TestCase):
    """Test class for testing the functionality of the individual modem helper functions like
    ``modem.send_command_parse`` etc."""

    def setUp(self):
        fake_machine.UART.reset_registry()
        self.addCleanup(fake_machine.UART.reset_registry)
        self.modem = modem_driver.Modem()
        self.uart: fake_machine.UART = self.modem.serial

    def test_send_command_read_joins_lines_with_double_space(self):
        """Test that ``modem.send_command_read()`` joins the command lines which are normally
        split with '\r\n' into one string using double spaces. Testing this as other functions
        like ``modem.send_command_parse()`` rely on splitting on the two spaces."""
        self.uart.set_mappings({"AT+CSQ\r": at_response("AT+CSQ", "+CSQ: 15,99", "OK")})
        self.assertEqual("AT+CSQ  +CSQ: 15,99  OK", self.modem.send_command_read("+CSQ"))

    # ------ send_command_parse tests ---------

    def test_send_command_parse_no_itr(self):
        """Test that when ``modem.send_command_parse()``` receives an echo + OK with no
        information text response it should parse with itr=None rather than an empty dict."""
        self.uart.set_mappings({"AT+CFUN=1\r": at_response("AT+CFUN=1", "OK")})
        echo, itr, frc, urc = self.modem.send_command_parse("+CFUN=1")
        self.assertEqual(echo, "AT+CFUN=1")
        self.assertIsNone(itr)
        self.assertEqual(frc, "OK")
        self.assertIsNone(urc)

    def test_send_command_parse_with_itr(self):
        """Test that ``modem.send_command_parse()`` properly parses a response containing itr."""
        self.uart.set_mappings({"AT+CSQ\r": at_response("AT+CSQ", "+CSQ: 15,99", "OK")})
        echo, itr, frc, urc = self.modem.send_command_parse("+CSQ")
        self.assertEqual(echo, "AT+CSQ")
        self.assertEqual(itr, {"+CSQ": ["15", "99"]})
        self.assertEqual(frc, "OK")
        self.assertIsNone(urc)

    def test_send_command_parse_with_urc(self):
        """Test that ``modem.send_command_parse()`` properly parses a response that contains an
        Unsolicited Return Code (URC) at the end."""
        self.uart.set_mappings(
            {"AT+UMQTTC=1\r": at_response("AT+UMQTTC=1", "+UMQTTC: 1,1", "OK", "+UUMQTTC: 1,0")}
        )
        echo, itr, frc, urc = self.modem.send_command_parse("+UMQTTC=1")
        self.assertEqual("AT+UMQTTC=1", echo)
        self.assertEqual({"+UMQTTC": ["1", "1"]}, itr)
        self.assertEqual("OK", frc)
        self.assertEqual("+UUMQTTC: 1,0", urc)

    def test_send_command_parse_pads_itr_values_to_nval(self):
        """Test that when send_command_parse receives a response with less itr values than the
        provided `nval` it pads the dict with empty strings."""
        self.uart.set_mappings({"AT+CEREG?\r": at_response("AT+CEREG?", "+CEREG: 0,1,2", "OK")})
        _, itr, _, _ = self.modem.send_command_parse("+CEREG?", nval=9)
        self.assertEqual(itr, {"+CEREG": ["0", "1", "2", "", "", "", "", "", ""]})

    def test_send_command_parse_defaults_when_echo_missing_entirely(self):
        """Test that ``modem.send_command_parse()`` returns default 4-None list when response
        does not contain the command echo.

        NOTE - for some reason on failure the function returns a list of 4 Nones rather than a
          tuple, not sure why.
        """
        self.uart.set_mappings({"AT+CSQ\r": at_response("SOMETHING UNEXPECTED", "OK")})
        self.assertEqual(self.modem.send_command_parse("+CSQ"), [None, None, None, None])

    def test_send_command_parse_fails_when_urc_precedes_echo(self):
        """Test the known limitation in ``modem.send_command_parse()`` where a URC preceding
        the echo breaks the parsing and causes the function to return with the None defaults list.
        """
        self.uart.set_mappings(
            {"AT+CSQ\r": at_response("+CREG: 1", "AT+CSQ", "+CSQ: 15,99", "OK")}
        )
        self.assertEqual(self.modem.send_command_parse("+CSQ"), [None, None, None, None])

    def test_send_command_parse_frc_returned_unchanged_on_cme_error(self):
        """When ``modem.send_command_parse()`` receives a +CME ERROR response for the frc it
        currently keeps the CME for the frc instead of raising, test it does this."""
        self.uart.set_mappings({"AT+CFUN?\r": at_response("AT+CFUN?", "+CME ERROR: 123")})
        echo, itr, frc, urc = self.modem.send_command_parse("+CFUN?")
        self.assertEqual(echo, "AT+CFUN?")
        self.assertEqual(frc, "+CME ERROR: 123")

    def test_send_command_parse_single_item_response_is_treated_as_timeout(self):
        """Test that when only the echo ever comes back (num_items == 1) itr/frc/urc all
        default to None."""
        self.assertEqual(("AT", None, None, None), self.modem.send_command_parse(""))


if __name__ == "__main__":
    unittest.main()
