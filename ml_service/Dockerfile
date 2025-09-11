FROM ultralytics/ultralytics:latest-python

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create models directory and download YOLOv10s model
RUN mkdir -p /app/models
RUN python -c "from ultralytics import YOLO; import shutil; model = YOLO('yolov10s.pt'); shutil.move('yolov10s.pt', '/app/models/yolov10s.pt'); print('YOLOv10s model downloaded to /app/models/')"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "wrapper:app", "--host", "0.0.0.0", "--port", "8000"]