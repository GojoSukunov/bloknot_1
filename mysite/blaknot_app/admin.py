from django.contrib import admin
from .models import User,Deal,Tasks,Note



class NoteInline(admin.TabularInline):
    model=Note
    extra=1
class GoalsAdmin(admin.ModelAdmin):
    inlines = [NoteInline]
admin.site.register(User)
admin.site.register(Deal,GoalsAdmin)
admin.site.register(Tasks)


