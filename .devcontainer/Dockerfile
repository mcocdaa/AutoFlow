# Development Environment Dockerfile (Full Stack)
# Provides a complete toolchain for both Python and Node.js development.
# Actual dependencies are installed at runtime via postCreateCommand.

FROM python:3.10-slim

# 1. Initialize env_manager tools
WORKDIR /opt/env_manager
COPY tools/env_manager/ .
# Install basic system tools required for development and env_manager
RUN apt-get update && apt-get install -y \
    bash \
    git \
    curl \
    vim \
    procps \
    && chmod +x bootstrap.sh && ./bootstrap.sh

# 2. Install Node.js Toolchain (for Frontend Dev)
# We install the tools, but not the project dependencies yet
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# 3. Cleanup
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Note: We do NOT copy or install setup.yaml here.
# The source code (including setup.yaml) will be mounted at /workspace
# when the DevContainer starts.
# The 'postCreateCommand' in devcontainer.json will handle the installation:
# "python3 /workspace/tools/env_manager/main.py install --scope=dev --root /workspace"
