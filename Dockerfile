# UltraSwarm - Multi-Agent AI System
# Cross-platform Docker image for Windows and Linux
# Supports browser automation with Playwright

# Use Python 3.11 slim as base
FROM python:3.11-slim-bookworm

LABEL maintainer="UltraSwarm Team"
LABEL description="Multi-agent AI swarm for e-commerce automation"
LABEL version="1.0.0"

# Build arguments for platform detection
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Playwright configuration
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 \
    # Browser-use configuration
    BROWSER_HEADLESS=true \
    BROWSER_USE_AUTO_START=true \
    BROWSER_USE_CDP_PORT=9222 \
    # Disable Playwright automatic browser management on Arch Linux
    PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1

# Install system dependencies for Playwright and browser automation
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    build-essential \
    # Playwright dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    # Additional browser dependencies
    libatspi2.0-0 \
    libxshmfence1 \
    libglu1-mesa \
    # Fonts for proper rendering
    fonts-liberation \
    fonts-noto-color-emoji \
    # Network utilities
    curl \
    wget \
    # Process management
    procps \
    # X11 for headless browser (virtual display)
    xvfb \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt \
    # Install playwright browsers (Chromium only for smaller image)
    && playwright install chromium \
    && playwright install-deps chromium

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/outputs \
    /app/knowledge \
    /app/agent_workspace \
    /app/.browser-profile

# Set permissions
RUN chmod -R 755 /app

# Create a non-root user for security
RUN useradd -m -s /bin/bash swarmuser \
    && chown -R swarmuser:swarmuser /app /ms-playwright

# Switch to non-root user
USER swarmuser

# Default environment
ENV HOME=/home/swarmuser

# Expose browser CDP port (optional, for external browser connection)
EXPOSE 9222

# Default command - interactive menu
CMD ["python", "main.py"]
