FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY upstream/Agenthon2026-public/common /opt/qfbench2-common
COPY upstream/track2-forecasting-public /opt/track2

RUN pip install --no-cache-dir /opt/qfbench2-common \
    && pip install --no-cache-dir /opt/track2

WORKDIR /work
ENTRYPOINT ["qfbench2-smoke"]

