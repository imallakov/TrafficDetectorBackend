from django.db import models
import uuid
from django.contrib.postgres.fields import JSONField


class TrafficTask(models.Model):
    """Основная модель для хранения задач анализа"""
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    task_id = models.UUIDField(primary_key=True, editable=False)
    user_id = models.CharField(max_length=100, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    video_filename = models.CharField(max_length=255, blank=True)
    output_video_path = models.TextField(blank=True)
    report_file_path = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]


class DirectionStatistics(models.Model):
    """Статистика по направлениям движения"""
    task = models.ForeignKey(TrafficTask, on_delete=models.CASCADE, related_name='direction_stats')
    start_direction = models.IntegerField()
    start_lane = models.IntegerField()
    end_zone = models.IntegerField()

    # Метрики
    start_delay = models.FloatField(null=True, help_text="Average start delay in seconds")
    travel_time = models.FloatField(null=True, help_text="Average travel time in seconds")
    vehicle_count = models.IntegerField(default=0, help_text="Number of vehicles")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['task', 'start_direction', 'start_lane', 'end_zone']
        indexes = [
            models.Index(fields=['task', 'end_zone']),
            models.Index(fields=['task', 'start_direction', 'start_lane']),
        ]


class VehicleMovement(models.Model):
    """Детальная информация о движении транспорта (опционально)"""
    task = models.ForeignKey(TrafficTask, on_delete=models.CASCADE, related_name='vehicle_movements')
    direction_stat = models.ForeignKey(DirectionStatistics, on_delete=models.CASCADE, related_name='movements')
    vehicle_class = models.CharField(max_length=50, blank=True)
    start_delay = models.FloatField()
    travel_time = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
