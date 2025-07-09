from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from kafka import KafkaConsumer, KafkaProducer
import json
import subprocess
import threading
import logging
import os
from typing import Dict, Any
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ML Traffic Analysis Service", version="1.0.0")

# Kafka producer for sending results
producer = KafkaProducer(
    bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092').split(','),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Task status storage (in production, use Redis or database)
task_status: Dict[str, Dict[str, Any]] = {}


class ProcessingTask(BaseModel):
    task_id: str
    user_id: str
    video_path: str
    sector_path: str
    output_path: str
    report_path: str
    model_path: str


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ml-traffic-analysis"}


@app.post("/process")
async def process_video(
        task: ProcessingTask,
        background_tasks: BackgroundTasks
):
    """
    Process video using the original AI code
    This endpoint is mainly for direct API calls (if needed)
    """
    task_status[task.task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "Starting video processing"
    }

    # Add to background processing
    background_tasks.add_task(run_ml_processing, task.dict())

    return {
        "task_id": task.task_id,
        "status": "processing",
        "message": "Video processing started"
    }


@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get processing status of a task"""
    if task_id not in task_status:
        return {"error": "Task not found"}

    return task_status[task_id]


def run_ml_processing(task_data: dict):
    """
    Run the original ML processing code as subprocess
    This function wraps the existing main.py without modifying it
    """
    task_id = task_data['task_id']

    try:
        logger.info(f"Starting ML processing for task {task_id}")

        # Update status
        task_status[task_id] = {
            "status": "processing",
            "progress": 10,
            "message": "Initializing AI model"
        }

        # Prepare command to run original main.py
        cmd = [
            "python", "main.py",
            "--video-path", task_data['video_path'],
            "--model-path", task_data['model_path'],
            "--output-path", task_data['output_path'],
            "--report-path", task_data['report_path'],
            "--sector_path", task_data['sector_path']
        ]

        logger.info(f"Running command: {' '.join(cmd)}")

        # Update status
        task_status[task_id]["progress"] = 20
        task_status[task_id]["message"] = "Processing video frames"

        # Run the original AI processing
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd='/app'  # Make sure we're in the right directory
        )

        if result.returncode == 0:
            logger.info(f"ML processing completed successfully for task {task_id}")

            # Update status
            task_status[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": "Processing completed successfully"
            }

            # Send result to Kafka for statistics service
            result_data = {
                "task_id": task_id,
                "user_id": task_data['user_id'],
                "status": "completed",
                "output_path": task_data['output_path'],
                "report_path": task_data['report_path'],
                "message": "Video processing completed successfully"
            }

            producer.send('ml_results', result_data)
            producer.flush()

            logger.info(f"Results sent to Kafka for task {task_id}")

        else:
            logger.error(f"ML processing failed for task {task_id}: {result.stderr}")

            # Update status with error
            task_status[task_id] = {
                "status": "failed",
                "progress": 0,
                "message": f"Processing failed: {result.stderr}",
                "error": result.stderr
            }

            # Send failure notification to Kafka
            result_data = {
                "task_id": task_id,
                "user_id": task_data['user_id'],
                "status": "failed",
                "error": result.stderr,
                "message": "Video processing failed"
            }

            producer.send('ml_results', result_data)
            producer.flush()

    except Exception as e:
        logger.error(f"Exception during ML processing for task {task_id}: {str(e)}")

        # Update status with exception
        task_status[task_id] = {
            "status": "failed",
            "progress": 0,
            "message": f"Processing failed with exception: {str(e)}",
            "error": str(e)
        }

        # Send failure notification to Kafka
        result_data = {
            "task_id": task_id,
            "user_id": task_data['user_id'],
            "status": "failed",
            "error": str(e),
            "message": "Video processing failed with exception"
        }

        producer.send('ml_results', result_data)
        producer.flush()


def kafka_consumer_worker():
    """
    Kafka consumer that listens for video processing tasks
    This runs in a separate thread
    """
    consumer = KafkaConsumer(
        'video_processing_tasks',
        bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092').split(','),
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        group_id='ml_processing_group',
        auto_offset_reset='latest'
    )

    logger.info("Kafka consumer started, waiting for video processing tasks...")

    for message in consumer:
        try:
            task_data = message.value
            task_id = task_data.get('task_id', str(uuid.uuid4()))

            logger.info(f"Received task from Kafka: {task_id}")

            # Process the task
            run_ml_processing(task_data)

        except Exception as e:
            logger.error(f"Error processing Kafka message: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Start Kafka consumer when FastAPI starts"""
    # Start Kafka consumer in background thread
    consumer_thread = threading.Thread(target=kafka_consumer_worker, daemon=True)
    consumer_thread.start()
    logger.info("ML Service started with Kafka consumer")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when shutting down"""
    producer.close()
    logger.info("ML Service shutting down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
