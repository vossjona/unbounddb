# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm AS builder

ARG DEBIAN_FRONTEND=noninteractive

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.9.2 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable --no-dev

FROM builder AS ci

ENV PATH="/app/.venv/bin:$PATH"

# install dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --group dev --group doc

# copy files and folders
COPY . .

# keep the container running
CMD ["sleep", "infinity"]

FROM python:3.11-slim-bookworm AS release

# https://specs.opencontainers.org/image-spec/annotations/
LABEL org.opencontainers.image.title="UnboundDB" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.description="Helps with Unbound" \
      org.opencontainers.image.authors="Jonas" \
      org.opencontainers.image.source="https://github.com/vossjona/unbounddb"

ARG UID=1000
ARG GID=1000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
	PATH="/app/.venv/bin:$PATH"

# create group and user mgm:mgm
RUN groupadd -g ${GID} -r mgm && useradd -u ${UID} --no-log-init -r -g mgm mgm

WORKDIR /app

# copy the virtual environment from the builder (thus we don't need to install anything)
COPY --chown=mgm:mgm --from=builder /app/.venv ./.venv

# copy python source files
COPY --chown=mgm:mgm unbounddb ./unbounddb

# use mgm user instead of root
USER mgm:mgm
