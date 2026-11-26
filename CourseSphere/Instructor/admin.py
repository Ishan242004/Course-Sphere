from django.contrib import admin
from .models import Instructor, Course


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'phone', 'created_at')
    search_fields = ('user__username', 'user__email', 'specialization', 'phone')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_title', 'category', 'price', 'status', 'instructor', 'created_date', 'has_image')
    list_filter = ('status', 'category', 'created_date', 'instructor')
    search_fields = ('course_title', 'category', 'description')
    ordering = ('-created_date',)
    readonly_fields = ('created_date',)
    fieldsets = (
        ('Course Information', {
            'fields': ('course_title', 'category', 'status', 'description', 'instructor')
        }),
        ('Pricing & Media', {
            'fields': ('price', 'course_image')
        }),
        ('Timestamps', {
            'fields': ('created_date',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(boolean=True, description="Has Image")
    def has_image(self, obj):
        return bool(obj.course_image)
