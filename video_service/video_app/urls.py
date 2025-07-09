from django.urls import path
from .views import VideoUploadView, TaskStatusView, UserTasksView, ROISchemaView

urlpatterns = [
    path('upload/', VideoUploadView.as_view(), name='video_upload'),
    path('task/<uuid:task_id>/', TaskStatusView.as_view(), name='task_status'),
    path('tasks/', UserTasksView.as_view(), name='user_tasks'),
    path('roi-schema/', ROISchemaView.as_view(), name='roi_schema'),
]
