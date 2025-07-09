import requests
import json
import os
import uuid
from kafka import KafkaProducer
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def validate_user_token(token):
    """Validates JWT token through Auth Service"""
    try:
        if token.startswith('Bearer '):
            token = token[7:]

        response = requests.post(
            f"{settings.AUTH_SERVICE_URL}/auth/validate-token/",
            json={"token": token},
            timeout=5
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {"valid": False, "error": "Invalid token"}

    except requests.RequestException as e:
        logger.error(f"Cannot reach auth service: {e}")
        return {"valid": False, "error": f"Auth service unavailable: {e}"}


def save_video_file(video_file, user_id):
    """Saves uploaded video to shared storage"""
    try:
        # Create unique filename
        file_extension = os.path.splitext(video_file.name)[1]
        filename = f"video_{user_id}_{uuid.uuid4()}{file_extension}"

        # Save to shared volume
        video_dir = os.path.join(settings.SHARED_STORAGE_PATH, 'videos')
        os.makedirs(video_dir, exist_ok=True)
        video_path = os.path.join(video_dir, filename)

        with open(video_path, 'wb') as f:
            for chunk in video_file.chunks():
                f.write(chunk)

        logger.info(f"Video saved: {video_path}")
        return video_path

    except Exception as e:
        logger.error(f"Error saving video: {e}")
        raise


def create_sector_json(roi_data, user_id):
    """Creates JSON file with sector coordinates for ML service"""
    try:
        # Convert ROI data to ML service format
        sector_data = {
            "sectors": [
                {
                    "sector_id": roi_data.get("sector_id", 1),
                    "region_start": {"coords": roi_data["start_region"]},
                    "region_end": {"coords": roi_data["end_region"]},
                    "lanes": [{"coords": lane} for lane in roi_data["lanes"]],
                    "lanes_count": roi_data["lanes_count"],
                    "sector_length": roi_data["length_km"],
                    "max_speed": roi_data["max_speed"]
                }
            ]
        }

        # Save JSON file
        json_dir = os.path.join(settings.SHARED_STORAGE_PATH, 'sectors')
        os.makedirs(json_dir, exist_ok=True)
        json_filename = f"sectors_{user_id}_{uuid.uuid4()}.json"
        json_path = os.path.join(json_dir, json_filename)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(sector_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Sector JSON created: {json_path}")
        return json_path

    except Exception as e:
        logger.error(f"Error creating sector JSON: {e}")
        raise


def send_to_kafka(task_data):
    """Sends task to Kafka for ML service"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=[settings.KAFKA_BOOTSTRAP_SERVERS],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

        producer.send('video_processing_tasks', task_data)
        producer.flush()
        producer.close()

        logger.info(f"Task sent to Kafka: {task_data['task_id']}")
        return True

    except Exception as e:
        logger.error(f"Error sending to Kafka: {e}")
        return False
