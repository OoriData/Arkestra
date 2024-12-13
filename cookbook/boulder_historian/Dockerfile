# Stage 1: Builder
FROM python:3.12.6-slim AS builder

# Set environment variables to reduce Python behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install necessary build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy and install Python dependencies
# COPY requirements.txt constraints.txt ./
# RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
# FROM python:3.12.6-slim
# Image comes with all necessary system dependencies for Playwright
FROM mcr.microsoft.com/playwright/python:v1.41.0-focal

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Install playwright headless browser
RUN python -m playwright install --with-deps chromium firefox webkit
# ensures the non-root user below can access the installed browsers
RUN chmod -R 777 /ms-playwright

# # RUN playwright install
# # RUN playwright install-deps
# RUN sudo python -m playwright install
# RUN sudo python -m playwright install-deps
# # RUN python -m playwright install chromium

# Set up the working directory
WORKDIR /app

# Copy your application code
COPY . .

# Create and switch to a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["python", "get_markdown.py"]

# Health check
# HEALTHCHECK CMD curl --fail http://localhost:9000/health || exit 1

# Expose port
# EXPOSE 9000

# Set the entrypoint
# ENTRYPOINT ["hypercorn", "main:app", "--bind=0.0.0.0:9000"]
