"""
Setup Test Environment Utility.

Basic script that handles downloading the required testing dependencies from micropython-lib
using `mip` into the proper library location.

Uses the `MIP_LIBRARY_PATH` environment variable to choose where to download the files.
"""

import mip
import os
import sys

# The required modules for testing, fetched by mip
REQUIRED_MODULES = [
    "unittest",
]


if __name__ == "__main__":
    lib_path = os.getenv("MIP_LIBRARY_PATH")
    if not lib_path:
        print("WARNING: MIP_LIBRARY_PATH env variable not set")
        sys.exit(1)

    for module in REQUIRED_MODULES:
        mip.install(module, target=lib_path)

    print("Test environment setup complete")
