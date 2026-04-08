# Stage 1: Base Python Image
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime Image
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from base
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application files
COPY shop_vuln.py .
COPY requirements.txt .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Expose port
EXPOSE 5000

# Run application
CMD ["python", "shop_vuln.py"]
