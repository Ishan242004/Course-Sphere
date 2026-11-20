from django.urls import path
from . import views

app_name = 'instructor'

urlpatterns = [
    path('register/', views.instructor_register, name='instructor_register'),
    path('login/', views.instructor_login, name='instructor_login'),
    path('logout/', views.instructor_logout, name='instructor_logout'),
    path('dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
    # Forgot Password flow
    path('forgot-password/', views.instructor_forgot_password, name='instructor_forgot_password'),
    path('verify-otp/', views.instructor_verify_otp, name='instructor_verify_otp'),
    path('reset-password/', views.instructor_reset_password, name='instructor_reset_password'),
]
