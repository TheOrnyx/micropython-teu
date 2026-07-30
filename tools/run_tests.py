"""
Run all tests.

Script responsible for running the tests for the different modules.

Uses the `LIB_PATHS` environment variable to add custom the library paths to the module search
path."""

import os
import sys
import gc

# Test paths for the test modules to run, path relative to src/, add tests manually
TEST_PATHS = ["tests/test_uart", "tests/test_pin"]


def run_tests() -> bool:
    """Run all tests in the TEST_PATHS list and returns whether they all succeeded."""
    all_passed = True
    for path in TEST_PATHS:
        print(f"---------Testing module {path}---------\n")
        result = unittest.main(path)

        # Check if any tests failed
        if not result.wasSuccessful():
            all_passed = False

        gc.collect()  # Just in case

    return all_passed


if __name__ == "__main__":
    lib_paths = os.getenv("LIB_PATHS", "")
    if not lib_paths:
        # TODO - maybe add a default so I don't need to set LIB_PATHS before running
        print("ERROR: LIB_PATHS environment variable not set.")
        sys.exit(1)

    paths = lib_paths.split(":")  # Split from one string into the different paths
    # For the test running to work the sys path must contain the "src" directory
    if "src" not in paths:
        paths.append("src")

    # Just gonna add a small warning if a LIB_PATHS entry contains a home tilde, as MicroPython
    # doesn't resolve those, except if they're in the MICROPYPATH on startup
    for path in paths:
        if path.startswith("~/"):
            print(
                f"\nWarning: the LIB_PATHS entry '{path}' begins with a tilde.\nThis won't be "
                f"parsed properly by MicroPython when importing, recommend replacing with $HOME/\n"
            )

    sys.path[:0] = paths  # Append lib paths to front so they're searched first
    print(f"Sys path is now: {sys.path}")

    import unittest

    result = run_tests()

    if result:
        print("\nSUCCESS: All tests succeeded!")
        sys.exit(0)
    else:
        print("\nFAILURE: One or more tests failed!")
        sys.exit(1)
