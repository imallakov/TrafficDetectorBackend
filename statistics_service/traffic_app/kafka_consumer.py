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
            enable_auto_commit=True
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

    def process_report_data(self, task, report_data):
        """Обработка и сохранение данных отчета"""
        logger.info(f"Processing report data for task {task.task_id}")

        # Парсим структуру отчета
        stats_to_create = []

        for key, routes in report_data.items():
            # Извлекаем end_id и метрику из ключа
            match = re.match(r"$end: (\d+), '(\w+)'$", key)
            if not match:
                continue

            end_id = int(match.group(1))
            metric = match.group(2)

            for route_key, value in routes.items():
                if value is None:
                    continue

                # Извлекаем direction и lane
                route_match = re.match(r"$direction: (\d+), lane: (\d+)$", route_key)
                if not route_match:
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
                if metric == 'start_delay':
                    existing_stat.start_delay = float(value)
                elif metric == 'travel_time':
                    existing_stat.travel_time = float(value)
                elif metric == 'vehicle_count':
                    existing_stat.vehicle_count = int(value)

        # Удаляем старые записи статистики для этой задачи
        DirectionStatistics.objects.filter(task=task).delete()

        # Создаем новые записи
        if stats_to_create:
            DirectionStatistics.objects.bulk_create(stats_to_create)
            logger.info(f"Created {len(stats_to_create)} statistics records for task {task.task_id}")
        else:
            logger.warning(f"No statistics to create for task {task.task_id}")
