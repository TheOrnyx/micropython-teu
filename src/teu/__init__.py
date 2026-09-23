"""teu - Testing Esp32 on Unix.

This is the top-level module for the TEU testing library, it includes the ``fake_machine``
package, the modified ``time`` module, as well as the basic stubbed out versions of the
``esp``, ``esp32``, and ``espnow`` libraries.
"""

# Re-export the local modules so users don't need to explicitly import.
# Also because they need to be imported for the shadowing
from . import esp_time
from . import fake_machine
from . import esp
from . import esp32
from . import espnow
from . import aioespnow
from . import network  # Needed for espnow programs

# TODO - could just shadow the builtins here when loading module instead of needing a manual call


def shadow_builtins(register_esp_modules=True):
    """Shadow/ register the specific builtin modules with TEU versions, so following code that
    imports the builtin modules will receive the custom TEU versions instead.

    :param register_esp_modules: Registers the custom ``esp``, ``esp32``, ``espnow`` module stubs
      if True, skips them if False. Helpful if testing on board and need the regular esp modules.
      Technically not a 'shadow' on the UNIX port but the wording should be fine.

    This function currently shadows/ registers the following builtin modules:

    + ``time`` -> ``teu.esp_time``
    + ``machine`` -> ``teu.fake_machine``
    + ``esp`` -> ``teu.esp`` (if `register_esp_modules`)
    + ``esp32`` -> ``teu.esp32``
    + ``espnow`` -> ``teu.espnow``
    + ``aioespnow`` -> ``teu.aioespnow``
    + ``network`` -> ``teu.network``
    """
    esp_time.shadow_builtin_time()
    fake_machine.shadow_builtin_machine()

    if register_esp_modules:
        esp.register_esp_module()
        esp32.register_esp32_module()
        espnow.register_espnow_module()
        aioespnow.register_aioespnow_module()
        network.register_network_module()
