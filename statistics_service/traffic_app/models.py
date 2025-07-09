from django.db import models


class TrafficData(models.Model):
    user_id = models.CharField(max_length=100)
    data = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user_id']),
        ]


class VideoProcessingResult(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    task_id = models.UUIDField(unique=True)
    user_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    output_video_path = models.CharField(max_length=500, blank=True, null=True)
    report_path = models.CharField(max_length=500, blank=True, null=True)  # Just store path
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['task_id']),
        ]
