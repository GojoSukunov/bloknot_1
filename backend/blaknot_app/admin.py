from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Deal, Note, Tasks, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Стандартный UserAdmin: пароли хешируются, права меняются штатными формами."""
    list_display = ("username", "email", "is_active", "is_staff", "date_joined")
    search_fields = ("username", "email")
    fieldsets = UserAdmin.fieldsets + (("Профиль", {"fields": ("phone_number", "age", "profile_image")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Профиль", {"fields": ("email", "phone_number", "age")}),
    )


class NoteInline(admin.TabularInline):
    model = Note
    extra = 0


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ("title_deal", "owner", "status", "cash", "updated_at")
    list_filter = ("status",)
    search_fields = ("title_deal", "owner__username")
    list_select_related = ("owner",)
    inlines = [NoteInline]


@admin.register(Tasks)
class TasksAdmin(admin.ModelAdmin):
    list_display = ("title_task", "owner", "deal", "level", "status", "deadline")
    list_filter = ("status", "level")
    search_fields = ("title_task", "owner__username")
    list_select_related = ("owner", "deal")


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title_note", "deal", "date_note")
    search_fields = ("title_note",)
    list_select_related = ("deal",)
