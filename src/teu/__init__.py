"""teu - Testing Esp32 on Unix.

This is the top-level module for the TEU testing library, it includes the ``fake_machine``
package, the modified ``time`` module, as well as the basic stubbed out versions of the
``esp``, ``esp32``, and ``espnow`` libraries.
"""

# re-export esp_time so can be accessed through here without explicit import
from . import esp_time
from . import fake_machine

# TODO - could just shadow the builtins here when loading module instead of needing a manual call


def shadow_builtins():
    """Shadow the specific builtin modules with TEU versions, so following code that imports the
    builtin modules will receive the custom TEU versions instead.

    This function currently shadows the following builtin modules:

    + ``time`` -> ``teu.esp_time``
    + ``machine`` -> ``teu.fake_machine``
    + ``esp`` -> ``teu.esp`` (TODO)
    + ``esp32`` -> ``teu.esp32`` (TODO)
    + ``espnow`` -> ``teu.espnow`` (TODO)
    """
    esp_time.shadow_builtin_time()
    fake_machine.shadow_builtin_machine()
