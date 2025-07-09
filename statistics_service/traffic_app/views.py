from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse, Http404
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import os
import mimetypes
import logging

from .models import TrafficData, VideoProcessingResult
from .serializers import TrafficDataSerializer
from .utils import validate_user_token

logger = logging.getLogger(__name__)


class UserTrafficDataView(APIView):
    """Original endpoint - keep for backwards compatibility"""

    @swagger_auto_schema(
        operation_summary="Get user traffic data",
        operation_description="Get legacy traffic data for a specific user",
        responses={200: TrafficDataSerializer(many=True)}
    )
    def get(self, request, user_id):
        traffic_data = TrafficData.objects.filter(user_id=user_id).order_by('-timestamp')
        serializer = TrafficDataSerializer(traffic_data, many=True)
        return Response(serializer.data)


class UserVideoResultsView(APIView):
    """Get all video processing results for authenticated user"""

    @swagger_auto_schema(
        operation_summary="Get user's video processing results",
        operation_description="Retrieve all video processing results for the authenticated user",
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
            200: openapi.Response(
                description="List of video processing results",
                examples={
                    "application/json": {
                        "results": [
                            {
                                "task_id": "uuid-here",
                                "status": "completed",
                                "created_at": "2024-01-01T10:00:00Z",
                                "report_download_url": "/api/download/report/uuid-here/",
                                "video_download_url": "/api/download/video/uuid-here/"
                            }
                        ]
                    }
                }
            ),
            401: openapi.Response(description="Unauthorized")
        }
    )
    def get(self, request):
        # Check authentication
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return Response({'error': 'Authorization header missing'},
                            status=status.HTTP_401_UNAUTHORIZED)

        auth_result = validate_user_token(auth_header)
        if not auth_result.get('valid'):
            return Response({'error': 'Invalid token'},
                            status=status.HTTP_401_UNAUTHORIZED)

        user_id = auth_result['user_id']

        # Get user's video processing results
        results = VideoProcessingResult.objects.filter(user_id=user_id).order_by('-created_at')

        results_data = []
        for result in results:
            result_data = {
                'task_id': str(result.task_id),
                'status': result.status,
                'created_at': result.created_at,
                'updated_at': result.updated_at,
                'error_message': result.error_message,
            }

            # Add download URLs if files exist
            if result.status == 'completed':
                if result.report_path:
                    result_data['report_download_url'] = f'/api/download/report/{result.task_id}/'
                if result.output_video_path:
                    result_data['video_download_url'] = f'/api/download/video/{result.task_id}/'

            results_data.append(result_data)

        return Response({'results': results_data})


class TaskResultView(APIView):
    """Get specific task result by task_id"""

    @swagger_auto_schema(
        operation_summary="Get specific task result",
        operation_description="Get video processing result for a specific task",
        manual_parameters=[
            openapi.Parameter(
                'Authorization',
                openapi.IN_HEADER,
                description="Bearer JWT token",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'task_id',
                openapi.IN_PATH,
                description="UUID of the task",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={200: "Task result details", 401: "Unauthorized", 404: "Task not found"}
    )
    def get(self, request, task_id):
        # Check authentication
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
            result = VideoProcessingResult.objects.get(task_id=task_id, user_id=user_id)

            result_data = {
                'task_id': str(result.task_id),
                'status': result.status,
                'created_at': result.created_at,
                'updated_at': result.updated_at,
                'error_message': result.error_message,
            }

            if result.status == 'completed':
                if result.report_path:
                    result_data['report_download_url'] = f'/api/download/report/{result.task_id}/'
                if result.output_video_path:
                    result_data['video_download_url'] = f'/api/download/video/{result.task_id}/'

            return Response(result_data)

        except VideoProcessingResult.DoesNotExist:
            return Response({'error': 'Task not found'},
                            status=status.HTTP_404_NOT_FOUND)


class DownloadReportView(APIView):
    """Download Excel report file"""

    @swagger_auto_schema(
        operation_summary="Download Excel report",
        operation_description="Download the Excel statistics report for a completed task",
        manual_parameters=[
            openapi.Parameter(
                'Authorization',
                openapi.IN_HEADER,
                description="Bearer JWT token",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'task_id',
                openapi.IN_PATH,
                description="UUID of the task",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(description="Excel file download"),
            401: "Unauthorized",
            404: "File not found"
        }
    )
    def get(self, request, task_id):
        # Check authentication
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
            result = VideoProcessingResult.objects.get(
                task_id=task_id,
                user_id=user_id,
                status='completed'
            )

            if not result.report_path or not os.path.exists(result.report_path):
                raise Http404("Report file not found")

            # Serve the file
            with open(result.report_path, 'rb') as f:
                response = HttpResponse(
                    f.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="traffic_report_{task_id}.xlsx"'
                return response

        except VideoProcessingResult.DoesNotExist:
            raise Http404("Task not found")


class DownloadVideoView(APIView):
    """Download processed video file"""

    @swagger_auto_schema(
        operation_summary="Download processed video",
        operation_description="Download the processed video file for a completed task",
        manual_parameters=[
            openapi.Parameter(
                'Authorization',
                openapi.IN_HEADER,
                description="Bearer JWT token",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'task_id',
                openapi.IN_PATH,
                description="UUID of the task",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(description="Video file download"),
            401: "Unauthorized",
            404: "File not found"
        }
    )
    def get(self, request, task_id):
        # Check authentication
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
            result = VideoProcessingResult.objects.get(
                task_id=task_id,
                user_id=user_id,
                status='completed'
            )

            if not result.output_video_path or not os.path.exists(result.output_video_path):
                raise Http404("Video file not found")

            # Serve the file
            with open(result.output_video_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='video/mp4')
                response['Content-Disposition'] = f'attachment; filename="processed_video_{task_id}.mp4"'
                return response

        except VideoProcessingResult.DoesNotExist:
            raise Http404("Task not found")
