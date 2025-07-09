from django.urls import path
from .views import (
    UserTrafficDataView,
    UserVideoResultsView,
    TaskResultView,
    DownloadReportView,
    DownloadVideoView
)

urlpatterns = [
    # Legacy endpoint (keep for backwards compatibility)
    path('traffic/<str:user_id>/', UserTrafficDataView.as_view(), name='user_traffic'),

    # New video processing endpoints
    path('results/', UserVideoResultsView.as_view(), name='user_video_results'),
    path('results/<uuid:task_id>/', TaskResultView.as_view(), name='task_result'),

    # Download endpoints
    path('download/report/<uuid:task_id>/', DownloadReportView.as_view(), name='download_report'),
    path('download/video/<uuid:task_id>/', DownloadVideoView.as_view(), name='download_video'),
]
