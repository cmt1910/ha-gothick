FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_INSTALL_DIR=/usr/local/bin

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        findutils \
        fontforge \
        pkg-config \
        python3 \
        python3-fontforge \
        python3-pip \
        ttfautohint \
        unzip \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /work
