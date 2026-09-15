# Stage 1: Build the React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app

# Copy package files
COPY src/frontend/package.json src/frontend/package-lock.json* ./src/frontend/
WORKDIR /app/src/frontend
RUN npm ci || npm install

# Copy frontend source and build
COPY src/frontend/ ./
RUN npm run build

# Stage 2: Build the Python backend
FROM python:3.11-slim
WORKDIR /app

# Install backend dependencies
COPY src/requirements.txt ./src/
RUN pip install --no-cache-dir -r src/requirements.txt

# Copy the backend source code
COPY src/ ./src/

# Copy the built frontend from Stage 1
COPY --from=frontend-builder /app/src/frontend/dist ./src/frontend/dist

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Set working directory to src so relative paths work (like in nixpacks)
WORKDIR /app/src

# Start the server (Railway dynamically injects the PORT env var)
CMD ["python", "-m", "api.server"]
