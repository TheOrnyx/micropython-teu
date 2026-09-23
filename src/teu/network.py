"""network.py

Very basic stubbed out implementation of the esp32 ``network`` module which is used for
``espnow`` code and is not available on UNIX port.

I am implementing this stubbed module as `espnow` needs a network config set-up otherwise it
causes a crash when activating. This means that if any code uses espnow it will likely also
``import network`` which would cause an ImportError. So am making a basic stub just so we can
support more code."""

# pylint: disable=global-statement

import sys


def register_network_module():
    """Register this module in ``sys.modules`` by adding it as the entry for ``'network'``,
    so going ``import network`` will import this module. Gets called by ``teu.shadow_builtins()``.
    """
    sys.modules["network"] = sys.modules[__name__]


# Module constants
STA_IF = 0
AP_IF = 1
MODE_11B = 1
MODE_11G = 2
MODE_11N = 4
MODE_LR = 8
AUTH_OPEN = 0
AUTH_WEP = 1
AUTH_WPA_PSK = 2
AUTH_WPA2_PSK = 3
AUTH_WPA_WPA2_PSK = 4
AUTH_WPA2_ENTERPRISE = 5
AUTH_WPA3_PSK = 6
AUTH_WPA2_WPA3_PSK = 7
AUTH_WAPI_PSK = 8
AUTH_OWE = 9
AUTH_WPA3_ENT_192 = 10
AUTH_WPA3_EXT_PSK = 11
AUTH_WPA3_EXT_PSK_MIXED_MODE = 12
AUTH_MAX = 17
PHY_LAN8710 = 0
PHY_LAN8720 = 1
PHY_IP101 = 2
PHY_RTL8201 = 3
PHY_DP83848 = 4
PHY_KSZ8041 = 5
PHY_KSZ8081 = 6
PHY_LAN8670 = 7
PHY_GENERIC = 8
PHY_KSZ8851SNL = 100
PHY_DM9051 = 101
PHY_W5500 = 102
ETH_INITIALIZED = 0
ETH_STARTED = 1
ETH_STOPPED = 2
ETH_CONNECTED = 3
ETH_DISCONNECTED = 4
ETH_GOT_IP = 5
STAT_IDLE = 1000
STAT_CONNECTING = 1001
STAT_GOT_IP = 1010
STAT_NO_AP_FOUND = 201
STAT_NO_AP_FOUND_IN_RSSI_THRESHOLD = 212
STAT_NO_AP_FOUND_IN_AUTHMODE_THRESHOLD = 211
STAT_NO_AP_FOUND_W_COMPATIBLE_SECURITY = 210
STAT_WRONG_PASSWORD = 202
STAT_BEACON_TIMEOUT = 200
STAT_ASSOC_FAIL = 203
STAT_CONNECT_FAIL = 203
STAT_HANDSHAKE_TIMEOUT = 204

# Stub attributes
_COUNTRY_CODE = "XX"
_HOSTNAME = "mpy-esp32"
_DNS_SERVER = "0.0.0.0"


def country(code=None) -> str | None:
    """Get or set country code. Raises if `code` is provided and isn't length 2.

    Stub will save the inputted code in `_country_code`, and return it when `code` is omitted.
    Default is worldwide 'XX'.
    """
    global _COUNTRY_CODE
    if code is not None:
        if len(code) != 2:
            raise ValueError("Invalid country code length")  # Technically no message on board
        _COUNTRY_CODE = code
        return None

    return _COUNTRY_CODE


def hostname(name=None) -> str | None:
    """Get or set the hostname for the device. Returns None if setting hostname. Raises if
    `name` length is greater than 32.

    Stub starts with default 'mpy-esp32' hostname and updates the `_hostname` if `name` provided.
    """
    global _HOSTNAME
    if name is not None:
        if len(name) > 32:
            raise ValueError
        _HOSTNAME = name
        return None

    return _HOSTNAME


def ipconfig(param=None, dns=None):
    """Either get or set global ip-configuration values. If `param` is specified than read and
    return the value. Raises on unknown config params.

    The ESP32 version of this only supports reading and writing the `dns` config value which
    has a default of '0.0.0.0', stub will support reading and updating it, but won't validate.
    Also this isn't exactly board accurate as the board uses kwargs to look up but I'll just
    use keyword params as it'll reject unknown anyway.
    """
    global _DNS_SERVER
    if param is not None:
        if param == "dns":
            return _DNS_SERVER
        raise ValueError("unexpected key")

    if dns is not None:
        _DNS_SERVER = dns
    return None


def phy_mode(arg=None) -> None:
    """ESP32 version of phy-mode just returns None and doesn't do anything, stub does same."""
    return None


def _dummy_ipconfig(param=None, **kwargs):
    """Base dummy version of ``ipconfig()`` for WLAN and LAN (see ``WLAN.ipconfig()`` for more
    info on method). Separated into its own method to avoid code duplication.

    Just validates that the params are allowed and returns canned responses for reads."""
    allowed_params = {"dhcp4": False, "addr4": ("0.0.0.0", "0.0.0.0"), "gw4": "0.0.0.0"}
    if param is not None:
        if param not in allowed_params:
            raise ValueError("unexpected key")
        return allowed_params[param]

    # Validate kwargs
    for key in kwargs:
        if key not in allowed_params:
            raise ValueError("unexpected key")
    return None


class WLAN:
    """Basic stubbed out dummy implementation of the ``network.WLAN`` class for Wi-Fi network
    stuff.

    This class seems to be able to be in either STA station mode or AP access point mode,
    with method availibility and functionality being different between these modes.
    """

    # Class constants
    IF_STA = 0
    IF_AP = 1
    SEC_OPEN = 0
    SEC_WEP = 1
    SEC_WPA = 2
    SEC_WPA2 = 3
    SEC_WPA_WPA2 = 4
    SEC_WPA2_ENT = 5
    SEC_WPA3 = 6
    SEC_WPA2_WPA3 = 7
    SEC_WAPI = 8
    SEC_OWE = 9
    SEC_WPA3_ENT_192 = 10
    SEC_WPA3_EXT_PSK = 11
    SEC_WPA3_EXT_PSK_MIXED_MODE = 12
    SEC_DPP = 13
    SEC_WPA3_ENT = 14
    SEC_WPA2_WPA3_ENT = 15
    SEC_WPA_ENT = 16
    PROTOCOL_DEFAULT = 7
    PROTOCOL_LR = 8
    PM_NONE = 0
    PM_PERFORMANCE = 1
    PM_POWERSAVE = 2
    BANDWIDTH_20 = 1
    BANDWIDTH_40 = 2
    BANDWIDTH_80 = 3
    BANDWIDTH_160 = 4
    BANDWIDTH_80_80 = 5

    def __init__(self, interface_id=IF_STA):
        """Creates a WLAN network interface object. `interface_id` can either be ``IF_STA`` for
        station, or ``IF_AP`` for access point. Default is station. Raises on invalid
        `interface_id`.

        Stub stores interface_id and sets initial values for a few basic stub attributes (like
        active)
        """
        if interface_id not in (self.IF_STA, self.IF_AP):
            raise ValueError("invalid WLAN interface identifier")

        self.interface_id = interface_id
        self._active = False

    def active(self, is_active=None) -> bool:
        """Activate or deactivate the network interface. Returns active status.

        Stub will store the `is_active` in `_active` if provided and return `_active` value
        after updating, like board.
        """
        if is_active is not None:
            self._active = bool(is_active)
        return self._active

    def connect(self, ssid=None, key=None, *, bssid=None) -> None:
        """Connect to the specified wireless network, using specified key.

        Stub will raise the basic OSError if not active, otherwise will just return None.

        I think board also raises if already connected to smth, and also caches the previous
        connect ssid but not doing these for now should be fine for basic stub, future work can
        do.
        """
        self._raise_if_not_active("Wifi Not Started")

    def disconnect(self) -> None:
        """Disconnect from wireless network, stub does nothing."""
        return None

    def scan(self):
        """Scan for available wireless networks, board returns found networks as list of 6-item
        tuples in following form: ``(ssid, bssid, channel, RSSI, security, hidden)``.

        Stub will just raise if not active and return empty List
        """
        self._raise_if_not_active("STA must be active")
        return []

    def status(self, param=None):
        """Returns status of current connection. If no `param` provided then will return
        network link status, which will be one of a subset of ``STAT_*`` constants. `AP`
        objects return None when no param present.

        If `param` is provided it must either be 'rssi' for STA or `stations` for AP. Rssi
        returns int signal strength indicator value, stations returns list of connected stations.

        For simplicity stub will just do basic returns for the no `param` (None for AP,
        either IDLE or NO_AP for ST), will do the validation for `param` being valid but won't
        do mode validations.
        """
        if param is None:
            if self.interface_id is self.IF_AP:
                return None
            return STAT_NO_AP_FOUND if self._active else STAT_IDLE

        if param == "rssi":
            return 0
        if param == "stations":
            return []

        raise ValueError("unknown status param")

    def isconnected(self) -> bool:
        """Returns connection status as bool. Stub just returns False"""
        return False

    def ifconfig(self, config_tuple=None):
        """Get/set IP-level network interface parameters: IP address, subnet mask, gateway and
        DNS server. If `config_tuple` is not present then return a 4-tuple of following form:
        ``(ip, subnet, gateway, dns)``. Passing `config_tuple` as same 4-tuple sets params (
        esp32 also supports passing 'dhcp' instead of the tuple).

        For getting the stub will just return a tuple with all items as ``'0.0.0.0'``,
        otherwise will do nothing.

        TODO - do config_tuple validation
        """
        if config_tuple is None:
            return "0.0.0.0", "0.0.0.0", "0.0.0.0", "0.0.0.0"
        return None

    def config(self, param=None, **kwargs):
        """Get or set general network interface params. Raises if trying to query and set at
        same time.

        Supports quite a few different params, some are explained in docs but board supports a
        lot more. See the allowed_params tuple. On-board some are allowed to only be either
        read or written, but stub doesn't care.

        Stub will do basic validation to ensure `param` and kwargs are all valid options but
        will just return empty string for reading, not accurate but fine for basic stub.

        TODO - obviously implement the proper storing and reading of items, along with validation
        """
        allowed_params = (
            "mac",
            "ssid",
            "essid",
            "channel",
            "hidden",
            "security",
            "authmode",
            "ifname",
            "key",
            "password",
            "hostname",
            "dhcp_hostname",
            "max_clients",
            "reconnects",
            "reconnects",
            "txpower",
            "pm",
            "protocol",
            "bandwidth",
        )
        if param is not None and kwargs:
            raise TypeError("either pos or kw args are allowed")

        if param is not None and param not in allowed_params:
            raise ValueError("unknown config param")

        for key in kwargs:
            if key not in allowed_params:
                raise ValueError("unknown config param")

        return ""  # TODO - Not accurate but fine for now

    def ipconfig(self, param=None, **kwargs):
        """Get or set interface-specific IP-configuration interface parameters. ESP32 only
        supports 'dhcp4', 'addr4', and 'gw4'.

        Stub will validate params and return canned values for reading these params, will do
        nothing for setting. These will have different values and availabilities on-board
        depending on if in STA or AP mode, but just using STA as it supports all, should be
        fine for basic stub.

        Will call the ``_dummy_ipconfig()`` to reduce code duplication since LAN does same stuff.

        # TODO - implement proper AP handling logic
        # TODO - implement storing the config
        """
        return _dummy_ipconfig(param, **kwargs)

    # ---- CSI methods ----

    def csi_enable(self, buffer_size=16) -> None:
        """Enables CSI capture and allocates resources for received frames. Raises OSError if
        not active.

        Stub will raise if not active but will otherwise do nothing.
        """
        self._raise_if_not_active("Wifi Not Started")

    def csi_disable(self) -> None:
        """Disables CSI capture and cleans up resources, stub does nothing."""
        return None

    def csi_read(self, result=None):
        """Reads a CSI frame from the buffer. Returns a list of CSI frame data or None if no
        frames. If `result` is provided it should be a list to be reused (instead of allocating
        new for each return).

        Stub will just return None"""
        return None

    def csi_available(self) -> int:
        """Returns number of CSI frames available in buffer. Stub returns 0"""
        return 0

    def csi_dropped(self) -> int:
        """Returns the number of CSI frames dropped due to buffer overflow. Stub returns 0"""
        return 0

    def _raise_if_not_active(self, msg) -> None:
        """Helper method to raise an OSError with a specific `msg` if `_active` is not True."""
        if not self._active:
            raise OSError(msg)


class PPP:
    """Basic stubbed out dummy implementation of the ``network.PPP`` serial point-to-point
    protocol class.

    Basic implementation will just stub out the available functions and constants with basic
    return values and basic validations. Internal functionality might not be entirely
    board-accurate but should be good enough for dummy implementation.
    """

    # Class constants
    SEC_NONE = 0
    SEC_PAP = 1
    SEC_CHAP = 2
    AUTH_NONE = 0
    AUTH_PAP = 1
    AUTH_CHAP = 2

    def __init__(self, stream):
        """Creates a PPP object with a backing stream object.

        Board version validates that this is a valid stream object by checking the object
        protocol, not entirely sure how to do this in python besides just checking if they
        have specific methods, so won't validate. Will just store as attribute.
        """
        self.stream_obj = stream
        self._active = False

    def connect(
        self, security=SEC_NONE, user=None, key=None, authmode=None, username=None, password=None
    ) -> None:
        """Initiates a PPP connection. Stub does nothing.

        Board seems to have a bit of extra validation logic with the last 3 deprecated params
        overiding the first 3 if they're None, but not relevant for basic stub. Board also
        raises if already connected.
        """
        return None

    def disconnect(self) -> None:
        """Terminates connection. Stub does nothing."""
        return None

    def isconnected(self) -> bool:
        """Returns True if PPP link is connected, False otherwise. Stub just returns False."""
        return False

    def status(self) -> int:
        """Returns the PPP status. Stub will just return 0 for not active."""
        return 0

    def config(self, param=None, **kwargs):
        """Get or set parameter of PPP interface. ESP32 only supports 'stream' and 'ifname' for
        reading and 'stream' for writing. Basic stub will just validate allowed params and
        return empty strings for reading.

        TODO - implement proper config stuff
        """
        if param is not None and kwargs:
            raise TypeError("either pos or kw args are allowed")

        if param is not None:
            if param not in ("stream", "ifname"):
                raise ValueError("unknown config param")
            return ""

        for key in kwargs:
            if key != "stream":
                raise ValueError("unknown config param")
        return None

    def ipconfig(self, param=None, **kwargs):
        """PPP ipconfig, only allows reading of 'addr4' and 'gw4'. Stub will validate inputs
        and return canned responses for reads, raise on kwargs."""
        if kwargs:
            raise TypeError("setting properties not supported")
        if param is None:
            raise TypeError("must query one param")

        if param == "addr4":
            return "0.0.0.0", "255.255.255.255"
        if param == "gw4":
            return "0.0.0.0"
        raise ValueError("unexpected key")

    def ifconfig(self, config_tuple=None):
        """Same as ``WLAN.ifconfig()``, sets parameters with tuple or reads if not provided.
        Stub will just return canned tuple and do nothing for setting."""
        if config_tuple is None:
            return "0.0.0.0", "0.0.0.0", "255.255.255.255", "0.0.0.0"
        return None

    def poll(self, irq_arg=None) -> int:
        """Polls underlying stream for data and passes up PPP stack, returns length I believe.
        Stub will just return 0"""
        return 0

    def active(self, is_active=None) -> bool:
        """Deprecated method (but still included) to activate or deactivate interface and query
        status, same as ``WLAN.active()``. Stub will update `_active` if `is_active` present,
        and return it."""
        if is_active is not None:
            self._active = bool(is_active)
        return self._active


class _LAN:
    """Basic stubbed out dummy implementation of the ``network.LAN`` LAN class.

    This class is implemented slightly strangely on the ESP32. The ``network.LAN`` item isn't
    the class but rather the C function ``get_lan()`` which is effectively the LAN constructor.
    This means that the class can't actually be inspected through the ``network`` module.

    This implemenation also might not be very accurate as I'm unable to instantiate the LAN
    obejct on board as it requires a very specific setup (I think it requires an external PHY
    to be connected as well as exact params) otherwise it fails to install the driver and
    doesn't create the object. So I'm not able to easily test how methods work or what they
    return. So I'll mostly be copying implementations from the other classes.

    TODO - properly implement this stub in an accurate way.
    """

    def __init__(  # pylint: disable=redefined-builtin
        self,
        id_=None,
        mdc=None,
        mdio=None,
        reset=None,
        power=None,
        phy_addr=None,
        phy_type=None,
        spi=None,
        cs=None,
        int=None,
        ref_clk_mode=-1,
        ref_clk=None,
    ):
        """Construct new LAN object.

        On-board this is a bit complicated and pedantic, if the parameters aren't an exact set
        then it will crash. There's also quite a few validations that I won't implement due to
        time. Stub will just accept whatever input.

        TODO - improve this and add proper argument validation.
        """
        self.id_ = id_ if id_ is not None else 0

    def active(self, state=None):
        """Get and optionally set the interface active state. Stub will just return False."""
        return False

    def isconnected(self) -> bool:
        """Returns True if connected and up, False otherwise. Stub returns False."""
        return False

    def status(self) -> int:
        """Returns the LAN status int code. Stub returns 0 for INITIALIZED."""
        return 0

    def ifconfig(self, config_tuple=None):
        """Same as previous ifconfigs, allows reading or setting IP-level network params.

        Basic stub will be same as others, will just return canned tuple on read and do nothing
        on write."""
        if config_tuple is None:
            return "0.0.0.0", "0.0.0.0", "255.255.255.255", "0.0.0.0"
        return None

    def ipconfig(self, param=None, **kwargs):
        """Get or set network params, like other ipconfigs. Stub will just be same as
        ``WLAN.ipconfig()``.

        Will call the ``_dummy_ipconfig()`` to reduce code duplication since does same stuff as
        WLAN.
        """
        return _dummy_ipconfig(param, **kwargs)

    def config(self, param=None, **kwargs):
        """Sets or gets parameter of interface. Can set `mac` and can read `mac` and `ifname`.

        Stub will validate proper param and will return canned values for reading (taken from
        WLAN so may be inaccurate), will do nothing for writing.

        TODO - implement properly
        """
        # TODO - ifname might not be accurate as got from WLAN, check in future
        canned_vals = {"mac": b"\xe0\x8c\xfe\xc2f\x98", "ifname": "lo0"}

        if param is not None and kwargs:
            raise TypeError("either pos or kw args are allowed")

        if param is not None:
            if param in canned_vals:
                return canned_vals[param]
            raise ValueError("unknown config param")
        return None

    @staticmethod
    def get_lan(*args, **kwargs):
        """Class method for constructing a new _LAN object. Just calls the constructor so can
        be assigned to the ``network.LAN`` constructor function."""
        return _LAN(*args, **kwargs)


# network.LAN is a function alias to the LAN constructor
LAN = _LAN.get_lan  # pylint: disable=invalid-name
