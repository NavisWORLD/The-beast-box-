FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY beastbox ./beastbox
RUN python -m pip install --no-cache-dir .
RUN useradd --create-home --uid 10001 beastbox && chown -R beastbox:beastbox /app
USER beastbox
ENTRYPOINT ["beastbox"]
CMD ["run", "--condition", "E20"]
