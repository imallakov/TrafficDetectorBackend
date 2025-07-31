from rest_framework import serializers
from .models import TrafficTask, DirectionStatistics


class DirectionStatisticsSerializer(serializers.ModelSerializer):
    """Сериализатор для статистики по направлениям"""

    class Meta:
        model = DirectionStatistics
        fields = [
            'start_direction', 'start_lane', 'end_zone',
            'start_delay', 'travel_time', 'vehicle_count'
        ]


class TrafficTaskSerializer(serializers.ModelSerializer):
    """Сериализатор для задач анализа"""
    direction_stats = DirectionStatisticsSerializer(many=True, read_only=True)

    class Meta:
        model = TrafficTask
        fields = [
            'task_id', 'user_id', 'status', 'video_filename',
            'created_at', 'completed_at', 'error_message',
            'direction_stats'
        ]


class TrafficTaskListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка задач"""

    class Meta:
        model = TrafficTask
        fields = [
            'task_id', 'status', 'video_filename',
            'created_at', 'completed_at'
        ]


class DirectionSummarySerializer(serializers.Serializer):
    """Сериализатор для сводной статистики по направлениям"""
    start_direction = serializers.IntegerField()
    start_lane = serializers.IntegerField()
    end_zone = serializers.IntegerField()
    total_vehicles = serializers.IntegerField()
    avg_start_delay = serializers.FloatField()
    avg_travel_time = serializers.FloatField()
    min_travel_time = serializers.FloatField()
    max_travel_time = serializers.FloatField()


class ErrorResponseSerializer(serializers.Serializer):
    """Сериализатор для ошибок"""
    error = serializers.CharField()
    details = serializers.CharField(required=False)
