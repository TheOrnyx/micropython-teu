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

# Initialize ssh folders and scan ecs gitlab so can pull custom MicroPython
# NOTE - if I don't end up modifying MicroPython we can always change this to just clone regular MicroPython
RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan gitlab.ecs.vuw.ac.nz >> ~/.ssh/known_hosts
RUN --mount=type=ssh \
    git clone --depth 1 \
    git@gitlab.ecs.vuw.ac.nz:course-work/project489/2026/project/silouzaki/micropython.git
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

# ------ Copy our custom classes
#
# Copy our custom test implementations of modules (fake_machine and esp_time) to the container.
#
# When copied they will be renamed to the built-in equivalent (machine and time) and placed in a
# default sys.path search location (/usr/lib/micropython) so users can run tests in the container
# with the stubs without needing any extra work

# src/teu/fake_machine -> /usr/lib/micropython/machine
COPY src/teu/fake_machine /usr/lib/micropython/machine

# src/teu/esp_time.py -> /usr/lib/micropython/time.py
COPY src/teu/esp_time.py /usr/lib/micropython/time.py

CMD ["bash"]
