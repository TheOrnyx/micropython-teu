"""test_machine_api_parity.py

Test file for testing that the API of our resulting ``fake_machine`` module matches what is
present on the board. Extra methods are fine but every method available in the ESP32 machine
classes should be available in our fake_machine implementation. And constants should have the
same value.

Most of the assertions take place in subTests so if one fails we can still explore the other
module nodes so the final result will show all violations.

The ``extract_module_contents.py`` script will be ran on the ESP32 to extract the ``machine``
module contents as a dict tree which will be copied into this file. Test will then check that
each item in the tree is available in ``fake_machine`` and has all the contents on the ESP32.
"""

# Pyright hates the unittest.subtest
# pyright: reportCallIssue=false

import unittest
from teu import fake_machine

# Extracted from my ESP32
ESP32_MACHINE_TREE = {
    "classes": {
        "SDCard": {
            "classes": {},
            "constants": {},
            "methods": ["writeblocks", "readblocks", "ioctl", "deinit", "info"],
            "modules": [],
            "name": "SDCard",
        },
        "Timer": {
            "classes": {},
            "constants": {"PERIODIC": 1, "ONE_SHOT": 0},
            "methods": ["init", "deinit", "value"],
            "modules": [],
            "name": "Timer",
        },
        "ADC": {
            "classes": {},
            "constants": {
                "WIDTH_12BIT": 12,
                "ATTN_11DB": 3,
                "WIDTH_10BIT": 10,
                "ATTN_2_5DB": 1,
                "WIDTH_11BIT": 11,
                "ATTN_6DB": 2,
                "ATTN_0DB": 0,
                "WIDTH_9BIT": 9,
            },
            "methods": [
                "atten",
                "block",
                "read_u16",
                "read_uv",
                "read",
                "init",
                "width",
                "deinit",
            ],
            "modules": [],
            "name": "ADC",
        },
        "I2C": {
            "classes": {},
            "constants": {},
            "methods": [
                "writevto",
                "writeto_mem",
                "readfrom",
                "readfrom_into",
                "stop",
                "init",
                "writeto",
                "deinit",
                "readfrom_mem_into",
                "readfrom_mem",
                "readinto",
                "write",
                "start",
                "scan",
            ],
            "modules": [],
            "name": "I2C",
        },
        "UART": {
            "classes": {},
            "constants": {
                "RTS": 1,
                "CTS": 2,
                "INV_TX": 32,
                "INV_CTS": 8,
                "IRQ_RXIDLE": 4096,
                "IRQ_BREAK": 2,
                "INV_RTS": 64,
                "IRQ_RX": 1,
                "INV_RX": 4,
            },
            "methods": [
                "txdone",
                "readline",
                "readinto",
                "flush",
                "read",
                "any",
                "write",
                "deinit",
                "irq",
                "init",
                "sendbreak",
            ],
            "modules": [],
            "name": "UART",
        },
        "TouchPad": {
            "classes": {},
            "constants": {},
            "methods": ["config", "read"],
            "modules": [],
            "name": "TouchPad",
        },
        "PWM": {
            "classes": {},
            "constants": {},
            "methods": ["freq", "init", "deinit", "duty", "duty_u16", "duty_ns"],
            "modules": [],
            "name": "PWM",
        },
        "Encoder": {
            "classes": {},
            "constants": {},
            "methods": ["init", "phases", "value", "deinit"],
            "modules": [],
            "name": "Encoder",
        },
        "DAC": {
            "classes": {},
            "constants": {},
            "methods": ["write"],
            "modules": [],
            "name": "DAC",
        },
        "Pin": {
            "classes": {
                "board": {
                    "classes": {},
                    "constants": {},
                    "methods": [],
                    "modules": [],
                    "name": "board",
                }
            },
            "constants": {
                "IRQ_RISING": 1,
                "OUT": 3,
                "DRIVE_3": 3,
                "DRIVE_0": 0,
                "WAKE_HIGH": 5,
                "DRIVE_2": 2,
                "DRIVE_1": 1,
                "PULL_UP": 2,
                "IRQ_FALLING": 2,
                "WAKE_LOW": 4,
                "OPEN_DRAIN": 7,
                "IN": 1,
                "PULL_DOWN": 1,
            },
            "methods": ["off", "on", "value", "irq", "toggle", "init"],
            "modules": [],
            "name": "Pin",
        },
        "SoftI2C": {
            "classes": {},
            "constants": {},
            "methods": [
                "writevto",
                "writeto_mem",
                "readfrom",
                "readfrom_into",
                "stop",
                "init",
                "writeto",
                "deinit",
                "readfrom_mem_into",
                "readfrom_mem",
                "readinto",
                "write",
                "start",
                "scan",
            ],
            "modules": [],
            "name": "SoftI2C",
        },
        "RTC": {
            "classes": {},
            "constants": {},
            "methods": ["datetime", "memory", "init"],
            "modules": [],
            "name": "RTC",
        },
        "Counter": {
            "classes": {},
            "constants": {"UP": 1, "RISING": 1, "FALLING": 2, "DOWN": 2},
            "methods": ["value", "deinit", "init"],
            "modules": [],
            "name": "Counter",
        },
        "SPI": {
            "classes": {},
            "constants": {"LSB": 1, "MSB": 0},
            "methods": ["write", "readinto", "init", "write_readinto", "deinit", "read"],
            "modules": [],
            "name": "SPI",
        },
        "WDT": {
            "classes": {},
            "constants": {},
            "methods": ["feed"],
            "modules": [],
            "name": "WDT",
        },
        "I2S": {
            "classes": {},
            "constants": {"RX": 1, "TX": 2, "MONO": 0, "STEREO": 1},
            "methods": ["write", "readinto", "init", "deinit", "irq", "shift"],
            "modules": [],
            "name": "I2S",
        },
        "Signal": {
            "classes": {},
            "constants": {},
            "methods": ["on", "value", "off"],
            "modules": [],
            "name": "Signal",
        },
        "ADCBlock": {
            "classes": {},
            "constants": {},
            "methods": ["init", "connect"],
            "modules": [],
            "name": "ADCBlock",
        },
        "SoftSPI": {
            "classes": {},
            "constants": {"LSB": 1, "MSB": 0},
            "methods": ["write", "readinto", "init", "write_readinto", "deinit", "read"],
            "modules": [],
            "name": "SoftSPI",
        },
    },
    "constants": {
        "DEEPSLEEP_RESET": 4,
        "SLEEP": 2,
        "HARD_RESET": 2,
        "mem8": "<8-bit memory>",
        "PWRON_RESET": 1,
        "mem16": "<16-bit memory>",
        "WDT_RESET": 3,
        "PIN_WAKE": 2,
        "ULP_WAKE": 6,
        "EXT1_WAKE": 3,
        "EXT0_WAKE": 2,
        "SOFT_RESET": 5,
        "mem32": "<32-bit memory>",
        "TOUCHPAD_WAKE": 5,
        "DEEPSLEEP": 4,
        "TIMER_WAKE": 4,
    },
    "methods": [
        "reset",
        "enable_irq",
        "soft_reset",
        "sleep",
        "dht_readinto",
        "mem_backup",
        "wake_pins",
        "idle",
        "reset_cause",
        "freq",
        "time_pulse_us",
        "unique_id",
        "const",
        "disable_irq",
        "lightsleep",
        "wake_reason",
        "deepsleep",
        "bitstream",
    ],
    "modules": [],
    "name": "machine",
}


class TestMachineApiParity(unittest.TestCase):
    """Test that all items in the `ESP32_MACHINE_TREE` are available in ``fake_machine``,
    to evaluate parity"""

    @staticmethod
    def _is_unrepresentable(value):
        """Returns true for values the extraction script could only capture as a repr string
        (e.g. machine.mem8 -> "<8-bit memory>") because they aren't a plain literal.
        There's nothing meaningful to compare those against by value, so should only check that
        the attribute exists."""
        return isinstance(value, str) and value.startswith("<") and value.endswith(">")

    def _check_methods(self, ref_node, live_obj, path):
        """Check that all methods/ functions in the reference tree node exist in the faked
        version of the node and are callable"""
        for method_name in ref_node["methods"]:
            with self.subTest(path=path, kind="method", name=method_name):
                self.assertTrue(
                    hasattr(live_obj, method_name),
                    f"{path} is missing method '{method_name}'",
                )
                if hasattr(live_obj, method_name):
                    self.assertTrue(
                        callable(getattr(live_obj, method_name)),
                        f"{path}.{method_name} exists but is not callable",
                    )

    def _check_constants(self, ref_node, live_obj, path):
        """Check that all constants in the reference tree node exist in the faked version of
        the node."""
        for const_name, expected in ref_node["constants"].items():
            if const_name.startswith("__"):
                # Internal marker from the extraction script for things like max_depth being
                # reached (e.g "__truncated__"), nothing to check so skip.
                continue
            with self.subTest(path=path, kind="constant", name=const_name):
                self.assertTrue(
                    hasattr(live_obj, const_name),
                    f"{path} is missing constant '{const_name}'",
                )
                if not hasattr(live_obj, const_name):
                    continue
                if self._is_unrepresentable(expected):
                    continue
                actual = getattr(live_obj, const_name)
                self.assertEqual(
                    actual,
                    expected,
                    f"{path}.{const_name} = {repr(actual)}, expected {repr(expected)}",
                )

    def _check_modules(self, ref_node, live_obj, path):
        """Check that modules in ref node exist in faked class.

        NOTE - in both here and the extraction script modules aren't explored recursively as
        not needed as there are only top-level modules on the board (aka ``machine`` only has
        classes, functions and constants, no nested modules).
        """
        for module_name in ref_node.get("modules", []):
            with self.subTest(path=path, kind="module", name=module_name):
                self.assertTrue(
                    hasattr(live_obj, module_name),
                    f"{path} is missing module '{module_name}'",
                )

    def _check_classes(self, ref_node, live_obj, path):
        """Check that all classes in the reference tree node exist in faked implementation.

        Recursively checks other child classes.
        """
        for class_name, sub_node in ref_node["classes"].items():
            child_path = f"{path}.{class_name}"
            with self.subTest(path=path, kind="class", name=class_name):
                self.assertTrue(
                    hasattr(live_obj, class_name),
                    "{} is missing class '{}'".format(path, class_name),
                )
            # Will still fail in subtest but continue so other classes can be explored
            if not hasattr(live_obj, class_name):
                continue

            live_class = getattr(live_obj, class_name)
            with self.subTest(path=child_path, kind="class-type"):
                self.assertTrue(
                    isinstance(live_class, type),
                    f"{child_path} exists but is not a class (got {repr(type(live_class))})",
                )
            if not isinstance(live_class, type):
                continue
            if sub_node.get("ref_only"):
                # Class is already extracted somewhere else in tree so ignore.
                continue

            self._check_node(sub_node, live_class, child_path)

    def _check_node(self, ref_node, real_class, path):
        """Recursively check the items in a specific tree ref node and check they exist in the
        real fake_machine implementation. Path used for subtest printing"""
        self._check_methods(ref_node, real_class, path)
        self._check_constants(ref_node, real_class, path)
        self._check_modules(ref_node, real_class, path)
        self._check_classes(ref_node, real_class, path)

    def test_machine_api_parity(self):
        self._check_node(ESP32_MACHINE_TREE, fake_machine, ESP32_MACHINE_TREE["name"])


if __name__ == "__main__":
    unittest.main()
