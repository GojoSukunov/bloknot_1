from django.contrib import admin
from .models import User,Goals,Category,Tasks,Note,Habits



class NoteInline(admin.TabularInline):
    model=Note
    extra=1
class GoalsAdmin(admin.ModelAdmin):
    inlines = [NoteInline]
admin.site.register(User)
admin.site.register(Goals,GoalsAdmin)
admin.site.register(Category)
admin.site.register(Tasks)
admin.site.register(Habits)


