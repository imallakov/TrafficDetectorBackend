FROM python:3.11-slim

# Install system dependencies (reduced list for headless OpenCV)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python packages with better timeout settings
RUN pip install --upgrade pip setuptools wheel && \
    pip install \
    --timeout 600 \
    --retries 5 \
    --prefer-binary \
    -r requirements.txt

# Copy project files
COPY . .

# Create directories
RUN mkdir -p /shared/videos /shared/sectors /shared/output /shared/reports /app/models

EXPOSE 8000

CMD ["python", "wrapper.py"]
