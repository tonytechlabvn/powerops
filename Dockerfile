FROM python:3.12-slim AS backend
WORKDIR /app
COPY pyproject.toml .
COPY backend/ backend/
COPY templates/ templates/
RUN pip install --no-cache-dir .

FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

# Copy installed Python packages from backend stage
COPY --from=backend /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy application code
COPY --from=backend /app /app
COPY --from=frontend /app/dist /app/static

# Install terraform
RUN apt-get update && apt-get install -y --no-install-recommends wget unzip \
    && wget -q https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip \
    && unzip terraform_1.7.0_linux_amd64.zip -d /usr/local/bin \
    && rm terraform_1.7.0_linux_amd64.zip \
    && apt-get purge -y wget unzip && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash powerops && \
    mkdir -p /app/workspaces /app/data && \
    chown -R powerops:powerops /app
USER powerops
EXPOSE 8000
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
