from django.urls import path
from . import views

app_name = 'student'

urlpatterns = [
    path('register/', views.student_register, name='student_register'),
    path('login/', views.student_login, name='student_login'),
    path('logout/', views.student_logout, name='student_logout'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    # Courses
    path('courses/', views.course_list, name='course_list'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('course-list/', views.course_list, name='student_course_list'),
    path('course-detail/<int:course_id>/', views.course_detail, name='student_course_detail'),
    # Cart, Coupons, Checkout & Orders
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:course_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:course_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('cart/coupon/', views.apply_coupon, name='apply_coupon'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/<str:order_id>/', views.order_detail, name='order_detail'),
    # Forgot Password flow
    path('forgot-password/', views.student_forgot_password, name='student_forgot_password'),
    path('verify-otp/', views.student_verify_otp, name='student_verify_otp'),
    path('reset-password/', views.student_reset_password, name='student_reset_password'),
]
