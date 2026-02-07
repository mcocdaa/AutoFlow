# Backend Production Dockerfile
FROM python:3.10-slim as base

# 1. Initialize env_manager
WORKDIR /opt/env_manager
COPY tools/env_manager/ .
# Since we are on Windows host, script might not be executable.
# We run it directly with bash.
RUN apt-get update && apt-get install -y bash && \
    chmod +x bootstrap.sh && ./bootstrap.sh

# 2. Install Backend Dependencies
WORKDIR /app/backend
COPY backend/setup.yaml .
COPY backend/pyproject.toml .
# We need the manager tool available.
# Since we copied it to /opt/env_manager, we can invoke it.
RUN python3 /opt/env_manager/main.py install --scope=prod --root /app/backend

# 3. Runtime Stage
FROM python:3.10-slim
WORKDIR /app

# Copy installed python packages from builder
COPY --from=base /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy Application Code
COPY backend/ .

# Runtime Command
# Assuming main entry point is app.main:app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
