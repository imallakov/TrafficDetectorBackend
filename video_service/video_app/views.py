from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import json
import logging

from .models import VideoTask
from .utils import validate_user_token, save_video_file, create_region_json, send_to_kafka
from .serializers import (
    VideoUploadSerializer, VideoUploadResponseSerializer,
    TaskStatusResponseSerializer, UserTasksResponseSerializer,
    ErrorResponseSerializer, DirectionROISerializer
)

logger = logging.getLogger(__name__)


class VideoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_summary="Upload video for traffic analysis",
        operation_description="""
        Upload a video file along with ROI (Region of Interest) data for traffic analysis.

        The ROI data should be a JSON string containing:
        - directions: Array of directions, each containing arrays of lane polygons
        - end_region: Array of end region polygons for each direction

        Example ROI data:
            {
                "directions": [
                    [
                        [[904, 1934], [1500, 1500], [1542, 1544], [938, 1988]],
                        [[1538, 1546], [1580, 1598], [986, 2054], [940, 1994]],
                        [[1580, 1604], [1634, 1664], [1030, 2128], [986, 2054]],
                        [[1632, 1668], [1684, 1730], [1154, 2146], [1032, 2130]],
                        [[1684, 1730], [1744, 1802], [1336, 2144], [1154, 2146]]
                    ],
                    [
                        [[3210, 2058], [2582, 1448], [2640, 1404], [3268, 1996]],
                        [[3272, 1994], [3316, 1946], [2710, 1354], [2642, 1408]],
                        [[3320, 1944], [3386, 1862], [2782, 1296], [2712, 1356]]
                    ],
                    [
                        [[2312, 584], [2858, 216], [2906, 288], [2378, 642]],
                        [[2380, 642], [2912, 292], [2936, 310], [2416, 672]],
                        [[2938, 312], [2980, 346], [2470, 714], [2416, 678]],
                        [[2982, 348], [3030, 386], [2518, 756], [2468, 716]]
                    ],
                    [
                        [[1386, 736], [1438, 696], [818, 10], [754, 46]],
                        [[1446, 696], [1510, 666], [888, 2], [818, 10]],
                        [[888, 0], [956, 0], [1564, 628], [1514, 666]],
                        [[1564, 624], [1624, 604], [1038, 0], [962, 0]]
                    ]
                ],
                "end_region": [
                    [[1488, 438], [1616, 572], [1824, 452], [1714, 338]],
                    [[2552, 798], [2810, 972], [2976, 886], [2700, 692]],
                    [[2524, 1766], [2680, 1610], [2920, 1828], [2744, 1992]],
                    [[1518, 1482], [1332, 1242], [1100, 1386], [1292, 1648]]
                ]
            }
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
        required_fields = ['directions', 'end_region']
        for field in required_fields:
            if field not in roi_data:
                return Response({'error': f'Missing ROI field: {field}'},
                                status=status.HTTP_400_BAD_REQUEST)

        # Validate that directions is a list of lists of lists
        if not isinstance(roi_data['directions'], list):
            return Response({'error': 'directions must be an array'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Validate that end_region is a list of lists
        if not isinstance(roi_data['end_region'], list):
            return Response({'error': 'end_region must be an array'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Validate that number of end_regions matches number of directions
        if len(roi_data['directions']) != len(roi_data['end_region']):
            return Response({
                'error': 'Number of directions must match number of end_regions',
                'details': f"Found {len(roi_data['directions'])} directions and {len(roi_data['end_region'])} end_regions"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 4. Save video file
            video_path = save_video_file(video_file, user_id)

            # 5. Create region JSON file
            region_json_path = create_region_json(roi_data, user_id)

            # 6. Create database record
            video_task = VideoTask.objects.create(
                user_id=user_id,
                original_filename=video_file.name,
                video_path=video_path,
                sector_config=roi_data,  # Now stores directions/end_regions
                status='uploaded'
            )

            # 7. Prepare task data for ML service
            task_data = {
                "task_id": str(video_task.task_id),
                "user_id": user_id,
                "video_path": video_path,
                "sector_path": region_json_path,  # Now points to regions JSON
                "output_path": f"/shared/output/output_{user_id}_{video_task.task_id}.mp4",
                "report_path": f"/shared/reports/report_{user_id}_{video_task.task_id}.json",  # Changed to .json
                "model_path": "/app/models/detector_yolov10s.pt"  # Updated model name
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
        operation_description="Returns the expected structure for ROI (Region of Interest) data with directions",
        responses={200: DirectionROISerializer}
    )
    def get(self, request):
        """Returns example ROI data structure for directional detection"""
        example_roi = {
            "directions": [
                [  # Direction 0 with 5 lanes
                    [[904, 1934], [1500, 1500], [1542, 1544], [938, 1988]],
                    [[1538, 1546], [1580, 1598], [986, 2054], [940, 1994]],
                    [[1580, 1604], [1634, 1664], [1030, 2128], [986, 2054]],
                    [[1632, 1668], [1684, 1730], [1154, 2146], [1032, 2130]],
                    [[1684, 1730], [1744, 1802], [1336, 2144], [1154, 2146]]
                ],
                [  # Direction 1 with 3 lanes
                    [[3210, 2058], [2582, 1448], [2640, 1404], [3268, 1996]],
                    [[3272, 1994], [3316, 1946], [2710, 1354], [2642, 1408]],
                    [[3320, 1944], [3386, 1862], [2782, 1296], [2712, 1356]]
                ],
                [  # Direction 2 with 4 lanes
                    [[2312, 584], [2858, 216], [2906, 288], [2378, 642]],
                    [[2380, 642], [2912, 292], [2936, 310], [2416, 672]],
                    [[2938, 312], [2980, 346], [2470, 714], [2416, 678]],
                    [[2982, 348], [3030, 386], [2518, 756], [2468, 716]]
                ],
                [  # Direction 3 with 4 lanes
                    [[1386, 736], [1438, 696], [818, 10], [754, 46]],
                    [[1446, 696], [1510, 666], [888, 2], [818, 10]],
                    [[888, 0], [956, 0], [1564, 628], [1514, 666]],
                    [[1564, 624], [1624, 604], [1038, 0], [962, 0]]
                ]
            ],
            "end_region": [
                [[1488, 438], [1616, 572], [1824, 452], [1714, 338]],  # End for direction 0
                [[2552, 798], [2810, 972], [2976, 886], [2700, 692]],  # End for direction 1
                [[2524, 1766], [2680, 1610], [2920, 1828], [2744, 1992]],  # End for direction 2
                [[1518, 1482], [1332, 1242], [1100, 1386], [1292, 1648]]  # End for direction 3
            ]
        }
        return Response(example_roi)
