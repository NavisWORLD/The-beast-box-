# ONE-SHOT ISOLATED RAILWAY EXPERIMENT ONLY. Never merge this root Dockerfile
# over the production Beast Box Dockerfile. No volume, API keys or public port.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PIP_NO_CACHE_DIR=1
WORKDIR /probe
COPY pyproject.toml README.md LICENSE ./
COPY beastbox ./beastbox
COPY tests/test_finisher_remote_anchor.py tests/test_finisher_trust_anchor.py tests/test_finisher_semantic_retrieval.py tests/test_finisher_semantic_staging.py tests/test_railway_anchor_receipt_parser.py ./tests/
COPY scripts/semantic_real_eval.py scripts/semantic_staging_acceptance.py scripts/railway_anchor_one_shot.py ./scripts/
RUN python -m pip install --disable-pip-version-check . pytest==8.4.2 cryptography==50.0.1 \
    && useradd --create-home --uid 10001 probe \
    && chown -R probe:probe /probe
USER 10001
CMD ["python", "-u", "scripts/railway_anchor_one_shot.py"]
