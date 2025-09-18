import json
import logging
from datetime import datetime
from kafka import KafkaConsumer
from django.conf import settings
from django.utils import timezone
import re

from .models import TrafficTask, DirectionStatistics

logger = logging.getLogger(__name__)


class MLResultsConsumer:
    """Консьюмер для обработки результатов ML анализа"""

    def __init__(self):
        self.consumer = KafkaConsumer(
            'ml_results',
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='statistics_service_group',
            auto_offset_reset='latest',
            enable_auto_commit=True,
            session_timeout_ms=60000,
            heartbeat_interval_ms=20000,
            max_poll_interval_ms=300000  # 5 minutes
        )

    def start(self):
        """Запуск консьюмера"""
        logger.info("Starting ML Results Consumer...")

        for message in self.consumer:
            try:
                self.process_message(message.value)
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)

    def process_message(self, data):
        """Обработка сообщения из Kafka"""
        task_id = data.get('task_id')
        user_id = data.get('user_id')
        status = data.get('status')

        logger.info(f"Processing result for task {task_id} with status {status}")

        if not task_id or not user_id:
            logger.error(f"Invalid message data: missing task_id or user_id - {data}")
            return

        try:
            # Создаем или обновляем задачу
            task, created = TrafficTask.objects.update_or_create(
                task_id=task_id,
                defaults={
                    'user_id': user_id,
                    'status': status,
                    'output_video_path': data.get('output_path', ''),
                    'report_file_path': data.get('report_path', ''),
                }
            )

            if status == 'completed':
                task.completed_at = timezone.now()
                task.save()

                # Обрабатываем данные отчета
                report_data = data.get('report_data')
                if report_data:
                    self.process_report_data(task, report_data)
                else:
                    logger.warning(f"No report data for task {task_id}")

            elif status == 'failed':
                task.error_message = data.get('error', 'Unknown error')
                task.save()
                logger.warning(f"Task {task_id} failed: {task.error_message}")

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)

    def process_report_data(self, task, report_data):
        """Обработка и сохранение данных отчета"""
        logger.info(f"Processing report data for task {task.task_id}")

        # Парсим структуру отчета
        stats_to_create = []

        for key, routes in report_data.items():
            # Извлекаем end_id и метрику из ключа
            # Expected format: "(end: 0, 'start_delay')"
            end_match = re.search(r"\(end:\s*(\d+),\s*'(\w+)'\)", key)
            if not end_match:
                logger.warning(f"Could not parse key format: {key}")
                continue

            end_id = int(end_match.group(1))
            metric = end_match.group(2)

            for route_key, value in routes.items():
                if value is None:
                    continue

                # Извлекаем direction и lane
                # Expected format: "(direction: 0, lane: 1)"
                route_match = re.search(r"\(direction:\s*(\d+),\s*lane:\s*(\d+)\)", route_key)
                if not route_match:
                    logger.warning(f"Could not parse route key format: {route_key}")
                    continue

                direction_id = int(route_match.group(1))
                lane_id = int(route_match.group(2))

                # Находим или создаем запись статистики
                stat_key = {
                    'task': task,
                    'start_direction': direction_id,
                    'start_lane': lane_id,
                    'end_zone': end_id
                }

                # Ищем существующую запись в списке для создания
                existing_stat = None
                for stat in stats_to_create:
                    if (stat.task == task and
                            stat.start_direction == direction_id and
                            stat.start_lane == lane_id and
                            stat.end_zone == end_id):
                        existing_stat = stat
                        break

                if not existing_stat:
                    existing_stat = DirectionStatistics(**stat_key)
                    stats_to_create.append(existing_stat)

                # Обновляем метрику
                try:
                    if metric == 'start_delay':
                        existing_stat.start_delay = float(value)
                    elif metric == 'travel_time':
                        existing_stat.travel_time = float(value)
                    elif metric == 'vehicle_count':
                        existing_stat.vehicle_count = int(value)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not convert value {value} for metric {metric}: {e}")

        # Удаляем старые записи статистики для этой задачи
        DirectionStatistics.objects.filter(task=task).delete()

        # Создаем новые записи
        if stats_to_create:
            DirectionStatistics.objects.bulk_create(stats_to_create)
            logger.info(f"Created {len(stats_to_create)} statistics records for task {task.task_id}")
        else:
            logger.warning(f"No statistics to create for task {task.task_id}")
