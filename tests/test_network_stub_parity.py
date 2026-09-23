"""test_network_stub_parity.py

Just a basic parity test to check that our custom ``teu.network`` module matches what's
available on board."""

import unittest

from . import parity_test_helpers

import teu

teu.shadow_builtins()

import network

NETWORK_TREE = {
    "classes": {
        "WLAN": {
            "classes": {},
            "constants": {
                "SEC_WPA2_ENT": 5,
                "BANDWIDTH_80_80": 5,
                "SEC_WPA3_EXT_PSK": 11,
                "SEC_WPA2_WPA3": 7,
                "SEC_WEP": 1,
                "SEC_OWE": 9,
                "SEC_WPA3_ENT_192": 10,
                "SEC_WPA": 2,
                "SEC_WPA3_ENT": 14,
                "SEC_WPA3_EXT_PSK_MIXED_MODE": 12,
                "PM_NONE": 0,
                "SEC_WPA_WPA2": 4,
                "SEC_WPA3": 6,
                "SEC_WPA2": 3,
                "BANDWIDTH_80": 3,
                "BANDWIDTH_160": 4,
                "SEC_DPP": 13,
                "SEC_OPEN": 0,
                "PROTOCOL_DEFAULT": 7,
                "BANDWIDTH_20": 1,
                "IF_STA": 0,
                "PROTOCOL_LR": 8,
                "SEC_WPA2_WPA3_ENT": 15,
                "PM_POWERSAVE": 2,
                "IF_AP": 1,
                "PM_PERFORMANCE": 1,
                "SEC_WPA_ENT": 16,
                "BANDWIDTH_40": 2,
                "SEC_WAPI": 8,
            },
            "methods": [
                "ipconfig",
                "scan",
                "config",
                "isconnected",
                "csi_read",
                "csi_available",
                "status",
                "csi_disable",
                "csi_dropped",
                "active",
                "csi_enable",
                "connect",
                "disconnect",
                "ifconfig",
            ],
            "modules": [],
            "name": "WLAN",
        },
        "PPP": {
            "classes": {},
            "constants": {
                "AUTH_NONE": 0,
                "SEC_PAP": 1,
                "AUTH_PAP": 1,
                "SEC_CHAP": 2,
                "AUTH_CHAP": 2,
                "SEC_NONE": 0,
            },
            "methods": [
                "ifconfig",
                "config",
                "ipconfig",
                "status",
                "connect",
                "disconnect",
                "isconnected",
                "poll",
                "active",
            ],
            "modules": [],
            "name": "PPP",
        },
    },
    "constants": {
        "PHY_DP83848": 4,
        "STAT_GOT_IP": 1010,
        "AUTH_WAPI_PSK": 8,
        "PHY_LAN8710": 0,
        "STAT_ASSOC_FAIL": 203,
        "AUTH_WPA2_WPA3_PSK": 7,
        "ETH_GOT_IP": 5,
        "AUTH_WPA3_EXT_PSK": 11,
        "PHY_W5500": 102,
        "AUTH_WPA3_ENT_192": 10,
        "AUTH_WPA2_PSK": 3,
        "AUTH_OWE": 9,
        "MODE_11N": 4,
        "MODE_11B": 1,
        "PHY_GENERIC": 8,
        "STA_IF": 0,
        "MODE_11G": 2,
        "AUTH_WPA2_ENTERPRISE": 5,
        "ETH_DISCONNECTED": 4,
        "PHY_RTL8201": 3,
        "STAT_NO_AP_FOUND_IN_AUTHMODE_THRESHOLD": 211,
        "ETH_INITIALIZED": 0,
        "MODE_LR": 8,
        "STAT_NO_AP_FOUND_W_COMPATIBLE_SECURITY": 210,
        "AUTH_WEP": 1,
        "STAT_NO_AP_FOUND_IN_RSSI_THRESHOLD": 212,
        "AUTH_MAX": 17,
        "STAT_NO_AP_FOUND": 201,
        "STAT_CONNECTING": 1001,
        "STAT_HANDSHAKE_TIMEOUT": 204,
        "ETH_CONNECTED": 3,
        "PHY_LAN8720": 1,
        "ETH_STOPPED": 2,
        "PHY_KSZ8041": 5,
        "STAT_IDLE": 1000,
        "AUTH_WPA3_EXT_PSK_MIXED_MODE": 12,
        "ETH_STARTED": 1,
        "PHY_LAN8670": 7,
        "PHY_KSZ8851SNL": 100,
        "STAT_BEACON_TIMEOUT": 200,
        "PHY_IP101": 2,
        "AUTH_WPA3_PSK": 6,
        "PHY_DM9051": 101,
        "AUTH_OPEN": 0,
        "STAT_WRONG_PASSWORD": 202,
        "STAT_CONNECT_FAIL": 203,
        "AP_IF": 1,
        "AUTH_WPA_PSK": 2,
        "AUTH_WPA_WPA2_PSK": 4,
        "PHY_KSZ8081": 6,
    },
    "methods": ["hostname", "ipconfig", "country", "phy_mode", "LAN"],
    "modules": [],
    "name": "network",
}


class TestNetworkStubParity(unittest.TestCase):
    """Network stub parity test"""

    def test_network_stub_parity(self):
        parity_test_helpers.check_node(self, NETWORK_TREE, network, "network")


if __name__ == "__main__":
    unittest.main()
