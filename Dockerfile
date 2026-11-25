FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir . && useradd --create-home appuser && mkdir -p /app/.local && chown appuser:appuser /app/.local
COPY --from=frontend /build/dist ./frontend/dist/
USER appuser
EXPOSE 8000
CMD ["uvicorn", "poker_review.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
