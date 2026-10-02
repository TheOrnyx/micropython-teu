# syntax=docker/dockerfile:1

# Dockerfile for the main container image containing micropython, testing dependencies, and the stubs.
# Build should be run from project root, not this folder

# TODO - if the custom micropython doesn't really get touched we could extend one of the existing
# micropython images
FROM ubuntu:noble-20260210.1

ENV TZ=Pacific/Auckland
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ARG DEBIAN_FRONTEND=noninteractive

# Install base dependencies
RUN apt-get update --quiet && \
    apt-get install --quiet --assume-yes --no-install-recommends \
        apt-utils \
        build-essential \
        pkg-config \
        libffi-dev \
        ca-certificates \
        tzdata \
        git \
        openssh-client \
        make \
        nano \
        python3 \
        python3-pip && \
    # Cleanup step: omit while developing
    rm -rf /var/lib/apt/lists/*

# Install Python packages required for linting.
# pre-commit pylint requires native pylint version so install here.
ARG MPY_VERSION="1.27.0.post2"
RUN pip install --no-cache-dir --break-system-packages \
        pre-commit>=4.5.1 \
        pylint>=4.0.5 \
        mpy-cross==$MPY_VERSION


# ------- Cloning and building the custom micropython

WORKDIR /opt

# Removed this and replaced with regular MicroPython 1.29.0 pull as didn't end up making
# custom MicroPython build.
#
# Initialize ssh folders and scan ecs gitlab so can pull custom MicroPython
# RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan gitlab.ecs.vuw.ac.nz >> ~/.ssh/known_hosts
# RUN --mount=type=ssh \
#     git clone --depth 1 \
#     git@gitlab.ecs.vuw.ac.nz:course-work/project489/2026/project/silouzaki/micropython.git

RUN git clone --depth 1 --branch v1.29.0 https://github.com/micropython/micropython.git
WORKDIR /opt/micropython/ports/unix

RUN make -C ../../mpy-cross && \
    make submodules
RUN make

# Update path to include our MicroPython
ENV PATH="/opt/micropython/ports/unix/build-standard:${PATH}"

WORKDIR /

# TODO - maybe remove the source code once it's compiled, but not sure if it relies on any files from there

# ------- Using MicroPython to mip install dependencies -------
# Apparently /app is common place to sit at, not sure tho
COPY tools/install_mpy_mip_deps.py /tmp/install_mpy_deps.py

# Run and delete in same layer, I think removing is what people recommend?
RUN micropython -v /tmp/install_mpy_deps.py && rm /tmp/install_mpy_deps.py

# ------ Copy our custom modules
#
# Copy our custom test implementations of modules and stub implementations to the container.
#
# When copied they will be renamed to their built-in equivalent and placed in a default sys.path
# search location (/usr/lib/micropython) so users can run tests in the container with the stubs
# without needing any extra work (fake_machine becomes machine and esp_time becomes time).
#
# The esp/ board-specific modules (esp, esp32, espnow, aioespnow, network) will also be copied to
# the default sys.path location with the same name, so any code that imports these modules won't fail
#
# The teu module as a whole will also be copied to the default sys.path location as it shouldn't
# cause any problems with the copied versions and would be nice for experimenting with the libary.

# src/teu/fake_machine -> /usr/lib/micropython/machine
COPY src/teu/fake_machine /usr/lib/micropython/machine

# src/teu/esp_time.py -> /usr/lib/micropython/time.py
COPY src/teu/esp_time.py /usr/lib/micropython/time.py

# esp modules:
COPY src/teu/esp.py /usr/lib/micropython/esp.py
COPY src/teu/esp32.py /usr/lib/micropython/esp32.py
COPY src/teu/espnow.py /usr/lib/micropython/espnow.py
COPY src/teu/aioespnow.py /usr/lib/micropython/aioespnow.py
COPY src/teu/network.py /usr/lib/micropython/network.py

# Copy whole teu library:
COPY src/teu/ /usr/lib/micropython/teu

CMD ["bash"]
