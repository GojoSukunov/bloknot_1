from rest_framework import permissions


class CheckOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return getattr(obj, 'owner', obj) == request.user