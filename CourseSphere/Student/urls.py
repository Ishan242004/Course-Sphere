from django.urls import path
from . import views

app_name = 'student'

urlpatterns = [
    path('register/', views.student_register, name='student_register'),
    path('login/', views.student_login, name='student_login'),
    path('logout/', views.student_logout, name='student_logout'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    # Forgot Password flow
    path('forgot-password/', views.student_forgot_password, name='student_forgot_password'),
    path('verify-otp/', views.student_verify_otp, name='student_verify_otp'),
    path('reset-password/', views.student_reset_password, name='student_reset_password'),
]
