# --- stage 1: build the dashboard (static files, no Node needed at runtime) ---
FROM node:20-alpine AS dashboard-build
WORKDIR /app/dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci
COPY dashboard/ ./
RUN npm run build

# --- stage 2: the actual app (bot + Flask API/dashboard server) ---
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tradingbot/ tradingbot/
COPY cli/ cli/
COPY webapp/ webapp/
COPY config/ config/
COPY --from=dashboard-build /app/dashboard/dist dashboard/dist

EXPOSE 8080
