from django.contrib import admin
from django.urls import path, include
from .views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('student/', include('Student.urls', namespace='student')),
    path('instructor/', include('Instructor.urls', namespace='instructor')),
]
