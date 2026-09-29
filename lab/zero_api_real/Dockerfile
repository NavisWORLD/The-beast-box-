# The image is provisioned BEFORE the container is network-isolated.
# The measured container mounts only synthetic data, checked-out Python code,
# offline hashed pretrained weights and a dedicated output directory.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2
RUN python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.6.0 && \
    python -m pip install --no-cache-dir transformers==4.49.0 huggingface-hub==0.29.3 psutil==7.0.0
WORKDIR /code
ENTRYPOINT ["python", "/code/zero_api_real_models.py"]
