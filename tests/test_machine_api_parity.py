"""test_machine_api_parity.py

Test file for testing that the API of our resulting ``fake_machine`` module matches what is
present on the board. Extra methods are fine but every method available in the ESP32 machine
classes should be available in our fake_machine implementation. And constants should have the
same value.

Uses the functions in ``parity_test_helpers`` to do the evaluation.

The ``extract_module_contents.py`` script will be ran on the ESP32 to extract the ``machine``
module contents as a dict tree which will be copied into this file. Test will then check that
each item in the tree is available in ``fake_machine`` and has all the contents on the ESP32.
"""

from . import parity_test_helpers

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

    def test_machine_api_parity(self):
        parity_test_helpers.check_node(
            self, ESP32_MACHINE_TREE, fake_machine, ESP32_MACHINE_TREE["name"]
        )


if __name__ == "__main__":
    unittest.main()
