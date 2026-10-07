"""run_driver_tests.py -

MicroPython tool script to run the example driver tests in ``driver_examples/``.

Quite similar to ``run_tests.py`` except this will only run specific tests, and CLI args can be
provided to run specific tests (can do partial, so 'modem' as cli arg would run test_modem_unix).

Run this script from the repo root directory with
``micropython tools/run_driver_tests.py [tests to run]``

Requires the ``unittest`` and ``logging`` micropython-lib modules to be installed.
"""

import os
import sys
import gc

import unittest  # Should be in path when ran

REPO_ROOT_PATH = os.getcwd()
SRC_PATH = REPO_ROOT_PATH + "/src"

# Driver tests as hardcoded dotted module paths from root, easier than autodetecting since only
# a few tests are implemented
DEFAULT_DRIVER_TESTS = [
    "driver_examples.pythings_sim800l.test_sim800l",
    "driver_examples.mpu9250_i2c.test_i2c_mpu9250",
    "driver_examples.tinypico_lis3dh.test_i2c_lis3dh",
]


def import_dotted_test(dotted_module: str):
    """Import and return a dotted tests paths proper test module.

    MicroPython unittest implementation isn't the best and fails when trying to test nested
    modules due to ``__import__(module_path)`` importing the parent and not the test submodule.
    So we need to import the module first before passing to unittest.

    So in order to properly import the test module this function will strip the test script
    name (so `test_bar` from 'foo.bar.test_bar`) and then use ``__import__()`` to import it
    with the fromlist argument receiving the submodule, which imports it instead of the top.
    """
    # Strip submodule name
    submodule_name = dotted_module.split(".")[-1]
    module = __import__(dotted_module, None, None, [submodule_name], 0)
    print(f"Imported [{module.__file__}]")
    return module


def run_tests(test_paths):
    """Run all tests in the provided test_paths list and returns whether they all succeeded."""
    all_passed = True
    total_results = unittest.TestResult()
    for path in test_paths:
        print(f"---------Testing module {path}---------")
        # Import the proper test submodule to pass into unittest
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
    return all_passed, total_results


if __name__ == "__main__":
    # If CLI args provided then run the specified tests with partial completion
    print(sys.argv)

    tests_to_run = set()
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            [tests_to_run.add(x) for x in DEFAULT_DRIVER_TESTS if arg in x]
    else:
        tests_to_run.update(DEFAULT_DRIVER_TESTS)

    if "src" not in os.listdir():  # Make sure in project root
        print(f"Please run this script from the project root, currently at {os.getcwd()}")
        sys.exit(1)

    # Add repo root and src directory to path, so modules are found correctly
    paths = []
    for path in (REPO_ROOT_PATH, SRC_PATH):
        if path not in paths:
            paths.append(path)
    sys.path[:0] = paths  # Append lib paths to front so they're searched first
    print(f"Sys path is now: {sys.path}\n")

    print(f"Running driver tests: {tests_to_run}\n")
    passed, total_results = run_tests(tests_to_run)

    print("----------------------------\nTotal:")
    print(f"Ran {total_results.testsRun} tests")
    print(
        f"<run={total_results.testsRun} errors={total_results.errorsNum} failures="
        f"{total_results.failuresNum} skipped={total_results.skippedNum}>"
    )

    if passed:
        print("\nSUCCESS: All tests succeeded!")
        sys.exit(0)
    else:
        print("\nFAILURE: One or more tests failed!")
        sys.exit(1)
