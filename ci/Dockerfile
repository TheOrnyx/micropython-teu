# syntax=docker/dockerfile:1

# A Docker image containing Node.js and the Python packages required
# to lint and build the data recorder software. Choose Ubuntu as the
# base image because it is similar to Raspberry Pi OS should allow
# transferability of configuration to the build-and-test server.
#
FROM ubuntu:noble-20260210.1

ENV TZ=Pacific/Auckland
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ARG DEBIAN_FRONTEND=noninteractive

# Python is required for Lint and Build.
# Require ca-certificates for wget in the following layer to succeed;
# python3-pip depends on ca-certificates but "explicit is better than
# implicit". The git and wget packages both _recommend_ ca-certificates.
# Note: The default package archive retains only the last few versions,
# so there is limited build reproducibility conferred by version pinning.
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
        python3 \
        python3-pip && \
    # Cleanup step: omit while developing
    rm -rf /var/lib/apt/lists/*

# Python packages required for linting. These packages will change most often,
# and are easily pinned, so place them as the final layer. Work-around the
# "externally managed environment" problem introduced by PEP668 by adding the
# '--break-system-packages' flag to 'pip3 install'.
# Note: Pylint requires imported packages to be available in the environment in
# which it runs so some dependencies will need to be installed in the image;
# consider installing the project dependencies from pyproject.toml here.
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
# TODO - see if I should add my custom classes to the container, could be useful for demonstrating but not much else
# Cuz if test authors would be vendoring our library it doesn't rlly need to be in container, but not sure
# Tbh I'm just not too familiar with how python projects handle that stuff, esp micropython

CMD ["bash"]
