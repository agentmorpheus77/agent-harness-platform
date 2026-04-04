# Multi-stage: Build frontend + run backend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# Install git for skills cloning at startup, and libpq for PostgreSQL
RUN apt-get update && apt-get install -y git libpq-dev && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy built frontend to serve as static files
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy config files
COPY harness.yaml .
COPY start.sh .
COPY skills/ ./skills/
RUN chmod +x start.sh

ENV PYTHONPATH=.

EXPOSE 8000

CMD ["./start.sh"]
