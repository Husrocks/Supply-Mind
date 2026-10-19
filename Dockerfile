# ============================================================
# SupplyMind — All-in-One Multi-Stage Production Dockerfile
# Builds Frontend-v2 SPA and runs FastAPI Backend on port 7860
# Designed for Hugging Face Spaces (Docker SDK) & Linux hosts
# ============================================================

# ── Stage 1: Build React Frontend (frontend-v2) ─────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Install node dependencies
COPY frontend-v2/package*.json ./
RUN npm ci

# Copy frontend source and build optimized production bundle
COPY frontend-v2/ ./
RUN npm run build

# ── Stage 2: Python 3.11 Backend & All-in-One Runtime ───────
FROM python:3.11-slim AS runner

WORKDIR /app

# Ensure non-buffered python output and production flags
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=7860 \
    APP_ENV=production \
    DEBUG=false \
    DATABASE_URL="sqlite+aiosqlite:////app/supplymind.db"

# Install system dependencies for LightGBM, Psycopg2, and utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU first (speeds up build significantly)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user (UID 1000 required by Hugging Face Spaces)
RUN useradd -m -u 1000 user

# Copy backend application code
COPY config.py .
COPY alembic.ini .
COPY alembic/ ./alembic/
COPY api/ ./api/
COPY agent/ ./agent/
COPY models/ ./models/
COPY simulation/ ./simulation/
COPY data/ ./data/

# Copy pre-seeded SQLite database
COPY supplymind.db /app/supplymind.db

# Copy built frontend assets from Stage 1 into /app/static
COPY --from=frontend-builder /app/frontend/dist /app/static

# Ensure user 1000 owns /app so SQLite write operations can proceed
RUN chown -R user:user /app

USER user

EXPOSE 7860

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
