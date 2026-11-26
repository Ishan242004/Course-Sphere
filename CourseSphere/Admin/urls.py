from django.urls import path
from . import views

app_name = 'admin_portal'

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/add/', views.add_course, name='add_course'),
    path('courses/<int:course_id>/edit/', views.edit_course, name='edit_course'),
    path('courses/<int:course_id>/delete/', views.delete_course, name='delete_course'),
    # Student CRUD
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),
    path('students/<int:student_id>/edit/', views.edit_student, name='edit_student'),
    path('students/<int:student_id>/delete/', views.delete_student, name='delete_student'),
    # Instructor CRUD
    path('instructors/', views.instructor_list, name='instructor_list'),
    path('instructors/add/', views.add_instructor, name='add_instructor'),
    path('instructors/<int:instructor_id>/', views.instructor_detail, name='instructor_detail'),
    path('instructors/<int:instructor_id>/edit/', views.edit_instructor, name='edit_instructor'),
    path('instructors/<int:instructor_id>/delete/', views.delete_instructor, name='delete_instructor'),
    # Payment Receipt CRUD
    path('receipts/', views.receipt_list, name='receipt_list'),
    path('receipts/add/', views.add_receipt, name='add_receipt'),
    path('receipts/<str:order_id>/', views.receipt_detail, name='receipt_detail'),
    path('receipts/<str:order_id>/edit/', views.edit_receipt, name='edit_receipt'),
    path('receipts/<str:order_id>/delete/', views.delete_receipt, name='delete_receipt'),
]
