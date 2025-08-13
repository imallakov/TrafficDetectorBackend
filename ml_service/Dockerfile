FROM python:3.11.9-slim-buster

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements_utf8.txt .
RUN pip install --no-cache-dir -r requirements_utf8.txt

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "wrapper:app", "--host", "0.0.0.0", "--port", "8000"]
