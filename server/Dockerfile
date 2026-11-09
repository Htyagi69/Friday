
FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
    openssl \
    libssl3 \
    libatomic1 \
    curl \
    ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    node --version && \
    npm --version && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev

COPY . .

ENV PRISMA_USE_GLOBAL_NODE=True

RUN uv run prisma py fetch
RUN uv run prisma generate

CMD ["sh", "-c", "/app/.venv/bin/prisma db push --skip-generate && /app/.venv/bin/uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
