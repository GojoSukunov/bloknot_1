from rest_framework import permissions


class CheckOwner(permissions.BasePermission):
    """Доступ к объекту только его владельцу (второй рубеж защиты — основной фильтр в get_queryset)."""

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "owner"):
            return obj.owner_id == request.user.pk
        if hasattr(obj, "deal"):  # Note не имеет owner — владелец заметки это владелец дела
            return obj.deal.owner_id == request.user.pk
        return obj == request.user