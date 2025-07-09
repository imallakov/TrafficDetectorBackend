from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import json
import logging

from .models import VideoTask
from .utils import validate_user_token, save_video_file, create_sector_json, send_to_kafka
from .serializers import (
    VideoUploadSerializer, VideoUploadResponseSerializer,
    TaskStatusResponseSerializer, UserTasksResponseSerializer,
    ErrorResponseSerializer, ROIDataSerializer
)

logger = logging.getLogger(__name__)


class VideoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_summary="Upload video for traffic analysis",
        operation_description="""
        Upload a video file along with ROI (Region of Interest) data for traffic analysis.

        The ROI data should be a JSON string containing:
        - start_region: Coordinates of the starting detection area
        - end_region: Coordinates of the ending detection area  
        - lanes: Array of lane coordinates
        - lanes_count: Number of lanes
        - length_km: Sector length in kilometers
        - max_speed: Speed limit in km/h

        Example ROI data:
        ```json
            {
            "sector_id": 1,
            "start_region": [[100,100], [200,100], [200,200], [100,200]],
            "end_region": [[300,100], [400,100], [400,200], [300,200]],
            "lanes": [[[150,100], [250,100], [250,200], [150,200]]],
            "lanes_count": 1,
            "length_km": 0.1,
            "max_speed": 60
            }
        ```
        """,
        manual_parameters=[
            openapi.Parameter(
                'Authorization',
                openapi.IN_HEADER,
                description="Bearer JWT token",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        request_body=VideoUploadSerializer,
        responses={
            201: VideoUploadResponseSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
            500: ErrorResponseSerializer
        }
    )
    def post(self, request):
        """
        Upload video and ROI data for processing
        Expected data:
        - video (file)
        - roi_data (JSON string)
        """
        # 1. Check authentication
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return Response({'error': 'Authorization header missing'},
                            status=status.HTTP_401_UNAUTHORIZED)

        auth_result = validate_user_token(auth_header)
        if not auth_result.get('valid'):
            return Response({
                'error': 'Invalid token',
                'details': auth_result.get('error')
            }, status=status.HTTP_401_UNAUTHORIZED)

        user_id = auth_result['user_id']

        # 2. Validate input data
        video_file = request.FILES.get('video')
        roi_data_str = request.data.get('roi_data')

        if not video_file:
            return Response({'error': 'Video file is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not roi_data_str:
            return Response({'error': 'ROI data is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            roi_data = json.loads(roi_data_str)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid ROI data format'},
                            status=status.HTTP_400_BAD_REQUEST)

        # 3. Validate ROI data structure
        required_fields = ['start_region', 'end_region', 'lanes', 'lanes_count', 'length_km', 'max_speed']
        for field in required_fields:
            if field not in roi_data:
                return Response({'error': f'Missing ROI field: {field}'},
                                status=status.HTTP_400_BAD_REQUEST)

        try:
            # 4. Save video file
            video_path = save_video_file(video_file, user_id)

            # 5. Create sector JSON file
            sector_json_path = create_sector_json(roi_data, user_id)

            # 6. Create database record
            video_task = VideoTask.objects.create(
                user_id=user_id,
                original_filename=video_file.name,
                video_path=video_path,
                sector_config=roi_data,
                status='uploaded'
            )

            # 7. Prepare task data for ML service
            task_data = {
                "task_id": str(video_task.task_id),
                "user_id": user_id,
                "video_path": video_path,
                "sector_path": sector_json_path,
                "output_path": f"/shared/output/output_{user_id}_{video_task.task_id}.mp4",
                "report_path": f"/shared/reports/report_{user_id}_{video_task.task_id}.xlsx",
                "model_path": "/app/models/default-model.pt"
            }

            # 8. Send to Kafka
            if send_to_kafka(task_data):
                video_task.status = 'queued'
                video_task.save()

                return Response({
                    'task_id': str(video_task.task_id),
                    'status': 'queued',
                    'message': 'Video processing started successfully'
                }, status=status.HTTP_201_CREATED)
            else:
                video_task.status = 'failed'
                video_task.error_message = 'Failed to queue task'
                video_task.save()

                return Response({'error': 'Failed to queue video processing task'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error processing video upload: {e}")
            return Response({'error': f'Processing failed: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TaskStatusView(APIView):
    @swagger_auto_schema(
        operation_summary="Get task status",
        operation_description="Retrieve the current status of a video processing task",
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
            200: TaskStatusResponseSerializer,
            401: ErrorResponseSerializer,
            404: ErrorResponseSerializer
        }
    )
    def get(self, request, task_id):
        """Get status of a video processing task"""
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
            task = VideoTask.objects.get(task_id=task_id, user_id=user_id)

            return Response({
                'task_id': str(task.task_id),
                'status': task.status,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'original_filename': task.original_filename,
                'error_message': task.error_message
            })

        except VideoTask.DoesNotExist:
            return Response({'error': 'Task not found'},
                            status=status.HTTP_404_NOT_FOUND)


class UserTasksView(APIView):
    @swagger_auto_schema(
        operation_summary="Get user's tasks",
        operation_description="Retrieve all video processing tasks for the authenticated user",
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
            200: UserTasksResponseSerializer,
            401: ErrorResponseSerializer
        }
    )
    def get(self, request):
        """Get all tasks for authenticated user"""
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

        tasks = VideoTask.objects.filter(user_id=user_id).order_by('-created_at')

        tasks_data = []
        for task in tasks:
            tasks_data.append({
                'task_id': str(task.task_id),
                'status': task.status,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'original_filename': task.original_filename,
                'error_message': task.error_message
            })

        return Response({'tasks': tasks_data})


class ROISchemaView(APIView):
    @swagger_auto_schema(
        operation_summary="Get ROI data schema",
        operation_description="Returns the expected structure for ROI (Region of Interest) data",
        responses={200: ROIDataSerializer}
    )
    def get(self, request):
        """Returns example ROI data structure"""
        example_roi = {
            "sector_id": 1,
            "start_region": [[100, 100], [200, 100], [200, 200], [100, 200]],
            "end_region": [[300, 100], [400, 100], [400, 200], [300, 200]],
            "lanes": [
                [[150, 100], [250, 100], [250, 200], [150, 200]],
                [[250, 100], [350, 100], [350, 200], [250, 200]]
            ],
            "lanes_count": 2,
            "length_km": 0.1,
            "max_speed": 60
        }
        return Response(example_roi)
