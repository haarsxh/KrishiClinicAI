FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for asyncpg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple

# Copy application code
COPY . .

# Bundle the local EfficientNetV2-S weights for zero-network offline inference.
# Only AI_PROVIDER=local needs them, so a failed fetch is a warning by default.
# Set REQUIRE_WEIGHTS=true (with HF_TOKEN if the repo is private) to make it fatal.
ARG HF_TOKEN=""
ARG REQUIRE_WEIGHTS="false"
ARG MODEL_REPO_ID="the-harsh-vardhan/krishiclinic-crop-disease-v0-1-baseline-bmd"
RUN HF_TOKEN="$HF_TOKEN" \
    REQUIRE_WEIGHTS="$REQUIRE_WEIGHTS" \
    MODEL_REPO_ID="$MODEL_REPO_ID" \
    python scripts/prefetch_weights.py

# Create uploads directory
RUN mkdir -p uploads

# Make start script executable (handle both LF and CRLF)
COPY start.sh .
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

EXPOSE 8000

# Use start script for proper startup sequencing
ENTRYPOINT ["./start.sh"]
