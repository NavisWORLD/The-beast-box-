# Build from repository root: docker build -f apps/beastbox-cloud/bridge/deploy/Dockerfile .
# Vercel remains frontend-only; Caddy fronts the loopback COSMOS owner bridge.
FROM caddy:2.10.2 AS caddy
FROM python:3.12-slim-bookworm AS production
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates gosu util-linux \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 10001 beastbox \
 && useradd --system --uid 10001 --gid beastbox --home-dir /nonexistent --shell /usr/sbin/nologin beastbox
COPY --from=caddy /usr/bin/caddy /usr/local/bin/caddy
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY beastbox/ beastbox/
COPY apps/beastbox-cloud/bridge/ apps/beastbox-cloud/bridge/
RUN pip install --no-cache-dir --no-compile '.[secure]' 'azure-storage-blob>=12.20,<13' \
 && install -d -m 0700 -o beastbox -g beastbox /srv/beastbox/data \
 && chmod 0755 apps/beastbox-cloud/bridge/deploy/start.sh
EXPOSE 8080
ENTRYPOINT ["/app/apps/beastbox-cloud/bridge/deploy/start.sh"]
