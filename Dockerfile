# Multi-stage: Build frontend + run backend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy built frontend to serve as static files
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy config files
COPY harness.yaml .

# Create data directory
RUN mkdir -p /data

ENV DATABASE_URL=sqlite:////data/harness.db
ENV PYTHONPATH=.

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
