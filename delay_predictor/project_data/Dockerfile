# Production Dockerfile for Delay Predictor App
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libffi-dev \
    libssl-dev \
    libmariadb-dev \
    pkg-config \
    redis-tools \
    software-properties-common \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for ERPNext)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Install Yarn
RUN npm install -g yarn

# Create app directory
WORKDIR /home/frappe/frappe-bench/apps/delay_predictor

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Set proper permissions
RUN chown -R frappe:frappe /home/frappe/frappe-bench/apps/delay_predictor

# Switch to frappe user
USER frappe

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/method/ping || exit 1

# Default command
CMD ["bench", "serve", "--port", "8000", "--host", "0.0.0.0"]
