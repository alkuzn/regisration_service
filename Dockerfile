FROM python:3.12-slim AS basestage
WORKDIR /app
RUN apt-get update && \
apt-get install -y --no-install-recommends curl && \
rm -rf /var/lib/apt/lists/*
COPY uv.lock pyproject.toml README.md .python-version /app
RUN \
--mount=type=cache,target=/root/.cache/uv \
--mount=type=cache,target=/root/.cache/pip \
pip install uv &&  uv sync --frozen --no-dev --no-install-project

FROM basestage AS second
WORKDIR /app
COPY src/auth_service/__init__.py /app/src/auth_service/__init__.py
RUN \
--mount=type=cache,target=/root/.cache/uv \
uv sync --frozen --no-dev

FROM second
WORKDIR /app
COPY src ./src
COPY keys /app/keys
EXPOSE ${APP_PORT}
CMD uv run --no-sync -m auth_service