from rest_framework import serializers
from .models import VideoTask


class DirectionROISerializer(serializers.Serializer):
    """Structure for directional ROI data"""
    directions = serializers.ListField(
        child=serializers.ListField(
            child=serializers.ListField(
                child=serializers.ListField(child=serializers.IntegerField())
            )
        ),
        help_text="Array of directions, each containing arrays of lane polygons"
    )
    end_region = serializers.ListField(
        child=serializers.ListField(
            child=serializers.ListField(child=serializers.IntegerField())
        ),
        help_text="Array of end region polygons for each direction"
    )


class VideoUploadSerializer(serializers.Serializer):
    """Video upload request structure"""
    video = serializers.FileField(help_text="Video file (MP4, AVI, MOV formats supported)")
    roi_data = serializers.CharField(help_text="JSON string containing directions and end_region data")


class VideoUploadResponseSerializer(serializers.Serializer):
    """Video upload response structure"""
    task_id = serializers.UUIDField(help_text="Unique task identifier for tracking")
    status = serializers.CharField(help_text="Current task status")
    message = serializers.CharField(help_text="Success message")


class TaskStatusResponseSerializer(serializers.ModelSerializer):
    """Task status response structure"""
    task_id = serializers.UUIDField(help_text="Unique task identifier")

    class Meta:
        model = VideoTask
        fields = ['task_id', 'status', 'created_at', 'updated_at', 'original_filename', 'error_message']


class UserTasksResponseSerializer(serializers.Serializer):
    """User tasks list response structure"""
    tasks = TaskStatusResponseSerializer(many=True, help_text="List of user's tasks")


class ErrorResponseSerializer(serializers.Serializer):
    """Error response structure"""
    error = serializers.CharField(help_text="Error message")
    details = serializers.CharField(required=False, help_text="Additional error details")
