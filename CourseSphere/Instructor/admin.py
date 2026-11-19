from django.contrib import admin
from .models import Instructor


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'phone', 'created_at')
    search_fields = ('user__username', 'user__email', 'specialization', 'phone')
