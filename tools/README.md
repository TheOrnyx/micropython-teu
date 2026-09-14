# Utilities and Tools

This folder contains scripts for helping out with processes like pipeline setup and testing.

Here's a little table of the tools and what they do

| Script                                                     | Description                                                                                                                                           |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`run_tests.py`](run_tests.py)                             | Sets up the module path and runs the tests, used in pipeline                                                                                          |
| [`install_mpy_mip_deps.py`](install_mpy_mip_deps.py)       | Installs the testing dependencies to `/usr/lib/micropython`, used by container build                                                                  |
| [`extract_module_contents.py`](extract_module_contents.py) | Script to recursively extract the contents of a specific module into a tree dictionary, used to test that implemented stub items match board contents |
