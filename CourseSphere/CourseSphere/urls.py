from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import home
from Student import views as student_views

urlpatterns = [
    path('admin-portal/', include('Admin.urls', namespace='admin_portal')),
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('courses/', student_views.course_list, name='courses_root'),
    path('student/', include('Student.urls', namespace='student')),
    path('instructor/', include('Instructor.urls', namespace='instructor')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
