from django.contrib import admin
from .models import Student, Cart, Order, OrderItem, Enrollment


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'roll_number', 'created_at')
    search_fields = ('user__username', 'user__email', 'roll_number', 'phone')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('student__user__username', 'course__course_title')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('course', 'course_title', 'price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_id',
        'student',
        'subtotal',
        'discount_amount',
        'tax_amount',
        'total_amount',
        'payment_method',
        'razorpay_payment_id',
        'status',
        'created_at',
    )
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_id', 'student__user__username', 'coupon_code', 'razorpay_order_id', 'razorpay_payment_id')
    inlines = [OrderItemInline]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'order', 'enrolled_at')
    list_filter = ('enrolled_at',)
    search_fields = ('student__user__username', 'course__course_title')
