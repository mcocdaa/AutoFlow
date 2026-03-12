# Backend Dockerfile (Production)
# Context: Project Root
FROM python:3.10-slim

ENV PORT=8000

WORKDIR /app/backend

RUN apt-get update && apt-get install -y \
    git \
    curl \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

COPY backend/pyproject.toml backend/poetry.lock* ./

RUN poetry config virtualenvs.create false

RUN poetry install --only main --no-interaction --no-ansi --no-root

COPY backend/ .

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 4
