from django.urls import path
from . import views

app_name = 'instructor'

urlpatterns = [
    path('register/', views.instructor_register, name='instructor_register'),
    path('login/', views.instructor_login, name='instructor_login'),
    path('logout/', views.instructor_logout, name='instructor_logout'),
    path('dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
]
