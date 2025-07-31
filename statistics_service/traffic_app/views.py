from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Avg, Sum, Min, Max, Count, Q
from django.utils import timezone
from datetime import timedelta
import logging

from .models import TrafficTask, DirectionStatistics
from .serializers import (
    TrafficTaskSerializer, TrafficTaskListSerializer,
    DirectionStatisticsSerializer, DirectionSummarySerializer,
    ErrorResponseSerializer
)
from .utils import validate_user_token

logger = logging.getLogger(__name__)


class TaskStatisticsView(APIView):
    """Получение статистики по конкретной задаче"""

    @swagger_auto_schema(
        operation_summary="Get task statistics",
        operation_description="Retrieve traffic analysis statistics for a specific task",
        manual_parameters=[
            openapi.Parameter(
                'Authorization',
                openapi.IN_HEADER,
                description="Bearer JWT token",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: TrafficTaskSerializer,
            401: ErrorResponseSerializer,
            404: ErrorResponseSerializer
        }
    )
    def get(self, request, task_id):
        # Проверка авторизации
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return Response({'error': 'Authorization header missing'},
                            status=status.HTTP_401_UNAUTHORIZED)

        auth_result = validate_user_token(auth_header)
        if not auth_result.get('valid'):
            return Response({'error': 'Invalid token'},
                            status=status.HTTP_401_UNAUTHORIZED)

        user_id = auth_result['user_id']

        try:
            task = TrafficTask.objects.prefetch_related('direction_stats').get(
                task_id=task_id,
                user_id=user_id
            )
            serializer = TrafficTaskSerializer(task)
            return Response(serializer.data)

        except TrafficTask.DoesNotExist:
            return Response({'error': 'Task not found'},
                            status=status.HTTP_404_NOT_FOUND)


class UserTasksListView(APIView):
    """Получение списка задач пользователя"""

    @swagger_auto_schema(
        operation_summary="Get user tasks",
        operation_description="Retrieve all traffic analysis tasks for the authenticated user",
        manual_parameters=[
            openapi.Parameter(
                'Authorization',
                openapi.IN_HEADER,
                description="Bearer JWT token",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filter by status",
                type=openapi.TYPE_STRING,
                enum=['processing', 'completed', 'failed']
            ),
            openapi.Parameter(
                'days',
                openapi.IN_QUERY,
                description="Filter by last N days",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: TrafficTaskListSerializer(many=True),
            401: ErrorResponseSerializer
        }
    )
    def get(self, request):
        # Проверка авторизации
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return Response({'error': 'Authorization header missing'},
                            status=status.HTTP_401_UNAUTHORIZED)

        auth_result = validate_user_token(auth_header)
        if not auth_result.get('valid'):
            return Response({'error': 'Invalid token'},
                            status=status.HTTP_401_UNAUTHORIZED)

        user_id = auth_result['user_id']

        # Базовый queryset
        tasks = TrafficTask.objects.filter(user_id=user_id)

        # Фильтры
        status_filter = request.query_params.get('status')
        if status_filter:
            tasks = tasks.filter(status=status_filter)

        days_filter = request.query_params.get('days')
        if days_filter:
            try:
                days = int(days_filter)
                date_from = timezone.now() - timedelta(days=days)
                tasks = tasks.filter(created_at__gte=date_from)
            except ValueError:
                pass

        tasks = tasks.order_by('-created_at')
        serializer = TrafficTaskListSerializer(tasks, many=True)

        return Response({
            'count': tasks.count(),
            'tasks': serializer.data
        })


class DirectionSummaryView(APIView):
    """Агрегированная статистика по направлениям"""

    @swagger_auto_schema(
        operation_summary="Get direction summary",
        operation_description="Get aggregated statistics for traffic directions",
        manual_parameters=[
            openapi.Parameter(
                'Authorization',
                openapi.IN_HEADER,
                description="Bearer JWT token",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'task_ids',
                openapi.IN_QUERY,
                description="Comma-separated list of task IDs",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'start_direction',
                openapi.IN_QUERY,
                description="Filter by start direction",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'end_zone',
                openapi.IN_QUERY,
                description="Filter by end zone",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: DirectionSummarySerializer(many=True),
            401: ErrorResponseSerializer
        }
    )
    def get(self, request):
        # Проверка авторизации
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return Response({'error': 'Authorization header missing'},
                            status=status.HTTP_401_UNAUTHORIZED)

        auth_result = validate_user_token(auth_header)
        if not auth_result.get('valid'):
            return Response({'error': 'Invalid token'},
                            status=status.HTTP_401_UNAUTHORIZED)

        user_id = auth_result['user_id']

        # Базовый queryset
        stats = DirectionStatistics.objects.filter(
            task__user_id=user_id,
            task__status='completed'
        )

        # Фильтры
        task_ids = request.query_params.get('task_ids')
        if task_ids:
            task_id_list = [tid.strip() for tid in task_ids.split(',')]
            stats = stats.filter(task__task_id__in=task_id_list)

        start_direction = request.query_params.get('start_direction')
        if start_direction:
            stats = stats.filter(start_direction=int(start_direction))

        end_zone = request.query_params.get('end_zone')
        if end_zone:
            stats = stats.filter(end_zone=int(end_zone))

        # Агрегация
        summary = stats.values(
            'start_direction', 'start_lane', 'end_zone'
        ).annotate(
            total_vehicles=Sum('vehicle_count'),
            avg_start_delay=Avg('start_delay'),
            avg_travel_time=Avg('travel_time'),
            min_travel_time=Min('travel_time'),
            max_travel_time=Max('travel_time')
        ).filter(
            total_vehicles__gt=0
        ).order_by('start_direction', 'start_lane', 'end_zone')

        return Response({
            'count': summary.count(),
            'summary': list(summary)
        })


class DownloadReportView(APIView):
    """Скачивание файла отчета"""

    @swagger_auto_schema(
        operation_summary="Download report file",
        operation_description="Download the original report file generated by ML service",
        manual_parameters=[
            openapi.Parameter(
                'Authorization',
                openapi.IN_HEADER,
                description="Bearer JWT token",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response('Report file'),
            401: ErrorResponseSerializer,
            404: ErrorResponseSerializer
        }
    )
    def get(self, request, task_id):
        # Проверка авторизации
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return Response({'error': 'Authorization header missing'},
                            status=status.HTTP_401_UNAUTHORIZED)

        auth_result = validate_user_token(auth_header)
        if not auth_result.get('valid'):
            return Response({'error': 'Invalid token'},
                            status=status.HTTP_401_UNAUTHORIZED)

        user_id = auth_result['user_id']

        try:
            task = TrafficTask.objects.get(
                task_id=task_id,
                user_id=user_id,
                status='completed'
            )

            if not task.report_file_path:
                return Response({'error': 'Report file not available'},
                                status=status.HTTP_404_NOT_FOUND)

            # Читаем файл и возвращаем его содержимое
            import os
            if os.path.exists(task.report_file_path):
                with open(task.report_file_path, 'r') as f:
                    report_data = f.read()

                from django.http import HttpResponse
                response = HttpResponse(
                    report_data,
                    content_type='application/json'
                )
                response['Content-Disposition'] = f'attachment; filename="report_{task_id}.json"'
                return response
            else:
                return Response({'error': 'Report file not found'},
                                status=status.HTTP_404_NOT_FOUND)

        except TrafficTask.DoesNotExist:
            return Response({'error': 'Task not found'},
                            status=status.HTTP_404_NOT_FOUND)
