FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update && \
    apt-get install -y openssl libssl3 libatomic1 && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN pip install uv

RUN uv sync --locked --no-dev

COPY . .

RUN uv run prisma py fetch
RUN uv run prisma generate

CMD ["sh", "-c", "/app/.venv/bin/prisma db push && /app/.venv/bin/uvicorn main:app --host 0.0.0.0 --port $PORT"]