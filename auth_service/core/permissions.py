from django.contrib.auth import get_user_model
from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, get_user_model()):
            if obj == request.user:
                return True
        return False
