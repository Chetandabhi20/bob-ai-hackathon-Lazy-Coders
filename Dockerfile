# Stage 1: Build React frontend
FROM node:20-slim AS frontend
WORKDIR /app
COPY src/frontend/package.json src/frontend/package-lock.json ./src/frontend/
RUN cd src/frontend && npm ci
COPY src/frontend/ ./src/frontend/
RUN cd src/frontend && npm run build

# Stage 2: Python runtime
FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
COPY src/requirements.txt ./src/requirements.txt
RUN pip install --no-cache-dir -r src/requirements.txt

# Copy full source code
COPY . .

# Overwrite with the built frontend from stage 1
COPY --from=frontend /app/src/frontend/dist ./src/frontend/dist

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=src

CMD ["python", "-m", "api.server"]
WORKDIR /app/src
