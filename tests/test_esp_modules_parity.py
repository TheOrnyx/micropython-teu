"""test_esp_modules_parity.py

Tests that just ensure that our custom implementations of the esp-specific ``esp``, ``esp32``,
``espnow``, and ``aioespnow`` modules match what's available on the ESP32. All functions should
exist, classes should exist and have matching contents, and constants with matching values.
Basically the same as the ``test_machine_api_parity.py`` test.

Uses the ``parity_test_helpers`` functions for the testing.

The esp module trees are extracted with the same ``tools/extract_module_contents.py`` script
being run for each module on my ESP32.
"""

import unittest
from . import parity_test_helpers

import teu

teu.shadow_builtins()  # Might as well test they can be shadowed/ registered too

import esp, esp32, espnow, aioespnow

# Module tree dict for the 'esp' module
ESP_TREE = {
    "classes": {},
    "constants": {
        "LOG_VERBOSE": 5,
        "LOG_WARNING": 2,
        "LOG_ERROR": 1,
        "LOG_DEBUG": 4,
        "LOG_INFO": 3,
        "LOG_NONE": 0,
    },
    "methods": [
        "gpio_matrix_in",
        "flash_read",
        "gpio_matrix_out",
        "flash_user_start",
        "osdebug",
        "flash_erase",
        "flash_size",
        "flash_write",
    ],
    "modules": [],
    "name": "esp",
}

# Module tree dict for the `esp32` module
ESP32_TREE = {
    "classes": {
        "PCNT": {
            "classes": {},
            "constants": {
                "IRQ_THRESHOLD1": 4,
                "IGNORE": 0,
                "IRQ_ZERO": 64,
                "DECREMENT": 2,
                "IRQ_MAX": 32,
                "REVERSE": 1,
                "HOLD": 2,
                "IRQ_MIN": 16,
                "INCREMENT": 1,
                "NORMAL": 0,
                "IRQ_THRESHOLD0": 8,
            },
            "methods": ["deinit", "init", "irq", "stop", "value", "start"],
            "modules": [],
            "name": "PCNT",
        },
        "NVS": {
            "classes": {},
            "constants": {},
            "methods": ["commit", "set_i32", "get_i32", "erase_key", "set_blob", "get_blob"],
            "modules": [],
            "name": "NVS",
        },
        "RMT": {
            "classes": {},
            "constants": {"PULSE_MAX": 32767},
            "methods": [
                "bitstream_rmt",
                "clock_div",
                "bitstream_channel",
                "deinit",
                "active",
                "write_pulses",
                "source_freq",
                "loop",
                "wait_done",
                "loop_count",
            ],
            "modules": [],
            "name": "RMT",
        },
        "ULP": {
            "classes": {},
            "constants": {"RESERVE_MEM": 2040},
            "methods": ["run", "set_wakeup_period", "load_binary"],
            "modules": [],
            "name": "ULP",
        },
        "Partition": {
            "classes": {},
            "constants": {"RUNNING": 1, "TYPE_APP": 0, "TYPE_DATA": 1, "BOOT": 0},
            "methods": [
                "writeblocks",
                "get_next_update",
                "find",
                "readblocks",
                "ioctl",
                "info",
                "set_boot",
                "mark_app_valid_cancel_rollback",
            ],
            "modules": [],
            "name": "Partition",
        },
    },
    "constants": {
        "WAKEUP_ANY_HIGH": True,
        "HEAP_EXEC": 1,
        "HEAP_DATA": 4,
        "WAKEUP_ALL_LOW": False,
    },
    "methods": [
        "raw_temperature",
        "wake_on_ext0",
        "wake_on_ext1",
        "wake_on_gpio",
        "wake_on_ulp",
        "idf_heap_info",
        "wake_on_touch",
    ],
    "modules": [],
    "name": "esp32",
}

# Module tree dict for the `espnow` module
ESPNOW_TREE = {
    "classes": {
        "ESPNowBase": {
            "classes": {},
            "constants": {},
            "methods": [
                "active",
                "del_peer",
                "config",
                "mod_peer",
                "get_peer",
                "any",
                "peer_count",
                "irq",
                "add_peer",
                "recvinto",
                "set_pmk",
                "send",
                "stats",
                "get_peers",
            ],
            "modules": [],
            "name": "ESPNowBase",
        },
        "ESPNow": {
            "classes": {},
            "constants": {},
            "methods": [
                "active",
                "del_peer",
                "config",
                "mod_peer",
                "get_peer",
                "recv",
                "peer_count",
                "irq",
                "any",
                "irecv",
                "add_peer",
                "recvinto",
                "set_pmk",
                "send",
                "stats",
                "get_peers",
            ],
            "modules": [],
            "name": "ESPNow",
        },
    },
    "constants": {
        "RATE_5M": 2,
        "RATE_11M": 3,
        "MAX_DATA_LEN": 1470,
        "MAX_ENCRYPT_PEER_NUM": 6,
        "RATE_12M": 10,
        "ADDR_LEN": 6,
        "KEY_LEN": 16,
        "RATE_LORA_500K": 42,
        "RATE_54M": 12,
        "RATE_6M": 11,
        "RATE_24M": 9,
        "RATE_2M": 1,
        "RATE_1M": 0,
        "MAX_TOTAL_PEER_NUM": 20,
        "RATE_LORA_250K": 41,
    },
    "methods": [],
    "modules": [],
    "name": "espnow",
}

# Module tree dict for the `aioespnow` module
AIOESPNOW_TREE = {
    "classes": {
        "AIOESPNow": {
            "classes": {},
            "constants": {},
            "methods": [
                "active",
                "del_peer",
                "recvinto",
                "airecv",
                "set_pmk",
                "get_peer",
                "irecv",
                "irq",
                "any",
                "recv",
                "config",
                "mod_peer",
                "send",
                "get_peers",
                "peer_count",
                "arecv",
                "stats",
                "add_peer",
                "asend",
            ],
            "modules": [],
            "name": "AIOESPNow",
        }
    },
    "constants": {},
    "methods": [],
    "modules": ["asyncio", "espnow"],
    "name": "aioespnow",
}


class TestEspModulesApiParity(unittest.TestCase):
    """Test that all items in the extracted esp/esp32/espnow/aioespnow trees are available in
    the corresponding fake stub modules, to evaluate parity."""

    def test_esp_api_parity(self):
        parity_test_helpers.check_node(self, ESP_TREE, esp, ESP_TREE["name"])

    def test_esp32_api_parity(self):
        parity_test_helpers.check_node(self, ESP32_TREE, esp32, ESP32_TREE["name"])

    def test_espnow_api_parity(self):
        parity_test_helpers.check_node(self, ESPNOW_TREE, espnow, ESPNOW_TREE["name"])

    def test_aioespnow_api_parity(self):
        parity_test_helpers.check_node(self, AIOESPNOW_TREE, aioespnow, AIOESPNOW_TREE["name"])


if __name__ == "__main__":
    unittest.main()
