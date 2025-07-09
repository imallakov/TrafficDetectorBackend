from django.db import models
import uuid


class VideoTask(models.Model):
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('queued', 'Queued for Processing'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    task_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user_id = models.CharField(max_length=100)
    original_filename = models.CharField(max_length=255)
    video_path = models.CharField(max_length=500)
    sector_config = models.JSONField()  # ROI data from frontend
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Task {self.task_id} - {self.status}"
