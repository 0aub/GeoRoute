# Use PyTorch official image with CUDA 12.1 support
# This includes Python 3.10, PyTorch 2.1, and CUDA pre-installed (~4GB image)
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Set timezone non-interactively (Gulf region = Asia/Dubai)
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Dubai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install system dependencies for geospatial libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    libgdal-dev \
    gdal-bin \
    libgeos-dev \
    libproj-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables for rasterio
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# PyTorch and torchvision are already installed in base image, so skip them
RUN pip install --no-cache-dir \
    segment-geospatial>=0.11.0 \
    opencv-python-headless>=4.8.0 \
    Pillow>=10.0.0 \
    scipy>=1.11.0 \
    && pip install --no-cache-dir -r requirements.txt

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
