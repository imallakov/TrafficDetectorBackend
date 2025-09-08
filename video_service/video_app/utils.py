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
        logger.info(f"Validating token: {token[:20]}...")

        if token.startswith('Bearer '):
            token = token[7:]

        logger.info(f"Sending request to auth service: {settings.AUTH_SERVICE_URL}/auth/validate-token/")
        response = requests.post(
            f"{settings.AUTH_SERVICE_URL}/auth/validate-token/",
            json={"token": token},
            timeout=5
        )

        logger.info(f"Auth service response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Auth service response: {result}")
            return result
        else:
            logger.error(f"Auth service error: {response.status_code} - {response.text}")
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


def create_region_json(roi_data, user_id):
    """
    Creates JSON file with directions and end regions for ML service
    The data is saved directly as received from frontend without transformation
    """
    try:
        # Validate required fields
        if 'directions' not in roi_data or 'end_region' not in roi_data:
            raise ValueError("ROI data must contain 'directions' and 'end_region' fields")

        # Save JSON file as-is (ML service expects this exact format)
        json_dir = os.path.join(settings.SHARED_STORAGE_PATH, 'regions')
        os.makedirs(json_dir, exist_ok=True)
        json_filename = f"regions_{user_id}_{uuid.uuid4()}.json"
        json_path = os.path.join(json_dir, json_filename)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(roi_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Region JSON created: {json_path}")
        return json_path

    except Exception as e:
        logger.error(f"Error creating region JSON: {e}")
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
