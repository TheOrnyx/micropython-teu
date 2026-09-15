"""
Run all tests.

Script responsible for running the unit tests for the implemented modules. Searches the tests/
folder for test files and runs each found test.

This script should be ran from the project root like this:
``micropython tools/run_tests.py``

The ``src/`` folder and the repo root paths are calculated relative to cwd which should be the
project root and added to the sys.path module search path automatically so tests can properly
import our modules. Extra library paths can be added by setting LIB_PATHS but this shouldn't be
necessary if they're already in a default search location like ~/.micropython/lib.

Python testing is strange..."""

import os
import sys
import gc

# Calculate the repo root and paths for src/ and tests/
# Not the nicest since micropython doesn't have os.path and __file__ doesn't give absolute path
REPO_ROOT_PATH = os.getcwd()
SRC_PATH = REPO_ROOT_PATH + "/src"
TESTS_DIR = REPO_ROOT_PATH + "/tests"


def discover_test_modules(tests_path):
    """Finds and returns a list of test modules found in the provided test folder.

    The returned list of test modules will be in a module format, so 'tests/test_pin.py' will
    be added as 'tests.test_pin', so can be resolved as a module for unittest."""
    modules = []
    for filename in sorted(os.listdir(tests_path)):
        if filename.startswith("test_") and filename.endswith(".py"):  # Ignore __init__.py
            name = filename[:-3]
            modules.append(f"tests.{name}")

    return modules


def import_dotted_test(dotted_module: str):
    """Import and return a dotted tests paths proper test module.

    For some reason when you try to do dotted test paths with the micropython unittest it does
    an ``__import__()`` but the returned imported module is just the `tests` part, with the
    requested test submodule as an attribute. So ``__import__("tests.test_uart")`` gives the
    tests module with ``test_uart`` as the attribute holding the submodule we want to test.

    So just import the module, get the proper child and return it
    """
    module = __import__(dotted_module)
    for part in dotted_module.split(".")[1:]:  # Just incase we ever have multiple test levels
        module = getattr(module, part)
    return module


def run_tests(test_paths) -> bool:
    """Run all tests in the provided test_paths list and returns whether they all succeeded."""
    all_passed = True
    total_results = unittest.TestResult()
    for path in test_paths:
        print(f"---------Testing module {path}---------")
        # Get the proper submodule to test (unittest will import and try to use top-level)
        imported_module = import_dotted_test(path)
        result = unittest.main(imported_module)
        total_results = total_results + result
        print(
            f"<{path} run={result.testsRun} errors={result.errorsNum} failures="
            f"{result.failuresNum} skipped={result.skippedNum}>\n"
        )

        # Check if any tests failed
        if not result.wasSuccessful():
            all_passed = False
        gc.collect()  # Just in case

    print("\n----------------------------\nTotal:")
    print(f"Ran {total_results.testsRun} tests")
    print(
        f"<run={total_results.testsRun} errors={total_results.errorsNum} failures="
        f"{total_results.failuresNum} skipped={total_results.skippedNum}>"
    )
    return all_passed


if __name__ == "__main__":
    # Debug stuff
    print(
        "Initial debug info:\n"
        f"\t__file__: {__file__}\n\tcwd: {os.getcwd()}\n\tInitial sys.path: {sys.path}\n"
    )

    if "src" not in os.listdir():  # Make sure in project root
        print(f"Please run this script from the project root, currently at {os.getcwd()}")
        sys.exit(1)

    lib_paths = os.getenv("LIB_PATHS", "")  # Get any extra libs
    paths = lib_paths.split(":") if lib_paths else []  # Split into the different paths

    # Add the src and repo root paths
    for path in (REPO_ROOT_PATH, SRC_PATH):
        if path not in paths:
            paths.append(path)

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

    try:
        import unittest
    except ImportError as e:
        print(
            f"Failed to import unittest {e}.\n"
            "Make sure it is in a default MicroPython search path or included in LIB_PATHS."
        )
        sys.exit(1)

    # Get and run tests
    test_paths = discover_test_modules(TESTS_DIR)
    if not test_paths:
        print(f"Error: no tests found in test folder {TESTS_DIR}")
        sys.exit(1)
    print(f"Discovered tests: {test_paths}\n")

    passed = run_tests(test_paths)

    if passed:
        print("\nSUCCESS: All tests succeeded!")
        sys.exit(0)
    else:
        print("\nFAILURE: One or more tests failed!")
        sys.exit(1)
