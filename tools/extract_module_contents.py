"""extract_module_contents.py - Tool script to recursively extract the contents of a module.

Meant for use on the ESP32 to extract the available classes, methods, and constants available
so can evaluate stubs to make sure every available item is implemented and constants match
board values.

Takes in a target module and recursively walks it, collecting available classes, methods,
and constants. Then for each found class it will collect those contents, etc. Currently it
doesn't recursively collect modules but this should be fine as I don't think any of the classes
have another module.

Result should be a tree dict with values describing:

  * Constants (name -> value)
  * methods/funcs (name only, can't collect signature)
  * classes (name -> dict of extracted items)
  * modules (just module name for now)

Designed for `machine` but should be usable with the `esp` and `esp32` modules.
"""

# sys import to extract the type of a module
import sys

_ModuleType = type(sys)


def _is_class(obj):
    return isinstance(obj, type)


def _is_module(obj):
    return isinstance(obj, _ModuleType)


def _sanitize(value, _depth=0):
    """Reduce a value to something that prints as valid, literal Python.

    Also recursively sanitizes list and tuple items, shouldn't be many list items but just in
    case.
    """
    if isinstance(value, (int, float, str, bool, bytes, type(None))):
        return value
    if isinstance(value, (tuple, list)) and _depth < 4:
        items = [_sanitize(v, _depth + 1) for v in value]
        return tuple(items) if isinstance(value, tuple) else items
    # Anything else (bound objects, descriptors, singleton instances, etc) gets stored as its
    # repr so the whole tree still prints/copies cleanly.
    try:
        return repr(value)
    except Exception:
        return "<unrepresentable>"


def _public_members(obj):
    """Collect member {name: value} for non-dunder, non-private attributes of obj."""
    members = {}
    for name in dir(obj):
        if name.startswith("_"):  # Ignore private
            continue
        try:
            members[name] = getattr(obj, name)
        except Exception as exc:
            members[name] = f"<error reading attribute: {exc}>"
    return members


def _build_node(obj, name, seen, max_depth, depth):
    """Build a tree node for a specific module/class `obj`.

    Avoids exploring already explored classes.
    """
    node = {"name": name, "constants": {}, "methods": [], "classes": {}, "modules": []}

    if depth > max_depth:
        node["constants"]["__truncated__"] = "max_depth reached"
        return node

    for attr_name, value in _public_members(obj).items():
        if isinstance(value, str) and value.startswith("<error reading attribute:"):
            node["constants"][attr_name] = value

        elif _is_class(value):
            key = id(value)
            if key in seen:
                # Same class object already expanded elsewhere in the tree,
                # record reference without recursing again
                node["classes"][attr_name] = {"name": attr_name, "ref_only": True}
            else:
                seen.add(key)
                node["classes"][attr_name] = _build_node(
                    value, attr_name, seen, max_depth, depth + 1
                )
        elif _is_module(value):
            # Don't recurse into modules, just record that they exist.
            # TODO - could make recursively explore modules but not necessary for now.
            node["modules"].append(attr_name)
        elif callable(value):
            node["methods"].append(attr_name)
        else:
            # Store extracted value of constant
            node["constants"][attr_name] = _sanitize(value)

    return node


def build_tree(module, module_name, max_depth=6):
    """Build the introspection tree for `module`, named `module_name`."""
    seen = set()
    seen.add(id(module))  # Use id for set instead of name
    return _build_node(module, module_name, seen, max_depth, depth=0)


if __name__ == "__main__":
    # Just running from command will extract machine contents, print to stdout and output to file.
    # Can be ran with mpremote run or copied to board and ran in repl.
    # TODO - maybe add cli args

    import machine

    tree = build_tree(machine, "machine")

    # Plain dict, can copy
    print(tree)

    # Also write the tree to a file on the device so it can optionally be copied
    # with `mpremote cp :machine_tree.py .` instead of copying terminal output.
    try:
        with open("machine_tree.py", "w") as f:
            f.write("MACHINE_TREE = ")
            f.write(repr(tree))
            f.write("\n")
    except Exception as exc:
        print(f"(could not write machine_tree.py: {exc})")
