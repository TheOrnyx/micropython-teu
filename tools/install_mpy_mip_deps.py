"""Little helper script to install the different MicroPython mip
dependencies we need for testing on the pipeline.

Mainly used by the dockerfile build."""

import mip

REQUIRED_DEPS = ["unittest", "logging"]

# One of the default sys.path locations, should be good for container
DEFAULT_INSTALL_DIR = "/usr/lib/micropython"


def install_deps(deps, target_folder=None, mpy=False):
    """Install dependencies in deps to target folder, as .py instead of compiled .mpy"""
    for dep in deps:
        mip.install(dep, target=target_folder, mpy=mpy)


if __name__ == "__main__":
    install_deps(REQUIRED_DEPS, target_folder=DEFAULT_INSTALL_DIR)
