from rest_framework import serializers
from .models import VideoTask


class ROIDataSerializer(serializers.Serializer):
    """ROI (Region of Interest) data structure"""
    sector_id = serializers.IntegerField(default=1, help_text="Unique sector identifier")
    start_region = serializers.ListField(
        child=serializers.ListField(child=serializers.IntegerField()),
        help_text="Start region coordinates as array of [x,y] points"
    )
    end_region = serializers.ListField(
        child=serializers.ListField(child=serializers.IntegerField()),
        help_text="End region coordinates as array of [x,y] points"
    )
    lanes = serializers.ListField(
        child=serializers.ListField(child=serializers.ListField(child=serializers.IntegerField())),
        help_text="Array of lane coordinates, each lane is array of [x,y] points"
    )
    lanes_count = serializers.IntegerField(help_text="Number of lanes in the sector")
    length_km = serializers.FloatField(help_text="Length of the sector in kilometers")
    max_speed = serializers.IntegerField(help_text="Maximum speed limit in km/h")


class VideoUploadSerializer(serializers.Serializer):
    """Video upload request structure"""
    video = serializers.FileField(help_text="Video file (MP4, AVI, MOV formats supported)")
    roi_data = serializers.CharField(help_text="JSON string containing ROI data structure")


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
