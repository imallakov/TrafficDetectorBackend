import asyncio
from aiokafka import AIOKafkaConsumer
from .models import TrafficData, VideoProcessingResult
import json
import logging

logger = logging.getLogger(__name__)


async def consume_ml_results():
    """Consumer for ML results - just save file paths"""
    consumer = AIOKafkaConsumer(
        'ml_results',
        bootstrap_servers='kafka:9092',
        group_id='ml_results_group',
        auto_offset_reset='latest'
    )

    await consumer.start()
    try:
        async for message in consumer:
            try:
                data = json.loads(message.value.decode('utf-8'))
                task_id = data.get('task_id')
                user_id = data.get('user_id')
                status = data.get('status')

                logger.info(f"Received ML result for task {task_id}, status: {status}")

                # Just save the data as-is
                await asyncio.to_thread(
                    VideoProcessingResult.objects.update_or_create,
                    task_id=task_id,
                    defaults={
                        'user_id': user_id,
                        'status': status,
                        'output_video_path': data.get('output_path'),
                        'report_path': data.get('report_path'),
                        'error_message': data.get('error', data.get('message'))
                    }
                )

                logger.info(f"Saved ML result for task {task_id}")

            except Exception as e:
                logger.error(f"Error processing ML result: {e}")
    finally:
        await consumer.stop()


# Keep original consumer + add new one
async def run_all_consumers():
    """Run both consumers concurrently"""
    await asyncio.gather(
        consume_ml_results()  # New
    )
