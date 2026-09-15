"""test_esp_time.py

Tests that ensure that the custom ``time`` module (``esp_time.py``) works properly and gives
the same results as the ESP32 port does."""

import unittest

try:
    import teu

    teu.shadow_builtins()  # Now an import time will import esp_time
except ImportError:
    teu = None
    pass

import time


class TestEspTime(unittest.TestCase):

    def test_builtin_was_shadowed(self):
        """Test that the builtin time was successfully shadowed by ``teu.esp_time``.

        This test has a guard to skip if ``teu`` wasn't available for import, so the rest of
        the tests can be ran on the ESP32 to validate.
        """
        if teu is None:
            self.skipTest("Teu not available, probably running on ESP32")
        self.assertIs(time, teu.esp_time)

    def test_tuple_length_matches_esp(self):
        """Test that the return tuples for ``localtime()`` and ``gmtime()`` are the same size
        as the ESP32, only 8 items instead of default unix 9 items."""
        self.assertEqual(len(time.localtime(0)), 8)
        self.assertEqual(len(time.gmtime(0)), 8)

    def test_epoch_matches_esp(self):
        """Test that the epoch for our custom `esp_time` matches the ESP32 time epoch of 2000
        instead of the builtin UNIX epoch of 1970.

        Can be found by calling ``time.localtime(0)`` which gives epoch, epoch of gmtime
        should be the same.
        """
        expected_epoch = (2000, 1, 1, 0, 0, 0, 5, 1)
        self.assertEqual(time.localtime(0), expected_epoch)
        self.assertEqual(time.gmtime(0), expected_epoch)

    def test_gmtime_and_localtime_produce_same_result(self):
        """The ESP32 doesn't have support for timezones in the time module, so ``gmtime()`` and
        ``gmtime()`` should give the same result for a given input.

        Will test both for output when given `secs` and the output for current time (which will
        be trimmed down to first 5 items as can't guarantee both calls happen within same second)
        """
        secs = 175741
        expected = (2000, 1, 3, 0, 49, 1, 0, 3)
        self.assertEqual(time.localtime(secs), time.gmtime(secs))
        self.assertEqual(time.localtime(secs), expected)
        self.assertEqual(time.gmtime(secs), expected)

        # Trim off seconds, weekday and weekyear as not needed and can't guarantee same second
        gmt, localt = time.gmtime()[:5], time.localtime()[:5]

        # TODO - could add a like 3-pass equality while loop here if we ever run into problems
        #  on hour ticking over between calls, which shouldn't happen
        self.assertEqual(gmt, localt)

    def test_mktime_outputs_match(self):
        """Test that ``mktime()`` outputs for localtime and gmtime both match.

        Since ``mktime()`` uses the localtime for the conversion the UNIX port gives different
        results for a provided gmtime, and passing the mktime secs back into gmtime gives a
        different result. This doesn't happen on the ESP32 as it doesn't use timezone."""
        secs = 175741
        expected = (2000, 1, 3, 0, 49, 1, 0, 3)

        gm1 = time.gmtime(secs)
        gm1_secs = time.mktime(gm1)
        gm2 = time.gmtime(gm1_secs)
        self.assertEqual(gm1, expected)
        self.assertEqual(gm1_secs, secs)
        self.assertEqual(gm2, gm1)

        lt1 = time.localtime(secs)
        lt1_secs = time.mktime(lt1)
        lt2 = time.localtime(lt1_secs)
        self.assertEqual(lt1, gm1)
        self.assertEqual(lt1_secs, gm1_secs)
        self.assertEqual(lt2, lt1)
