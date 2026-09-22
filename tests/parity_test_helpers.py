"""parity_test_helpers.py

Extra util test file for providing methods to test the parity of a module and ensure it matches
the basic API of the board.

The ``check_node()`` function is the main entry point and takes in an extracted dictionary tree
representation of the module (the reference), and the imported version of the module to check
the parity with. It will recursively check each function, constant, and class in the reference
tree and make sure they're available in the live version of the module and the constants are
the same value. At each class it will explore all the contents of that class (functions,
constants, inner classes) and make sure they also match.

Most of the checks occur in a ``subTest`` so if a check fails it will get printed and count as
a failure but the rest of the checks will continue, so all missing/ invalid items will be found
instead of the first being found and then exiting.

Also, modules don't get recursively checked like classes as I couldn't find any modules which
had nested modules defined in them. But quite a few other modules will import sys or something,
in which case we don't want to inspect.

The extracted reference tree is extracted from the ESP32 using the
``extract_module_contents.py`` script, these extracted trees can be seen in
`test_machine_api_parity.py` and `test_esp_modules_parity.py`.

Sadly due to the way MicroPython implements their built-in functions we can't also examine the
signature to make sure it matches, but ideally they should all match. Future work would
probably implement proper tests for the extra stubs to ensure they support the different ways
they can be called, as I don't have time unfortunately"""

# Pyright hates the unittest.subtest
# pyright: reportCallIssue=false

import unittest


def is_unrepresentable(value):
    """Returns true for values the extraction script could only capture as a repr string
    (like machine.mem8 -> "<8-bit memory>") because they aren't a plain literal.
    There's nothing meaningful to compare those against by value, so should only check that
    the attribute exists."""
    return isinstance(value, str) and value.startswith("<") and value.endswith(">")


def check_methods(test_case: unittest.TestCase, ref_node, live_obj, path):
    """Check that all methods/ functions in the reference tree node exist in the implemented
    version of the node and are callable"""
    for method_name in ref_node["methods"]:
        with test_case.subTest(path=path, kind="method", name=method_name):
            test_case.assertTrue(
                hasattr(live_obj, method_name),
                f"{path} is missing method '{method_name}'",
            )
            if hasattr(live_obj, method_name):
                test_case.assertTrue(
                    callable(getattr(live_obj, method_name)),
                    f"{path}.{method_name} exists but is not callable",
                )


def check_constants(test_case: unittest.TestCase, ref_node, live_obj, path):
    """Check that all constants in the reference tree node exist in the implemented version of
    the node."""
    for const_name, expected in ref_node["constants"].items():
        if const_name.startswith("__"):
            # Internal marker from the extraction script for things like max_depth being
            # reached (e.g "__truncated__"), nothing to check so skip.
            continue
        with test_case.subTest(path=path, kind="constant", name=const_name):
            test_case.assertTrue(
                hasattr(live_obj, const_name),
                f"{path} is missing constant '{const_name}'",
            )
            if not hasattr(live_obj, const_name):
                continue
            if is_unrepresentable(expected):
                continue
            actual = getattr(live_obj, const_name)
            test_case.assertEqual(
                actual,
                expected,
                f"{path}.{const_name} = {repr(actual)}, expected {repr(expected)}",
            )


def check_modules(test_case: unittest.TestCase, ref_node, live_obj, path):
    """Check that modules in ref node exist in faked class.

    Modules aren't explored recursively (here or in the extraction script) as it's not needed -
    the module trees this is used against only have classes, functions and constants at the
    nested level (no nested modules defined on the board). And some classes import things like
    sys which we don't need to check for now.
    """
    for module_name in ref_node.get("modules", []):
        with test_case.subTest(path=path, kind="module", name=module_name):
            test_case.assertTrue(
                hasattr(live_obj, module_name),
                f"{path} is missing module '{module_name}'",
            )


def check_classes(test_case: unittest.TestCase, ref_node, live_obj, path):
    """Check that all classes in the reference tree node exist in faked implementation.

    Then recursively checks each child class with a call to ``check_node()``, to ensure classes
    match too.
    """
    for class_name, sub_node in ref_node["classes"].items():
        child_path = f"{path}.{class_name}"
        with test_case.subTest(path=path, kind="class", name=class_name):
            test_case.assertTrue(
                hasattr(live_obj, class_name),
                "{} is missing class '{}'".format(path, class_name),
            )
        # Will still fail in subtest but continue so other classes can be explored
        if not hasattr(live_obj, class_name):
            continue

        live_class = getattr(live_obj, class_name)
        with test_case.subTest(path=child_path, kind="class-type"):
            test_case.assertTrue(
                isinstance(live_class, type),
                f"{child_path} exists but is not a class (got {repr(type(live_class))})",
            )
        if not isinstance(live_class, type):
            continue
        if sub_node.get("ref_only"):
            # Class is already extracted somewhere else in tree so ignore.
            continue

        check_node(test_case, sub_node, live_class, child_path)


def check_node(test_case: unittest.TestCase, ref_node, live_obj, path):
    """Recursively check the items in a specific tree ref node and check they exist in the
    real fake implementation. Path used for subtest printing"""
    check_methods(test_case, ref_node, live_obj, path)
    check_constants(test_case, ref_node, live_obj, path)
    check_modules(test_case, ref_node, live_obj, path)
    check_classes(test_case, ref_node, live_obj, path)
