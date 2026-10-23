from rest_framework import permissions


class CheckOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'deal'):  # Note не имеет поля owner — владелец это владелец дела
            return obj.deal.owner == request.user
        return obj == request.user