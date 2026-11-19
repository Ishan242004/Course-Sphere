from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'roll_number', 'created_at')
    search_fields = ('user__username', 'user__email', 'roll_number', 'phone')
