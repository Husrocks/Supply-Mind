# Build stage for frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Build stage for backend
FROM python:3.10-slim AS backend
WORKDIR /app

# Install system dependencies for psycopg2 and lightgbm
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY config.py .
COPY api/ ./api/
COPY agent/ ./agent/
COPY models/ ./models/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Copy built frontend (optional if serving from FastAPI, but typically handled by separate server)
# COPY --from=frontend-builder /app/frontend/dist /app/static

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
