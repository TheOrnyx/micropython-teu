"""espnow.py

Custom stubbed out implementation of the ESP-specific ``espnow`` module to allow loading code
that imports it on the UNIX port.

This file will contain basic stubbed out dummy versions of the ``espnow`` classes,
and the constants will be included with the same value as board. These classes will be the
``ESPNowBase`` base class and the ``ESPNow`` subclass.

This module is slightly weird on the board as the actual ``espnow`` module itself is
implemented in python and re-exports the base C module which can actually be accessed with
``import _espnow``. There's also an extra ``aioespnow`` module provided by micropython-lib
which is included in the ESP32 port and provides a subclass of ``espnow.ESPNow`` called
``AIOESPNow`` which provides extra async methods, but that will be implemented in a separate
file to be safe.

Due to this complexity I likely won't replicate these modules exactly. I'll replicate the base
modules and everything but there might be a few slight differences (such as not re-exporting a
custom ``_espnow`` module), but it should be fine as this module isn't too important and the
specific differences shouldn't be noticeable for most code.

On board the ``espnow`` class objects are represented as a singleton in the back, so multiple
calls to ``espnow.ESPNow()`` won't return the same class object in memory but calls to most
methods like ``.config()`` will use the same backing object (as instead of using self in the C
code they use a ``_get_singleton_initialized()`` call). This won't be implemented for
simplicity, but would be good to properly do for future work and keep a global storage for
stuff like the config and peers.

For future work it could be good to implement a kinda mock network device, like UART. So test
authors can replicate network communication."""

import sys


def register_espnow_module():
    """Register this module in ``sys.modules`` by adding it as the entry for ``'espnow'``,
    so going ``import espnow`` will import this module. Gets called by ``teu.shadow_builtins()``.
    """
    sys.modules["espnow"] = sys.modules[__name__]


# Module constants
MAX_DATA_LEN = 1470  # ESP32 supports esp-now v2 which has larger max data
ADDR_LEN = 6
KEY_LEN = 16
MAX_TOTAL_PEER_NUM = 20
MAX_ENCRYPT_PEER_NUM = 6

RATE_LORA_250K = 41
RATE_LORA_500K = 42
RATE_1M = 0
RATE_2M = 1
RATE_5M = 2
RATE_6M = 11
RATE_11M = 3
RATE_12M = 10
RATE_24M = 9
RATE_54M = 12


class ESPNowBase:
    """Basic stubbed out dummy implementation of the ``espnow.ESPNowBase`` base class that's
    implemented in C on the ESP32 port.

    Will implement the basic dummy methods and will then be subclassed by ``espnow.ESPNow`` to
    replicate the boards class structure.

    Most of the methods on-board perform a check which raises an `'ESP_ERR_ESPNOW_NOT_INIT'`
    OSError when the connection hasn't been initialized with a call to ``.active(True)``. Since
    this is a quick and dirty implementation I will just make most of these methods raise this
    OSError instead of returning a canned value (which would require more investigation time to
    figure out).

    Future work could improve this by adding a flag for whether ``.active(True)`` has been
    called to initialize so functions that raise un-initialized OSErrors can return canned values.
    """

    def __init__(self):
        """Create new instance, stub sets defaults for the config values in a dict."""
        # NOTE - not storing rate as is not readable and rate gets set through ESP-IDF
        self.config_vals = {"rxbuf": 2968, "timeout_ms": 300000}

        # Normally accessed through dynamic getattr, gets dict of seen peers
        self.peers_table = {}

    def active(self, flag=None) -> bool:
        """Either gets active status as bool if `flag` not present. Otherwise `flag` True
        initializes the ESP-NOW communication protocol, False deinits.

        For basic dummy this will just always return False. Might be worth making a flag though
        for methods that should fail when not active.
        """
        return False

    def config(self, get=None, *, rxbuf=None, timeout_ms=None, rate=None) -> int | None:
        """Set or get ESPNow configuration values, use keywords to set values and just plain
        string to read config value. Just setting a value returns None

        Reading and setting can be done at the same time, ``.config("timeout_ms", rxbuf=500)``
        will set rxbuf to 500 and return timeout_ms.

        `rate` can only be set, it cannot be read. Raises if trying to read an unkown config
        value, like on board.
        """
        # Setting
        if rxbuf is not None:
            self.config_vals["rxbuf"] = rxbuf
        if timeout_ms is not None:
            self.config_vals["timeout_ms"] = timeout_ms

        # Getting
        if get is not None and get in self.config_vals:
            return self.config_vals[get]
        if get is not None:
            raise ValueError("unknown config param")

        return None

    def irq(self, handler, *args) -> None:
        """Set a callback function to be called when receives message from another ESPNow
        device. Stub will just return None.

        Will also replicate the basic functionality of raising if `handler` is not callable.
        """
        if not callable(handler):
            raise ValueError("invalid handler")

    def stats(self):
        """Get the packet info stats as a 5-tuple in following format:
        ``(tx_pkts, tx_responses, tx_failures, rx_packets, rx_dropped_packets)``

        Stub will just return a tuple for no packets sent ``(0, 0, 0, 0, 0)``.
        """
        return 0, 0, 0, 0, 0

    def send(self, peer_addr=None, message=None, sync=True) -> bool:
        """Send the data in `message` to `peer_addr`. This function can be used either with
        both `peer_addr` and `message` for a specific peer or just `message` to send to all
        registered peers. Returns bool.

        Stub will just raise the OSError for `ESP_ERR_ESPNOW_NOT_INIT` not active. Maybe change
        this later so it will just return a bool if ``.active(True)`` has been called so not
        initialized.
        """
        raise OSError(-12389, "ESP_ERR_ESPNOW_NOT_INIT")

    def recvinto(self, data, timeout_ms=None) -> int:
        """Wait for incoming message, returns length of data received. `data` should be a list
        of at least 2 items ``[peer, msg]``, where `msg` should be a bytearray that can hold
        received data, `peer` should be a bytearray too but I think the memory gets replaced on
        ESP32 so doesn't matter. I think the ESP32 also supports passing a 4-item list to get
        the ``rssi`` and `timestamp` values.

        Used by the ``recv()`` and ``irecv()`` methods in ``espnow.ESPNow``.

        Stub will check that `data` has a length of at least 2 or will raise TypeError,
        then will just raise the un-initialized OSError.

        Future work would probably support specifying fake data to receive.
        """
        if len(data) < 2:
            raise TypeError("data list not long enough")  # Doesn't have msg on board but is fine
        raise OSError(-12393, "ESP_ERR_ESPNOW_NOT_INIT")

    def any(self) -> bool:
        """Check if data is available to be read and return True if so, False otherwise.

        Stub will just raise the un-initialized OSError.
        """
        raise OSError(-12389, "ESP_ERR_ESPNOW_NOT_INIT")

    # ----- Peer management methods
    #
    # Most of these are implemented as basic dummys which just do a basic buffer length check
    # and raise the un-initialized OSError.
    # This is fine for basic dummy but for future work it could be nice to properly keep track
    # of some fake peers with made up info.

    @classmethod
    def _validate_mac_len(cls, mac) -> None:
        """Validates that the provided mac is of proper size. Raises ValueError if ``len(mac)``
        is not ADDR_LEN."""
        if len(mac) != ADDR_LEN:
            raise ValueError("invalid buffer length")

    def set_pmk(self, pmk) -> None:
        """Set the Primary Master Key (PMK) which is used to encrypt the Local Master Keys for
        encrypting messages. Raises ValueError if pmk isn't of length KEY_LEN. Returns None

        Board version doesn't do the init check so will just check pmk length and return None.
        """
        if len(pmk) != KEY_LEN:
            raise ValueError("invalid buffer length")

    def add_peer(self, mac, lmk=None, channel=None, ifidx=None, encrypt=None) -> None:
        """Add/ register the provided `mac` as a peer.

        On-board technically the init check happens after the param processing so things can
        fail in other ways first. But for simplicity stub will implement the basic `mac` buffer
        length check since that happens first but otherwise will just throw the un-initialized
        OSError.
        """
        self._validate_mac_len(mac)
        raise OSError(-12389, "ESP_ERR_ESPNOW_NOT_INIT")

    def del_peer(self, mac) -> None:
        """Deregister peer associated with `mac`. Returns None.

        Stub will just do the buffer length check and then raise the un-initialized OSError.
        """
        self._validate_mac_len(mac)
        raise OSError(-12389, "ESP_ERR_ESPNOW_NOT_INIT")

    def mod_peer(self, mac, lmk=None, channel=None, ifidx=None, encrypt=None) -> None:
        """Modify the parameters for the peer associated with `mac`, much like ``.add_peer()``
        but for modifying.

        Just like ``.add_peer()``, on-board does init check after param processing so other
        things can fail first. But stub will just do the buffer length check and then raise the
        un-initialized OSError.
        """
        self._validate_mac_len(mac)
        raise OSError(-12389, "ESP_ERR_ESPNOW_NOT_INIT")

    def get_peer(self, mac):
        """Get 5-tuple of the information for the peer associated with `mac`, in form of:
        ``(mac, lmk, channel, ifidx, encrypt)``.

        Stub will just do the `mac` length check and then raise the un-initialized OSError.
        """
        self._validate_mac_len(mac)
        raise OSError(-12389, "ESP_ERR_ESPNOW_NOT_INIT")

    def get_peers(self):
        """Returns a tuple of tuples of the info for each registered peer, each tuple in form of:
        ``(mac, lmk, channel, ifidx, encrypt)``.

        Stub will just raise the un-initialized OSError since gets checked first.
        """
        raise OSError(-12389, "ESP_ERR_ESPNOW_NOT_INIT")

    def peer_count(self):
        """Get the number of registered peers as a tuple of ``(peer_num, encrypt_num)`` total
        registered peers and number of encrypted peers.

        Stub will just raise the un-initialized OSError.
        """
        raise OSError(-12389, "ESP_ERR_ESPNOW_NOT_INIT")


class ESPNow(ESPNowBase):
    """Basic stubbed out dummy implementation of main espnow class ``espnow.ESPNow()`` which is
    implemented in the ``espnow.py`` in the `ports/esp32/modules/` folder.

    Subclasses the ``ESPNowBase`` and adds the following extra basic stubbed methods:

    + ``.irecv([timeout_ms])`` - Reads data into internal buffer and then returns that data if read.
    + ``.recv([timeout_ms])`` - Reads data into internal buffer, then returns the data if read.
      Quite similar to ``irecv`` except this one allocates new ``bytes`` objects for each return.
    + ``__iter__``, and ``__next__`` - Iterator methods, just calls ``irecv``.
    + ``irq()`` - Just calls super version of ``irq`` but with self passed as extra arg.

    The recv methods will be implemented as basic stubs which will call the super recvinto
    which will just cause the OSError, for future work it could be good to implement these as
    proper fakes though.
    """

    # I prefer to be declarative :p
    # pylint: disable-next=useless-parent-delegation
    def __init__(self):
        super().__init__()

    def recv(self, timeout_ms=None):
        """Wait for incoming message and then return 2-item list ``[mac_addr, msg]`` containing
        sender address and received message. Returns a ``(None, None)`` tuple if timeout.

        On-board this allocates new bytes objects for each return, the ``.irecv()`` reuses an
        internal `_data` object instead, but doesn't matter for stub.

        Stub will just call the supers recvinto which will raise the un-initialized OSError.
        """
        self.recvinto([None, None], timeout_ms)
        return None, None  # For type hints

    def irecv(self, timeout_ms=None):
        """Same as ``.recv()`` but reuses internal bytearrays on-board to reduce allocations.
        This is used for the iterator next method.

        Stub will just call the supers recvinto which will raise the un-initialized OSError,
        same as recv.
        """
        self.recvinto([None, None], timeout_ms)
        return None, None  # For type hinting

    def irq(self, handler, *args) -> None:
        """Just calls the super irq with ``self`` as the extra param. Doesn't matter for stub
        as extra param isn't used but good to implement for future.
        """
        super().irq(handler, self)

    def __iter__(self):
        """Get iterator for this class, just returns self like on-board. ``__next__`` will call
        ``irecv``"""
        return self

    def __next__(self):
        """Next item in iterator, calls ``irecv`` but stub will just raise the un-initialized
        OSError."""
        return self.irecv()
