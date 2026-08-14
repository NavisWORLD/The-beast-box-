FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    cargo \
    curl \
    dnsutils \
    file \
    g++ \
    gcc \
    git \
    iproute2 \
    jq \
    make \
    procps \
    rustc \
    tar \
    unzip \
    xz-utils \
    zip \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 beast && useradd --uid 10001 --gid 10001 --create-home --shell /bin/bash beast

WORKDIR /opt/beastbox
COPY . /opt/beastbox
RUN python -m pip install --no-cache-dir /opt/beastbox

RUN mkdir -p /work && chown 10001:10001 /work
WORKDIR /work
USER 10001:10001

CMD ["sleep", "infinity"]
