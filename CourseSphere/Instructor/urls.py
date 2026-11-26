from django.urls import path
from . import views

app_name = 'instructor'

urlpatterns = [
    path('register/', views.instructor_register, name='instructor_register'),
    path('login/', views.instructor_login, name='instructor_login'),
    path('logout/', views.instructor_logout, name='instructor_logout'),
    path('dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
    path('courses/', views.instructor_courses, name='instructor_courses'),
    path('courses/add/', views.instructor_add_course, name='add_course'),
    path('courses/<int:course_id>/', views.instructor_course_detail, name='course_detail'),
    path('courses/<int:course_id>/edit/', views.instructor_edit_course, name='edit_course'),
    path('courses/<int:course_id>/delete/', views.instructor_delete_course, name='delete_course'),
    path('profile/', views.instructor_profile, name='instructor_profile'),
    # Forgot Password flow
    path('forgot-password/', views.instructor_forgot_password, name='instructor_forgot_password'),
    path('verify-otp/', views.instructor_verify_otp, name='instructor_verify_otp'),
    path('reset-password/', views.instructor_reset_password, name='instructor_reset_password'),
]
