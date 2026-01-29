# Use lightweight Python image
FROM python:3.11-slim

WORKDIR /app

# Set timezone non-interactively (Gulf region = Asia/Dubai)
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Dubai \
    DEBCONF_NONINTERACTIVE_SEEN=true

# Install minimal system dependencies
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into georoute subdirectory
COPY . ./georoute/

# Set Python path so georoute module can be found
ENV PYTHONPATH=/app

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (actual port is configured via env var)
EXPOSE 9001

# Run the application with optional hot-reload (set RELOAD=true for development)
CMD if [ "$RELOAD" = "true" ]; then \
      python -m uvicorn georoute.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload --reload-dir /app/georoute; \
    else \
      python -m uvicorn georoute.main:app --host 0.0.0.0 --port $BACKEND_PORT; \
    fi
