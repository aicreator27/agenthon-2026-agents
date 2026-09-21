FROM python:3.13-slim-bookworm@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26

LABEL qfbench2.interface_version="2.0"
LABEL qfbench2.track="coding"
LABEL qfbench2.verb="solve"
LABEL org.opencontainers.image.source="https://github.com/aicreator27/agenthon-2026-agents"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/core/src:/app/tracks/t1_agenthon/src

WORKDIR /app

COPY packaging/t1/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r /app/requirements.lock

COPY core/src /app/core/src
COPY tracks/t1_agenthon/src /app/tracks/t1_agenthon/src

RUN printf '#!/bin/sh\nexec python3 -m t1_agenthon.cli solve "$@"\n' > /usr/local/bin/solve \
    && chmod +x /usr/local/bin/solve \
    && useradd --create-home --uid 1000 runner

USER runner

CMD ["solve", "--help"]
