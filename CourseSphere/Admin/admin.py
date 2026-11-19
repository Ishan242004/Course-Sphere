from django.contrib import admin
from .models import Admin


@admin.register(Admin)
class AdminPanelAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone')
