FROM python:3.11-slim

# Install system dependencies for OpenCV and ML libraries
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python packages with timeout and retry options
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --timeout 300 --retries 3 -r requirements.txt

# Copy all project files
COPY . .

# Create necessary directories
RUN mkdir -p /shared/videos /shared/sectors /shared/output /shared/reports /app/models

# Expose port
EXPOSE 8000

# Run the wrapper
CMD ["python", "wrapper.py"]
