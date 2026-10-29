# syntax=docker/dockerfile:1

# ---- 1. Build the React frontend ----
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 2. Python runtime serving the API and the built frontend ----
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    STATIC_DIR=/app/static \
    DATA_DIR=/app/data
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/scripts ./scripts
# Optional pre-fetched snapshot (python -m scripts.fetch_data); fetched on first start if absent.
COPY backend/data ./data
COPY --from=frontend /frontend/dist ./static
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
# Heroku injects $PORT at runtime.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
