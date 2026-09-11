# ==============================================================================
# Dynavec Production Container Image
# Multi-stage build for Python API & Observability Dashboard
# ==============================================================================

# --- Stage 1: Build Next.js Dashboard ---
FROM node:20-alpine AS dashboard-builder
WORKDIR /app/dashboard

COPY dashboard/package*.json ./
RUN npm ci

COPY dashboard/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# --- Stage 2: Production Python & Service Runtime ---
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements & dynavec package
COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e .

# Copy Next.js built dashboard
COPY --from=dashboard-builder /app/dashboard /app/dashboard

# Copy evaluation data & configs
COPY evals/ evals/

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV AWS_REGION=us-east-1
ENV DYNAVEC_TABLE=dynavec_docs
ENV DYNAVEC_VECTOR_BUCKET=dynavec-vectors-212919533030
ENV DYNAVEC_INDEX=docs-index

EXPOSE 8779 3000

# Default command: Start live dashboard telemetry service
CMD ["python", "-m", "dynavec.dashboard"]
