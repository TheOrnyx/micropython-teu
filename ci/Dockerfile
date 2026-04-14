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
        ca-certificates \
        tzdata \
        git \
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

CMD ["bash"]
