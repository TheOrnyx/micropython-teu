"""esp_time.py

Modified version of built-in time which matches output of ESP32 port version by adjusting the
Epoch to be the year 2000 and removing the extra item from the time tuples.

Has a method to shadow the builtin time rather than relying on sys path shadowing since easier
to manage in tests (explicit call rather than path configuration), but see if better to just do
path shadowing.

Provides custom implementations of ``localtime()``, ``gmtime()``, ``mktime()``, ``time()``,
and ``time_ns()``. Remaining functions (like the sleep and tick functions) are re-exported from
built-in.

Functions are implemented as custom implementations rather than shims around the built-in
versions as the built-in versions are very dependent on the OS timezone and so would need to
work around the timezone, easier to just implement by hand.

The time calculations are based on the Howard Hinnant date algorithms.
https://howardhinnant.github.io/date_algorithms.html

TODO - could allow users to set a custom current time but might not be too useful.
"""

# Suppress the pyright and pylint warnings when we change the function signatures and redefine
# pyright: reportAssignmentType=false
# pylint: disable=wildcard-import, function-redefined, unused-wildcard-import

import sys

# Import all built-in time methods so we only need to re-implement the problematic methods
# and can leave others as default.
_path = sys.path
sys.path = ()
try:
    from time import *

    import time as _time  # Keep local version for getting current time for conversions
finally:
    sys.path = _path
    del _path


def shadow_builtin_time():
    """Shadows the builtin ``time`` module by setting the ``sys.modules`` entry for time to
    this module.

    So ``import time`` calls will import this module instead. Should be called before any other
    imports occur or tests run as if the builtin is imported first it will take priority until
    imported again.

    Gets called by the toplevel ``teu.shadow_builtins()`` method.
    """
    sys.modules["time"] = sys.modules[__name__]


# --- Constants used for calculating the times

EPOCH_YEAR = 2000  # Year of the epoch used by the ESP32 (and other baremetal) ports.

# Seconds between the UNIX epoch (1970-01-01) and the ESP32 epoch (2000-01-01), UTC.
EPOCH_OFFSET = 946684800

# Offset between the host clock and an ESP32-epoch timestamp. Zero when already running on a
# port whose epoch is 2000 (i.e. on-device), so importing this module there won't break anything.
_HOST_OFFSET = EPOCH_OFFSET if _time.gmtime(0)[0] != EPOCH_YEAR else 0
_HOST_OFFSET_NS = _HOST_OFFSET * 1000000000

# Number of seconds per day
_SECS_PER_DAY = 86400

# Days from 0000-03-01 (the shifted epoch the conversions count from) to 2000-01-01.
# 0000-03-01 is used as the base epoch for the Howard Hinnant days_from_civil calculation.
_DAYS_SHIFT = 730425

# 2000-01-01 was a Saturday, and weekday is 0-6 for Mon-Sun.
_EPOCH_WEEKDAY = 5


def _days_from_civil(year, month, mday):
    """Calculate and return number of days between 2000-01-01 and the given proleptic Gregorian
    date.
    """
    year -= month <= 2
    era = year // 400
    yoe = year - era * 400  # [0, 399]
    doy = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + mday - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - _DAYS_SHIFT


def _civil_from_days(days):
    """Inverse of `_days_from_civil`, returns a ``(year, month, mday)`` tuple."""
    days += _DAYS_SHIFT
    era = days // 146097  # TODO - check negative works here
    doe = days - era * 146097  # [0, 146096]
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365  # [0, 399]
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)  # [0, 365]
    mp = (5 * doy + 2) // 153  # [0, 11], March-based month
    mday = doy - (153 * mp + 2) // 5 + 1  # [1, 31]
    month = mp + 3 if mp < 10 else mp - 9  # [1, 12]
    return yoe + era * 400 + (month <= 2), month, mday


def gmtime(secs=None):
    """Convert seconds since the 2000 epoch into an 8-tuple, same as the ESP32 port.

    Returns `(year, month, mday, hour, minute, second, weekday, yearday)`, same tuple size as
    ESP32.

    If `secs` is None the current time is used and properly converted to the ESP32 epoch before
    returning the tuple.
    """
    if secs is None:  # Get converted current time in secs since ESP32 epoch
        secs = time()

    # Separate base datetime info from division
    days, rem = divmod(int(secs), _SECS_PER_DAY)
    hour, rem = divmod(rem, 3600)
    minute, second = divmod(rem, 60)
    year, month, mday = _civil_from_days(days)
    return (
        year,
        month,
        mday,
        hour,
        minute,
        second,
        (days + _EPOCH_WEEKDAY) % 7,
        days - _days_from_civil(year, 1, 1) + 1,
    )


def localtime(secs=None):
    """Alias of `gmtime`.

    The ESP32 port has no timezone support, `localtime` and `gmtime` both read the RTC and so
    return identical tuples (``localtime(0) == gmtime(0) == (2000, 1, 1, 0, 0, 0, 5, 1)``).
    """
    return gmtime(secs)


def mktime(date_time_tuple):
    """Inverse of `localtime`/`gmtime`, returns seconds since the 2000 epoch for a date-time
    tuple.

    Accepts a tuple of length 8 or 9 (accepts a 9-tuple for support with regular UNIX port,
    the extra daylight-savings UNIX item is ignored, as are `weekday` and `yearday`).

    Out-of-range fields are normalised the way the underlying ports do, e.g. month 13 rolls
    into the next year.
    """
    if not 8 <= len(date_time_tuple) <= 9:
        raise TypeError("mktime needs a tuple of length 8 or 9")
    year = int(date_time_tuple[0])
    month = int(date_time_tuple[1])
    mday = int(date_time_tuple[2])
    hour = int(date_time_tuple[3])
    minute = int(date_time_tuple[4])
    second = int(date_time_tuple[5])
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1
    days = _days_from_civil(year, month, mday)
    return days * _SECS_PER_DAY + hour * 3600 + minute * 60 + second


def time():
    """Returns the seconds from the 2000 epoch to current time, returns as an int like the
    ESP32 does, rather than the UNIX ports float return."""
    return int(_time.time()) - _HOST_OFFSET


def time_ns():
    """Returns nanoseconds since the 2000 epoch, as an int."""
    return _time.time_ns() - _HOST_OFFSET_NS
