# AutoFlow Integrated Production Dockerfile (Backend + Frontend)

# ==========================================
# Stage 1: Backend Builder
# ==========================================
FROM python:3.10-slim AS backend-builder

# Initialize env_manager
WORKDIR /opt/env_manager
COPY tools/env_manager/ .
RUN apt-get update && apt-get install -y bash && \
    chmod +x bootstrap.sh && ./bootstrap.sh

# Install Backend Dependencies
WORKDIR /app/backend
COPY backend/setup.yaml .
COPY backend/pyproject.toml .
# Use env_manager to install prod dependencies
RUN python3 /opt/env_manager/main.py install --scope=prod --root /app/backend


# ==========================================
# Stage 2: Frontend Builder
# ==========================================
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend dependency files
COPY frontend/package.json frontend/package-lock.json* ./
COPY frontend/setup.yaml ./

# Install and Build
RUN npm ci
COPY frontend/ .
RUN npm run build


# ==========================================
# Stage 3: Final Production Image
# ==========================================
FROM python:3.10-slim

WORKDIR /app

# 1. Install System Dependencies (Runtime only)
# We assume libpq is needed for runtime if using postgres
RUN apt-get update && apt-get install -y libpq5 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Copy Python Environment from Backend Builder
COPY --from=backend-builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# 3. Copy Frontend Static Files from Frontend Builder
# We place them in /app/static, assuming FastAPI is configured to serve this directory
COPY --from=frontend-builder /app/frontend/dist /app/static

# 4. Copy Backend Source Code
COPY backend/ /app/

# 5. Start Application
# Environment variable to tell backend to serve static files
ENV SERVE_STATIC_FILES=true
ENV STATIC_FILES_DIR=/app/static

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
