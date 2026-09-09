FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update && \
    apt-get install -y openssl libssl3 && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN pip install uv

RUN uv sync --locked --no-dev --no-install-project

COPY . .

RUN uv run prisma generate
RUN uv run prisma py fetch

CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port $PORT"]