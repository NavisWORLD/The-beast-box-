FROM python:3.12-slim-bookworm

RUN python3 --version && python --version
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

RUN groupadd --gid 10001 zeref \
    && useradd --uid 10001 --gid 10001 --create-home --shell /bin/bash zeref \
    && mkdir -p /work /state /opt/zeref \
    && chown -R 10001:10001 /work /state /home/zeref

USER 10001:10001
WORKDIR /work
CMD ["sleep", "infinity"]
