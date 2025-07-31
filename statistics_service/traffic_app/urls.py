from django.urls import path
from .views import (
    TaskStatisticsView,
    UserTasksListView,
    DirectionSummaryView,
    DownloadReportView
)

urlpatterns = [
    path('tasks/<uuid:task_id>/', TaskStatisticsView.as_view(), name='task_statistics'),
    path('tasks/', UserTasksListView.as_view(), name='user_tasks'),
    path('summary/', DirectionSummaryView.as_view(), name='direction_summary'),
    path('report/<uuid:task_id>/', DownloadReportView.as_view(), name='download_report'),
]
