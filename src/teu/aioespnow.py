"""aioespnow.py

Custom stubbed out implementation of the custom micropython-lib ``aioespnow`` module,
as it's included in the esp32 port. This module just includes a subclass of ``espnow.ESPNow``
called ``AIOESPNow`` which includes a few extra async methods: ``.arecv()``, ``.airecv()``,
``.asend()``, ``__aiter__()``, and ``__ainext()``.

I'm not familiar at all with how async works on Python (especially MicroPython),
so this implementation might not be fully correct. But it should be fine for basic stubbed
functions."""

# Unused but might as well keep for module parity
import asyncio  # pylint: disable=unused-import
import sys
from . import espnow


def register_aioespnow_module():
    """Register this module in ``sys.modules`` by adding it as the entry for ``'aioespnow'``,
    so going ``import aioespnow`` will import this module. Gets called by
    ``teu.shadow_builtins()``.
    """
    sys.modules["aioespnow"] = sys.modules[__name__]


class AIOESPNow(espnow.ESPNow):
    """Basic stubbed out dummy implementation of the ``AIOESPNow`` async ESPNow subclass.

    As previously mentioned, I'm not very familiar with python async so this might be a bit
    inaccurate but should hopefully be fine.

    I believe the recv methods do something to yield to place the rest of the call in the
    asyncio IO_QUEUE which I think gets run later after polling the object? But I don't really
    understand how it works fully, so I'll just make it return and hope it's all good. Should
    be fine for basic dummy at least, as long as API matches.
    """

    async def arecv(self):
        """Async version of ``.recv()``.

        Board does a ``yield asyncio.core._io_queue.queue_read(self)`` and then returns
        ``self.recv(0)``. Stub will skip the yield part and just return the ``self.recv()``
        which will raise the un-initialized OSError.
        """
        return self.recv(0)

    async def airecv(self):
        """Async version of ``.irecv()``. Stub just calls ``self.irecv()``."""
        return self.irecv(0)

    async def asend(self, mac, msg=None, sync=True):
        """Async version of ``.send()``.

        Stub sets parameters (if msg is None then mac is actually msg) and calls send."""
        if msg is None:
            msg, mac = mac, None
        return self.send(mac, msg, sync)

    def __aiter__(self):
        """Return self for async iterator"""
        return self

    async def __anext__(self):
        """Async iterator next method, just awaits ``.airecv()``"""
        return await self.airecv()
