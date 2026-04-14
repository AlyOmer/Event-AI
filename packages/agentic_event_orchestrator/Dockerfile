# ============================================
# Event-AI Agentic Orchestrator Dockerfile (Multi-stage)
# ============================================

# --- Stage 1: Build/Install ---
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir uv

# Copy dependency files and install
COPY pyproject.toml uv.lock* ./
RUN uv pip install --system --no-cache -r pyproject.toml || pip install --no-cache-dir -e .

# --- Stage 2: Production ---
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root user
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start the FastAPI server (NOT chainlit)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
