FROM python:3.13-slim-bookworm

LABEL qfbench2.interface_version="2.0"
LABEL qfbench2.track="forecasting"
LABEL qfbench2.verb="forecast"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/core/src:/app/tracks/t2_agenthon/src

WORKDIR /app

COPY packaging/t2/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r /app/requirements.lock

COPY core/src /app/core/src
COPY tracks/t2_agenthon/src /app/tracks/t2_agenthon/src

RUN printf '#!/bin/sh\nexec python3 -m t2_agenthon.cli "$@"\n' > /usr/local/bin/forecast \
    && chmod +x /usr/local/bin/forecast \
    && useradd --create-home --uid 1000 runner

USER runner

CMD ["forecast", "--help"]

