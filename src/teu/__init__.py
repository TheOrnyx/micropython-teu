"""teu - Testing Esp32 on Unix.

This is the top-level module for the TEU testing library, it includes the ``fake_machine``
package, the modified ``time`` module, as well as the basic stubbed out versions of the
``esp``, ``esp32``, and ``espnow`` libraries.

TODO - finish implementing this and move the fake_machine to this module, either with an alias
  or move the whole thing. Alias would be good for flexibility but might not work well with the
  import system...
"""

# re-export esp_time so can be accessed through here without explicit import
from . import esp_time

# TODO - could just shadow the builtins here when loading module instead of needing a manual call


def shadow_builtins():
    """Shadow the specific builtin modules with TEU versions, so following code that imports the
    builtin modules will receive the custom TEU versions instead.

    This function currently shadows the following builtin modules:

    + ``time`` -> ``teu.esp_time``
    + ``machine`` -> ``teu.fake_machine`` (TODO)
    + ``esp`` -> ``teu.esp`` (TODO)
    + ``esp32`` -> ``teu.esp32`` (TODO)
    + ``espnow`` -> ``teu.espnow`` (TODO)
    """
    esp_time.shadow_builtin_time()
